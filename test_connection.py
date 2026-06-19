# test_connection.py

from sqlalchemy import create_engine

DATABASE_URL = (
    "postgresql://postgres:root@localhost:5432/fashion_ai"
)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Connected successfully!")
