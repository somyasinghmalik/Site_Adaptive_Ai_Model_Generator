import json
import os
import queue
import threading
import time
import base64
import requests
import re
from collections import defaultdict
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
from PIL import Image
from playwright.sync_api import sync_playwright

# -----------------------------
# CONFIG & INITIALIZATION (Configured Dynamically via URL)
# -----------------------------
OUTPUT_DIR = "site_data"
SCREENSHOT_DIR = ""
output_json = ""

# Initialize Thread-Safe Queue
data_queue = queue.Queue()
data_lock = threading.Lock()  # Prevents corruption when writing JSON concurrently

# Master Dictionary Structure
site_data_store = {
    "global_brand_visual_blueprint": "Pending initialization...",
    "pages": []
}

BAD_KEYWORDS = [
    "privacy", "refund", "shipping", "faq", "contact", 
    "terms", "policy", "login", "signup", "cart", 
    "checkout", "account", "track-order"
]

# -----------------------------
# REPLICATE HTTP DIRECT API CALLER
# -----------------------------
def call_replicate_api_direct(model_version: str, prompt: str, image_input):
    """
    Direct HTTP alternative to Replicate SDK using 'requests'.
    Converts local image files to PURE base64 alphanumeric arrays to match the model schema.
    """
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("[Error] REPLICATE_API_TOKEN not found in environment variables.")
        return "API Key Error."

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

    try:
        # Normalize single string input to a list for unified handling
        image_paths = [image_input] if isinstance(image_input, str) else image_input
        
        encoded_images = []
        for path in image_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                    
                    # Determine extension dynamically to build a bulletproof URI
                    ext = "png" if path.lower().endswith(".png") else "jpeg"
                    
                    # This builds a valid, structurally sound URI scheme that Replicate's gateway requires
                    encoded_images.append(f"data:image/{ext};base64,{b64_data}")

        if not encoded_images:
            return "Analysis failed: No valid screenshots available."

        create_url = f"https://api.replicate.com/v1/models/{model_version}/predictions"
        
        # Exact schema requirements for google/gemini-3-flash
        payload = {
            "input": {
                "prompt": prompt,
                "images": encoded_images,
                "temperature": 1,
                "top_p": 0.95
            }
        }
        
        response = requests.post(create_url, json=payload, headers=headers, timeout=30)
        if response.status_code not in [200, 201]:
            print(f"[HTTP Error] Replicate creation status: {response.status_code} - {response.text}")
            return "Analysis failed on engine submission request."
            
        prediction_data = response.json()
        poll_url = prediction_data["urls"]["get"]

        # Polling loop to wait for completion
        while True:
            time.sleep(2)
            poll_response = requests.get(poll_url, headers=headers, timeout=20)
            if poll_response.status_code != 200:
                continue
                
            status_data = poll_response.json()
            status = status_data["status"]
            
            if status == "succeeded":
                output = status_data.get("output", "")
                return "".join(output).strip() if isinstance(output, list) else str(output).strip()
            elif status in ["failed", "canceled"]:
                return f"Analysis failed due to execution state: {status}"

    except Exception as e:
        print(f"[HTTP Exception Connection Break]: {e}")
        return "Analysis failed due to network request exceptions."

# -----------------------------
# HELPERS
# -----------------------------
def clean_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def get_group(url):
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    return parts[0] if parts else "home"

def should_skip(url):
    url = url.lower()
    return any(word in url for word in BAD_KEYWORDS)

def safe_filename(url):
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    return (path if path else "home")[:120]

def generate_brand_description_from_images(images_list):
    print("[Replicate] Analyzing homepage visual layers to formulate global brand identity...")
    
    # EDIT 1: Swapped to optimized global prompt using clean asterisks formatting (*16:9*)
    prompt = """
    Analyze these sequential screenshots from the homepage of an e-commerce fashion brand. 
    Synthesize the brand's core visual identity into a detailed, high-fashion image-generation description paragraph.

    Rules:
    - Capture the background environment, lighting style, color palette, garment textures, model choices, and overall photography aesthetic.
    - At the very end of your response, evaluate the overall shape of the website layout and append the best-fitting aspect ratio choice (*1:1*, *16:9*, *9:16*, or *4:3*) wrapped in asterisks.

    Example Ending:
    ... luxury ethnic fashion photography, soft cinematic depth, high-end fashion campaign.
    *16:9*
    """
    try:
        return call_replicate_api_direct("google/gemini-3-flash", prompt, images_list)
    except Exception as e:
        print(f"[Replicate Error] Could not generate brand description from images: {e}")
        return "A high-fashion e-commerce studio portrait, editorial lighting, clean neutral background. \n*16:9*"

