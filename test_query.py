from database import SessionLocal
from db_models import Brand

db = SessionLocal()

brands = db.query(Brand).all()

for brand in brands:
    print(brand.id)
    print(brand.domain)