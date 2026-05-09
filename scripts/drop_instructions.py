import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text

def main():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE food_items DROP COLUMN instructions;"))
    print("Column 'instructions' dropped successfully.")

if __name__ == "__main__":
    main()