# -----------------------------
# BACKGROUND REPLICATE CONSUMER
# -----------------------------
def replicate_consumer_worker():
    print("[Replicate Worker] Started and waiting for screenshots...")

    while True:
        task = data_queue.get()
        if task is None:
            print("[Replicate Worker] No more images incoming. Finalizing...")
            data_queue.task_done()
            break
        
        item_data, screenshot_index, filepath = task
        print(f"  [Replicate Worker] Processing: {os.path.basename(filepath)}")
        
        try:
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                # EDIT 2: Swapped to optimized condensed product prompt template
                prompt = """
                Analyze this e-commerce fashion screenshot.

                Output EXACTLY in this format:

                Base Prompt: ...
                Pose A: ...
                Pose B: ...
                Pose C: ...

                *aspect_ratio*

                Requirements for Content:
                1. Base Prompt: Create a comprehensive image-generation prompt capturing the environment/background, lighting style, color temperature, fashion aesthetic, model appearance, hairstyle, and overall photography style. End this line with: "aspect ratio portrait".
                2. Pose A: Describe a natural hero/catalog pose appropriate for the clothing category.
                3. Pose B: Describe a different camera angle and body position from Pose A.
                4. Pose C: Describe a dynamic pose emphasizing movement, garment drape, or lifestyle storytelling.

                Rules:
                - Poses A, B, and C must be completely distinct from one another.
                - At the very end, evaluate the layout shape of the clothing images in the screenshot and append the best-fitting aspect ratio choice (*1:1*, *16:9*, *9:16*, *4:3*, or *3:4*) wrapped in asterisks.

                Example Output:
                Base Prompt: indoor lifestyle setting, rustic stone wall backdrop, soft natural daylight, warm tones, luxury ethnic fashion photography, young adult female model, elegant jewelry, polished makeup, sophisticated commercial styling, high-end fashion campaign, aspect ratio portrait
                Pose A: front-facing full-length standing pose with hands relaxed at sides
                Pose B: seated leaning pose with head tilted toward camera
                Pose C: walking pose with flowing garment movement and natural stride
                *3:4*

                CRITICAL EXCEPTION RULE:
                If the screenshot is a website error, timeout, generic digital UI, navigation menu, or contains NO visible human fashion subject, ignore the format above and reply with exactly:
                NO_HUMAN_SUBJECT
                """

                analysis_text = call_replicate_api_direct("google/gemini-3-flash", prompt, filepath)
            else:
                analysis_text = "Screenshot file unavailable or empty."
        except Exception as e:
            print(f"  [Replicate Error] File {filepath}: {e}")
            analysis_text = "Analysis failed due to an API or system error."

        with data_lock:
            for data_entry in site_data_store["pages"]:
                if data_entry["url"] == item_data["url"]:
                    if "NO_HUMAN_SUBJECT" in analysis_text:
                        data_entry["screenshots"][screenshot_index]["photo_details"] = "NO_HUMAN_SUBJECT"
                    else:
                        # EDIT 3: Added regex cleaner to extract ratio value seamlessly and keep JSON payload text clean
                        ratio_match = re.search(r'\*(\d+:\d+)\*', analysis_text)
                        if ratio_match:
                            detected_ratio = ratio_match.group(1)
                            clean_text = analysis_text.replace(ratio_match.group(0), "").strip()
                            data_entry["screenshots"][screenshot_index]["layout_aspect_ratio"] = detected_ratio
                            data_entry["screenshots"][screenshot_index]["photo_details"] = clean_text
                        else:
                            data_entry["screenshots"][screenshot_index]["layout_aspect_ratio"] = "3:4"  # default catalog layout
                            data_entry["screenshots"][screenshot_index]["photo_details"] = analysis_text
                    break
            
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(site_data_store, f, indent=2)
        
        data_queue.task_done()

# -----------------------------
# PLAYWRIGHT CRAWLER FUNCTIONS
# -----------------------------
def extract_links(page):
    links = page.evaluate("""
    () => Array.from(document.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.href }));
    """)
    cleaned, seen = [], set()
    for link in links:
        href = link["href"]
        if not href or not href.startswith("http"): continue
        href = clean_url(href).split("#")[0].strip()
        if href in seen: continue
        href = seen.add(href) or href
        
        text = link["text"]
        if not text:
            parsed = urlparse(href)
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) > 1:
                fallback_segment = parts[1]
                text = fallback_segment.replace("-", " ").replace("_", " ").strip().title()
            elif len(parts) == 1:
                text = parts[0].replace("-", " ").replace("_", " ").strip().title()
            else:
                text = "Home"

        cleaned.append({"text": text, "url": href})
    return cleaned

def build_groups(links):
    groups = defaultdict(list)
    for link in links:
        if not should_skip(link["url"]):
            groups[get_group(link["url"])].append(link)
    return dict(sorted(groups.items(), key=lambda item: len(item[1]), reverse=True))

def capture_screenshots(page, url, output_base, item_data):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        page_height = page.evaluate("document.body.scrollHeight")
        positions = [0, int(page_height * 0.35)]
        priorities = [1.0, 0.7]

        for i, pos in enumerate(positions):
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(1500)

            filename = f"{output_base}_{i+1}.jpg"
            filepath = os.path.join(SCREENSHOT_DIR, filename)

            page.screenshot(path=filepath, type="jpeg", quality=60, full_page=False)

            with data_lock:
                item_data["screenshots"].append({
                    "path": filepath,
                    "scroll_y": pos,
                    "priority": priorities[i],
                    "layout_aspect_ratio": "Pending extraction...",
                    "photo_details": "Pending AI analysis..." 
                })

            data_queue.put((item_data, i, filepath))

    except Exception as e:
        print(f"[Playwright Error] Failed crawling {url}: {e}")

