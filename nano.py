import os
import re
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
    "Prefer": "wait"
}

URL = "https://api.replicate.com/v1/models/google/nano-banana-2/predictions"


def process_request(prompt, aspect_ratio="16:9", image_bytes=None, image_filename=None):
    print(f"\n[Nano Engine] Aspect Ratio: {aspect_ratio}")

    raw_blocks = [p.strip() for p in prompt.split("---") if p.strip()]
    generated_image_urls = []

    image_input = []

    # Convert uploaded image into data URL
    if image_bytes:
        mime = "image/jpeg"

        if image_filename:
            ext = image_filename.lower().split(".")[-1]

            if ext == "png":
                mime = "image/png"
            elif ext == "webp":
                mime = "image/webp"

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        image_input = [
            f"data:{mime};base64,{b64}"
        ]

    for b_idx, block in enumerate(raw_blocks):

        is_page_prompt = "Pose A:" in block

        base_prompt_match = re.search(
            r"Base Prompt:\s*(.*?)(?=\nPose A:|$)",
            block,
            re.DOTALL
        )

        base_text = (
            base_prompt_match.group(1).strip()
            if base_prompt_match
            else block.strip()
        )

        pose_matches = re.findall(
            r"Pose [A-C]:\s*(.*?)(?=\nPose [A-C]:|$)",
            block,
            re.DOTALL
        )

        if is_page_prompt:
            ratio_match = re.search(
                r"\*\s*(\d+:\d+)\s*\*",
                block
            )

            target_ratio = (
                ratio_match.group(1)
                if ratio_match
                else aspect_ratio
            )

        else:
            target_ratio = aspect_ratio
            pose_matches = [""]

        for pose_text in pose_matches[:3]:

            final_prompt = f"{base_text}, {pose_text.strip()}".strip(", ")

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

            print("\n========================")
            print("BLOCK:", b_idx + 1)
            print("FINAL PROMPT:")
            print(final_prompt)
            print("ASPECT RATIO:", target_ratio)
            print("IMAGE ATTACHED:", len(image_input) > 0)
            print("========================\n")

            response = requests.post(
                URL,
                headers=HEADERS,
                json=payload
            )

            print(response.status_code)

            if response.status_code not in [200, 201]:
                print(response.text)
                continue

            data = response.json()
            print("\nFULL REPLICATE RESPONSE:")
            print(data)

            output = data.get("output")

            if isinstance(output, list):
                generated_image_urls.extend(output)

            elif isinstance(output, str):
                generated_image_urls.append(output)

            time.sleep(1)

    return {
        "status": "success",
        "images": generated_image_urls
    }