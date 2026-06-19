# relationship_test.py

from database import SessionLocal
from db_models import Brand

db = SessionLocal()

brand = db.query(Brand).first()

print("Brand:", brand.domain)

for page in brand.pages:
    print("Page:", page.url)

    for screenshot in page.screenshots:
        print("Screenshot:", screenshot.image_path)