# -----------------------------
# MAIN PIPELINE EXECUTION
# -----------------------------
def run_scraper_pipeline(start_url: str, force_rescrape: bool = False):
    global OUTPUT_DIR, SCREENSHOT_DIR, output_json, site_data_store

    # 1. Parse domain dynamically to build clean isolated directories
    parsed_url = urlparse(start_url)
    domain = parsed_url.netloc.replace("www.", "")
    safe_domain = "".join(c for c in domain if c.isalnum() or c in "._-").strip()
    if not safe_domain:
        safe_domain = "unknown_destination"

    # Set paths bound directly to this specific target site domain dynamically
    OUTPUT_DIR = os.path.join("site_data", safe_domain)
    SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
    output_json = os.path.join(OUTPUT_DIR, f"{safe_domain}_biodata.json")

    # 2. Local Database Validation Layer & Rescrape Override Option
    if os.path.exists(output_json):
        print(f"\n[Cache Alert] Existing database discovered for site '{safe_domain}' at:")
        print(f" > {output_json}")

        if not force_rescrape:
            print("\n[Cache Hit] Using historical dataset. Bypassing engine crawl routine...")

            with open(output_json, "r", encoding="utf-8") as f:
                site_data_store = json.load(f)

            print(
                f"SUCCESS: Loaded local data map. Current Saved Blueprint Summary:\n"
                f"> {site_data_store.get('global_brand_visual_blueprint')}\n"
            )

            return

        print("\n[Cache Override] Initializing clean overwrite execution sequence...")
    # Build unique tracking folders dynamically
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # Clear previous run memory caches before crawling
    with data_lock:
        site_data_store["global_brand_visual_blueprint"] = "Pending initialization..."
        site_data_store["pages"] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        print(f"Loading custom target destination: {start_url}")
        page.goto(start_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # --- EXTRACT GLOBAL IDENTITY VIA VISUAL LAYERS ---
        homepage_height = page.evaluate("document.body.scrollHeight")
        homepage_positions = [0, int(homepage_height * 0.35)]
        homepage_image_paths = []

        print("[Playwright] Snapshotting homepage layers for visual DNA modeling...")
        for i, pos in enumerate(homepage_positions):
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(1500)
            
            hp_path = os.path.join(SCREENSHOT_DIR, f"homepage_identity_layer_{i+1}.jpg")
            page.screenshot(path=hp_path, type="jpeg", quality=80)
            homepage_image_paths.append(hp_path)

        BRAND_VISUAL_PROMPT = generate_brand_description_from_images(homepage_image_paths)
        
        # Pull layout marker value out of global brand identity output as well
        brand_ratio_match = re.search(r'\*(\d+:\d+)\*', BRAND_VISUAL_PROMPT)
        if brand_ratio_match:
            site_data_store["global_layout_aspect_ratio"] = brand_ratio_match.group(1)
            site_data_store["global_brand_visual_blueprint"] = BRAND_VISUAL_PROMPT.replace(brand_ratio_match.group(0), "").strip()
        else:
            site_data_store["global_layout_aspect_ratio"] = "16:9"
            site_data_store["global_brand_visual_blueprint"] = BRAND_VISUAL_PROMPT

        print(f"\n[Brand Blueprint Saved To Master Key]:\n> {site_data_store['global_brand_visual_blueprint']}\n")

        # Start consumer thread worker
        consumer_thread = threading.Thread(target=replicate_consumer_worker, daemon=True)
        consumer_thread.start()

        links = extract_links(page)
        groups = build_groups(links)

        for group_name, items in groups.items():
            print(f"\n--- PROCESSING GROUP: {group_name} ---")
            for item in items:
                url = item["url"]
                print(f"[Playwright] Snapping: {url}")

                filename_base = safe_filename(url)
                
                data_entry = {
                    "group": group_name,
                    "url": url,
                    "anchor_text": item["text"],
                    "screenshots": [] 
                }
                
                with data_lock:
                    site_data_store["pages"].append(data_entry)

                capture_screenshots(page, url, filename_base, data_entry)
                time.sleep(0.5)

        browser.close()

    print("\n[Playwright] Finished crawling all pages. Waiting for Replicate to catch up...")
    data_queue.put(None)
    consumer_thread.join()
    print(f"\nSUCCESS: Pipeline finished execution perfectly. Dataset saved: {output_json}")

# -----------------------------
# DIRECT TERMINAL EXECUTION TEST
# -----------------------------
if __name__ == "__main__":
    TEST_URL = "https://seeaash.in/" 
    
    print(f"=== Starting Standalone Terminal Test for: {TEST_URL} ===")
    
    if not os.environ.get("REPLICATE_API_TOKEN"):
        print("[WARNING] REPLICATE_API_TOKEN not found in environment. Please check your .env file.")
    
    run_scraper_pipeline(TEST_URL)