from database import SessionLocal
from db_models import Brand

def get_brand(domain):
    db = SessionLocal()

    try:
        return (
            db.query(Brand)
            .filter(Brand.domain == domain)
            .first()
        )
    finally:
        db.close()

def get_brand_dataset(domain):
    db = SessionLocal()

    try:
        brand = (
            db.query(Brand)
            .filter(Brand.domain == domain)
            .first()
        )

        if not brand:
            return None

        result = {
            "global_brand_visual_blueprint":
                brand.visual_blueprint,

            "global_layout_aspect_ratio":
                brand.aspect_ratio,

            "pages": []
        }

        for page in brand.pages:

            page_dict = {
                "group": page.group_name,
                "url": page.url,
                "anchor_text": page.anchor_text,
                "screenshots": []
            }

            for screenshot in page.screenshots:

                page_dict["screenshots"].append({
                    "path": screenshot.image_path,
                    "scroll_y": screenshot.scroll_y,
                    "priority": screenshot.priority,
                    "layout_aspect_ratio":
                        screenshot.aspect_ratio,
                    "photo_details":
                        screenshot.photo_details
                })

            result["pages"].append(page_dict)

        return result

    finally:
        db.close()