from app import app, db
from sqlalchemy import text
import traceback

def update_test_result_table():
    try:
        print("Attempting to update the test_result table...")
        with app.app_context():
            # Check if column exists first
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(test_result)"))
                columns = [row[1] for row in result]
                print(f"Existing columns in test_result: {columns}")
                
                # Add active column if missing
                if 'active' not in columns:
                    print("Adding 'active' column to test_result table...")
                    conn.execute(text("ALTER TABLE test_result ADD COLUMN active BOOLEAN DEFAULT 1 NOT NULL"))
                    conn.commit()
                    print("Added 'active' column successfully")
                else:
                    print("'active' column already exists")
                    
                # Set all existing records to active
                conn.execute(text("UPDATE test_result SET active = 1 WHERE active IS NULL"))
                conn.commit()
                print("Updated existing test results to be active")
                
            print("Database update completed successfully!")
    except Exception as e:
        print(f"Error updating database: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    update_test_result_table() 