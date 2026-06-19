import os
import json

from database import SessionLocal
from db_models import Brand, Page, Screenshot


def sync_json_to_db(json_path: str):

    db = SessionLocal()

    try:

        if not os.path.exists(json_path):
            print(f"JSON not found: {json_path}")
            return

        domain = (
            os.path.basename(json_path)
            .replace("_biodata.json", "")
        )

        print(f"Syncing {domain}")

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        existing_brand = (
            db.query(Brand)
            .filter(Brand.domain == domain)
            .first()
        )

        if existing_brand:

            print(f"{domain} already exists")

            return

        brand = Brand(
            domain=domain,
            visual_blueprint=data.get(
                "global_brand_visual_blueprint",
                ""
            ),
            aspect_ratio=data.get(
                "global_layout_aspect_ratio",
                ""
            )
        )

        db.add(brand)
        db.flush()

        for page_data in data.get("pages", []):

            page = Page(
                brand_id=brand.id,
                group_name=page_data.get("group"),
                url=page_data.get("url"),
                anchor_text=page_data.get("anchor_text")
            )

            db.add(page)
            db.flush()

            for screenshot_data in page_data.get(
                "screenshots",
                []
            ):

                screenshot = Screenshot(
                    page_id=page.id,
                    image_path=screenshot_data.get(
                        "path"
                    ),
                    photo_details=screenshot_data.get(
                        "photo_details"
                    ),
                    aspect_ratio=screenshot_data.get(
                        "layout_aspect_ratio"
                    ),
                    scroll_y=screenshot_data.get(
                        "scroll_y"
                    ),
                    priority=screenshot_data.get(
                        "priority"
                    )
                )

                db.add(screenshot)

        db.commit()

        print(
            f"Successfully synced {domain}"
        )

    except Exception as e:

        db.rollback()

        print(
            f"Error syncing {domain}: {e}"
        )

    finally:

        db.close()