import os
import re
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json"
}

URL = "https://api.replicate.com/v1/models/google/nano-banana-2/predictions"

def _to_data_url(image_bytes, filename=None):
    mime = "image/jpeg"
    if filename:
        ext = filename.lower().split(".")[-1]
        if ext == "png": mime = "image/png"
        elif ext == "webp": mime = "image/webp"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _dispatch_single_pose(final_prompt, target_ratio, image_input):
    """Worker sub-routine to send prediction request to Replicate instantly."""
    payload = {
        "input": {
            "prompt": final_prompt,
            "resolution": "1K",
            "image_input": image_input,
            "aspect_ratio": target_ratio,
            "image_search": False,
            "google_search": False,
            "output_format": "jpg"
        }
    }
    try:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "prediction_id": data.get("id"),
                "status": data.get("status", "starting"),
                "prompt_type": final_prompt[:30]
            }
        else:
            print(f"[Worker Error] HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[Worker Exception] Request failed: {str(e)}")
        return None

def get_option(options, key):
    if not options:
        return None

    item = options.get(key)

    if not item:
        return None

    if item.get("mode") == "AI_SELECTED":
        return None

    if item.get("mode") == "CUSTOM":
        return item.get("custom")

    return item.get("mode")

def process_request(prompt, aspect_ratio="3:4", options=None, images_bytes_list=None, image_filenames_list=None):
    """Dispatches multiple pose generation loops concurrently using multi-threaded workers."""
    raw_blocks = [p.strip() for p in prompt.split("---") if p.strip()]
    override_text = ""

    if options:

        for key in options:

            value = get_option(options, key)

            if value:

                override_text += f"\n{key}: {value}"
    
    image_input = []
    if images_bytes_list:
        for idx, img_bytes in enumerate(images_bytes_list):
            filename = image_filenames_list[idx] if image_filenames_list and idx < len(image_filenames_list) else None
            image_input.append(_to_data_url(img_bytes, filename))

    tasks_to_dispatch = []

    for block in raw_blocks:
        is_page_prompt = "Pose A:" in block
        base_prompt_match = re.search(r"Base Prompt:\s*(.*?)(?=\nPose A:|$)", block, re.DOTALL)
        base_text = base_prompt_match.group(1).strip() if base_prompt_match else block.strip()
        pose_matches = re.findall(r"Pose [A-C]:\s*(.*?)(?=\nPose [A-C]:|$)", block, re.DOTALL)

        if is_page_prompt:
            ratio_match = re.search(r"\*\s*(\d+:\d+)\s*\*", block)
            target_ratio = ratio_match.group(1) if ratio_match else aspect_ratio
        else:
            target_ratio = aspect_ratio
            pose_matches = [""]

        for pose_text in pose_matches[:3]:
            raw_combined_text = f"{base_text}, {pose_text.strip()}".strip(", ")
            final_prompt = (
                f"Context: Preserve the exact clothing type, hemlines, color, and garment style shown in the provided image.\n\n"

                f"Action: {raw_combined_text}\n\n"

                f"IMPORTANT INSTRUCTIONS:\n"
                f"1. Use all information from the Action section above.\n"
                f"2. Use the USER OVERRIDES section below as additional requirements.\n"
                f"3. If a USER OVERRIDE conflicts with an earlier instruction, replace ONLY the conflicting detail.\n"
                f"4. Keep all non-conflicting details from the original prompt.\n\n"

                f"USER OVERRIDES:\n"
                f"{override_text}"
            )
            tasks_to_dispatch.append((final_prompt, target_ratio))

    prediction_trackers = []
    
    max_workers = max(1, len(tasks_to_dispatch))


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_dispatch_single_pose, prompt_text, ratio, image_input)
            for prompt_text, ratio in tasks_to_dispatch
        ]
        for future in as_completed(futures):
            res = future.result()
            if res and res.get("prediction_id"):
                prediction_trackers.append(res)

    return {
        "status": "dispatched",
        "trackers": prediction_trackers
    }