import sys
sys.path.append('.')

from app.core.database import SessionLocal, engine
from sqlalchemy import text

def add_about_us_column():
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='salons' AND column_name='about_us'
        """))
        
        if result.fetchone() is None:
            print("Adding about_us column to salons table...")
            db.execute(text("""
                ALTER TABLE salons 
                ADD COLUMN about_us TEXT
            """))
            db.commit()
            print("Successfully added about_us column")
        else:
            print("about_us column already exists")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_about_us_column()
