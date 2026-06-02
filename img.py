import json
import re
import os

# Global memory caches to handle tracking for multiple brand directories safely
site_biodata_cache = {}
last_modified_cache = {}


def load_json_if_changed(brand_domain: str) -> str:
    """
    Normalizes incoming website URLs or domains, locates their respective
    JSON data file within 'site_data', and checks file modification times 
    to reload memory states only when hot updates occur on the system disk.
    """
    global site_biodata_cache, last_modified_cache

    # Normalize URLs down to root folders cleanly (e.g., "https://nike.in/men" -> "nike.in")
    clean_domain = (
        brand_domain.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .split("/")[0]
        .strip()
    )

    # Map directly into your custom workspace asset storage pathing rules
    json_path = os.path.join("site_data", clean_domain, f"{clean_domain}_biodata.json")

    try:
        if not os.path.exists(json_path):
            print(f"[WARNING] Requested structural dataset path not found: {json_path}")
            return json_path

        current_modified = os.path.getmtime(json_path)

        # Hot-reload from disk only if the file is new or has been modified since last read
        if json_path not in site_biodata_cache or current_modified != last_modified_cache.get(json_path, 0):
            with open(json_path, "r", encoding="utf-8") as f:
                site_biodata_cache[json_path] = json.load(f)

            last_modified_cache[json_path] = current_modified
            print(f"[INFO] Global Memory Cache hot-reloaded for domain: {clean_domain}")

    except Exception as e:
        print(f"[ERROR] Critical failure parsing brand disk matrix for {clean_domain}: {e}")

    return json_path


def search_brand_blueprint(search_input: str, brand_domain: str) -> dict:
    """
    Queries the localized dataset of a specific brand domain context. Aggregates both 
    exact matching categories and partial alternatives to hand total selection visibility 
    over to the user interface layer, completely avoiding early direct prompt returns.
    """
    # 1. Dynamically target, resolve, and load the correct brand profile JSON
    json_path = load_json_if_changed(brand_domain)
    data = site_biodata_cache.get(json_path, {})

    # Extract our primary structures
    global_fallback = data.get("global_brand_visual_blueprint", "")
    global_ratio = data.get("global_layout_aspect_ratio", "16:9")  # <-- Grab global ratio
    pages = data.get("pages", [])

    # 2. Tokenize and normalize user input parameters
    search_input_lower = search_input.lower().strip()
    search_words = set(re.findall(r"\w+", search_input_lower))

    if not search_words:
        return {"type": "prompt", "data": global_fallback, "global_layout_aspect_ratio": global_ratio}

    # 3. Scan and identify distinct demographic groups dynamically present in the source logs
    available_groups = {
        page.get("group", "").lower() for page in pages if page.get("group")
    }

    # See if the search query contains one of our isolated master groups (e.g., "men", "women")
    matched_groups = search_words.intersection(available_groups)

    # 4. Filter pages based on demography to avoid mixed cross-matches
    if matched_groups:
        target_group = list(matched_groups)[0]
        filtered_pages = [
            p for p in pages if p.get("group", "").lower() == target_group
        ]
        anchor_search_words = search_words - matched_groups
        if not anchor_search_words:
            anchor_search_words = search_words
    else:
        filtered_pages = pages
        anchor_search_words = search_words

    suggestions = []

    # 5. Evaluate all pages to assemble active matches
    for page in filtered_pages:
        anchor_text = page.get("anchor_text", "").strip()
        if not anchor_text:
            continue

        anchor_text_lower = anchor_text.lower()
        anchor_words = set(re.findall(r"\w+", anchor_text_lower))
        
        exact_match_count = len(anchor_search_words.intersection(anchor_words))
        is_exact = exact_match_count > 0

        is_partial = False
        if not is_exact:
            for word in anchor_search_words:
                if word == "men" and "women" in anchor_text_lower:
                    continue
                if word in anchor_text_lower or any(word in aw for aw in anchor_words):
                    is_partial = True
                    break

        if is_exact or is_partial:
            if anchor_text not in [s["text"] for s in suggestions]:
                prompt_payload = extract_page_prompts(page, global_fallback)
                suggestions.append({
                    "text": anchor_text,
                    "is_exact": is_exact,
                    "is_group_filler": False,
                    "group": page.get("group", "").strip(),
                    "raw_url": page.get("url", "") or "",
                    "prompt": prompt_payload["data"]
                })

    # 6. DYNAMIC FILLER ADDITION
    active_group = None
    if matched_groups:
        active_group = list(matched_groups)[0]
    elif suggestions:
        active_group = suggestions[0]["group"].lower()
    elif available_groups:
        active_group = sorted(list(available_groups))[0]

    if active_group:
        for page in pages:
            if page.get("group", "").lower() == active_group:
                anchor_text = page.get("anchor_text", "").strip()
                if not anchor_text:
                    continue
                
                if anchor_text not in [s["text"] for s in suggestions]:
                    prompt_payload = extract_page_prompts(page, global_fallback)
                    suggestions.append({
                        "text": anchor_text,
                        "is_exact": False,
                        "is_group_filler": True,
                        "group": page.get("group", "").strip(),
                        "raw_url": page.get("url", "") or "",
                        "prompt": prompt_payload["data"]
                    })

    if suggestions:
        suggestions.sort(key=lambda x: (x.get("is_group_filler", False), not x.get("is_exact", False)))
        return {"type": "suggestions", "data": suggestions, "global_layout_aspect_ratio": global_ratio}

    return {"type": "prompt", "data": global_fallback, "global_layout_aspect_ratio": global_ratio}


def extract_page_prompts(page: dict, fallback: str) -> dict:
    """
    Helper function to safely extract clean visual detail layers from 
    a validated page target while ensuring errors and missing elements are dropped.
    """
    screenshots = page.get("screenshots", [])
    prompts = []

    for snap in screenshots:
        details = snap.get("photo_details", "").strip()
        ratio = snap.get("layout_aspect_ratio", "3:4")  # <-- Pull layout ratio out of JSON structure
        details_lower = details.lower()

        if (
            details
            and "analysis failed" not in details_lower
            and "pending" not in details_lower
            and "no_human_subject" not in details_lower
        ):
            # FIXED: Bake the ratio back into the text block for nano.py to catch natively
            prompts.append(f"{details}\n*{ratio}*")

    if prompts:
        return {"type": "prompt", "data": "\n\n---\n\n".join(prompts)}
    
    return {"type": "prompt", "data": fallback}

if __name__ == "__main__":
    print("=== Standalone Engine Verification Layer ===")
    brand_input = input("Enter target brand domain or full URL context: ").strip()
    user_query = input("Enter category filter search query terms: ").strip()

    result_payload = search_brand_blueprint(user_query, brand_input)

    print("\n" + "=" * 30 + " SYSTEM PROMPT EXECUTION OUTPUT " + "=" * 30)
    print(f"Payload Type: {result_payload['type']}")
    print("-" * 72)
    if result_payload["type"] == "suggestions":
        print("Matches found! Comprehensive options collection:")
        for item in result_payload["data"]:
            status = "[EXACT MATCH]" if item["is_exact"] else "[PARTIAL]"
            print(f" -> {status} [{item['group'].upper()}] {item['text']} ({item['raw_url']})")
    else:
        print(result_payload["data"])
    print("=" * 92 + "\n")