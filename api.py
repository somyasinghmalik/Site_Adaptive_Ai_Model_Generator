import json
import os
from fastapi import FastAPI, BackgroundTasks, Query, File, UploadFile, Form
from nano import process_request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse
from typing import Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
from dotenv import load_dotenv
load_dotenv()

REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Link to scraper and search engine
from rgen10 import run_scraper_pipeline, site_data_store
from img import search_brand_blueprint

app = FastAPI(title="Dynamic Scraper & Search API Bridge")

os.makedirs("generated", exist_ok=True)

app.mount(
    "/generated",
    StaticFiles(directory="generated"),
    name="generated"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    url: str  
    force_rescrape: bool = False

prompt_cache = {}

engine_state = {
    "status": "idle",
    "message": "System engine is idle. Awaiting configuration input from React."
}

def resolve_site_json_path(url_string: str) -> str:
    parsed_url = urlparse(url_string)
    domain = parsed_url.netloc.replace("www.", "")
    safe_domain = "".join(c for c in domain if c.isalnum() or c in "._-").strip()
    return os.path.join("site_data", safe_domain, f"{safe_domain}_biodata.json")

def execution_wrapper(target_url: str, force_rescrape: bool):
    global engine_state
    try:
        engine_state["status"] = "running"
        engine_state["message"] = f"Playwright crawler running on target: {target_url}"
        
        # 2. Dynamic check: Safely handle whether rgen7 accepts the flag or not
        import inspect
        sig = inspect.signature(run_scraper_pipeline)
        if "force_rescrape" in sig.parameters:
            run_scraper_pipeline(target_url, force_rescrape=force_rescrape)
        else:
            # Fallback if your rgen7.py hasn't been updated yet
            run_scraper_pipeline(target_url)
            
        engine_state["status"] = "completed"
        engine_state["message"] = f"Pipeline analysis completed for {target_url}."
    except Exception as e:
        engine_state["status"] = "failed"
        engine_state["message"] = f"Pipeline terminated abnormally: {str(e)}"

# ------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------

@app.get("/api/categories")
def fetch_all_categories(url: str = Query(..., description="Target brand domain URL")):
    """Returns all discoverable categories for a given brand domain, ungrouped."""
    from img import search_brand_blueprint
    # Use a broad single-char query so all group fillers are returned
    result = search_brand_blueprint("a", url)
    
    all_items = []
    seen = set()

    if result.get("type") == "suggestions":
        for item in result["data"]:
            if item["text"] not in seen:
                seen.add(item["text"])
                # Cache the prompt so generate-image works immediately after dropdown pick
                global_ratio = result.get("global_layout_aspect_ratio", "16:9")
                prompt_cache[item["text"]] = {
                    "prompt": item["prompt"],
                    "aspect_ratio": global_ratio
                }
                all_items.append({
                    "text": item["text"],
                    "group": item.get("group", ""),
                    "is_exact": item.get("is_exact", False),
                    "raw_url": item.get("raw_url", "")   # ← add this line
                })

    # Sort: group first, then alphabetically within group
    all_items.sort(key=lambda x: (x["group"].lower(), x["text"].lower()))
    return {"categories": all_items}

@app.get("/api/check-cache")
def check_cache_status(url: str = Query(..., description="Target URL to check")):
    dynamic_json_path = resolve_site_json_path(url)
    exists = os.path.exists(dynamic_json_path)
    return {"exists": exists, "path": dynamic_json_path}

@app.post("/api/start-crawl")
def trigger_pipeline_engine(payload: CrawlRequest, background_tasks: BackgroundTasks):
    global engine_state
    if engine_state["status"] == "running":
        return {"message": "The pipeline engine is already running an active scan configuration."}
    
    target_string_url = str(payload.url)
    # Automatically fix missing protocols so Playwright doesn't crash later
    if not target_string_url.startswith("http://") and not target_string_url.startswith("https://"):
        target_string_url = "https://" + target_string_url

    background_tasks.add_task(execution_wrapper, target_string_url, payload.force_rescrape)
    return {"message": f"Background engine job scheduled for destination: {target_string_url}"}

@app.get("/api/status")
def query_engine_status():
    return engine_state


# FIXED: url is now Optional[str] = None, completely eliminating the 422 error
@app.get("/api/results")
def fetch_stored_dataset(url: Optional[str] = None):
    # Scenario A: Explicit URL provided by frontend
    if url:
        dynamic_json_path = resolve_site_json_path(url)
        if os.path.exists(dynamic_json_path):
            try:
                with open(dynamic_json_path, "r", encoding="utf-8") as file:
                    return json.load(file)
            except Exception as e:
                return JSONResponse(status_code=500, content={"message": f"Error parsing file: {str(e)}"})

    # Scenario B: No URL provided, or specific file doesn't exist yet -> Fallback to memory store
    if site_data_store.get("pages"):
        return site_data_store
        
    # Scenario C: Auto-detect the most recently updated file inside the site_data directory
    base_dir = "site_data"
    if os.path.exists(base_dir):
        latest_file = None
        latest_time = 0
        
        for item in os.listdir(base_dir):
            sub_path = os.path.join(base_dir, item)
            if os.path.isdir(sub_path):
                json_file = os.path.join(sub_path, f"{item}_biodata.json")
                if os.path.exists(json_file):
                    modified_time = os.path.getmtime(json_file)
                    if modified_time > latest_time:
                        latest_time = modified_time
                        latest_file = json_file
                        
        if latest_file:
            try:
                with open(latest_file, "r", encoding="utf-8") as file:
                    return json.load(file)
            except:
                pass

    return JSONResponse(
        status_code=404, 
        content={"message": "No brand metrics data generated or found on system disks."}
    )


@app.get("/api/search")
def search_blueprint(
    query: str = Query(..., description="The query keyword to search"),
    url: str = Query(..., description="The active context brand domain source URL")
):
    # Pass both query and url context to the updated backend module
    result_prompt = search_brand_blueprint(query, url)
    
    # Grab the site-wide global aspect ratio fallback
    global_site_ratio = result_prompt.get("global_layout_aspect_ratio", "16:9")

    if (
        result_prompt.get("type") == "suggestions"
        and "data" in result_prompt
    ):
        for item in result_prompt["data"]:
            # FIXED: Pairs your combined prompt text blocks with the global fallback ratio
            prompt_cache[item["text"]] = {
                "prompt": item["prompt"],
                "aspect_ratio": global_site_ratio 
            }

    return {"query": query, "result": result_prompt}

@app.post("/api/generate-image")
async def generate_image(
    category: str = Form(...),
    front_image: UploadFile | None = File(None),
    back_image: UploadFile | None = File(None)
):
    images_bytes_list = []
    image_filenames_list = []

    if front_image:
        images_bytes_list.append(await front_image.read())
        image_filenames_list.append(front_image.filename)

    if back_image:
        images_bytes_list.append(await back_image.read())
        image_filenames_list.append(back_image.filename)
    # Retrieve our cached dictionary config safely
    cached_config = prompt_cache.get(category)
    
    if isinstance(cached_config, dict):
        prompt = cached_config.get("prompt")
        aspect_ratio = cached_config.get("aspect_ratio", "16:9")
    else:
        # Fallback if cache hits an old string reference or empty state
        prompt = cached_config
        aspect_ratio = "16:9"

    print("CATEGORY:", category)
    print("PROMPT:", prompt)
    print("ASPECT RATIO SENT TO NANO:", aspect_ratio)

    # FIXED: Added aspect_ratio to the parameters passed to your generation engine
    result = process_request(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        images_bytes_list=images_bytes_list,
        image_filenames_list=image_filenames_list
    )
    return result


@app.post("/api/prediction-status")
def prediction_status(payload: dict):

    prediction_ids = payload.get("prediction_ids", [])

    images = []
    all_done = True

    headers = {
        "Authorization": f"Bearer {REPLICATE_TOKEN}"
    }

    for pid in prediction_ids:

        response = requests.get(
            f"https://api.replicate.com/v1/predictions/{pid}",
            headers=headers
        )

        if response.status_code != 200:
            all_done = False
            continue

        data = response.json()

        status = data.get("status")

        if status not in ["succeeded", "failed"]:
            all_done = False

        if status == "succeeded":

            output = data.get("output")

            if isinstance(output, list):
                images.extend(output)

            elif isinstance(output, str):
                images.append(output)

    return {
        "completed": all_done,
        "images": images
    }

    
@app.get("/download/{filename}")
def download_image(filename: str):
    file_path = os.path.join("generated", filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
