from app import app, db
from sqlalchemy import text
import traceback

def fix_database():
    try:
        print("Attempting to fix the test_case table...")
        with app.app_context():
            # Check if columns exist first
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(test_case)"))
                columns = [row[1] for row in result]
                print(f"Existing columns: {columns}")
                
                # Add name column if missing
                if 'name' not in columns:
                    print("Adding 'name' column...")
                    conn.execute(text("ALTER TABLE test_case ADD COLUMN name TEXT DEFAULT 'Unnamed Test'"))
                    conn.commit()
                    print("Added 'name' column successfully")
                else:
                    print("'name' column already exists")
                
                # Add description column if missing
                if 'description' not in columns:
                    print("Adding 'description' column...")
                    conn.execute(text("ALTER TABLE test_case ADD COLUMN description TEXT"))
                    conn.commit()
                    print("Added 'description' column successfully")
                else:
                    print("'description' column already exists")
                    
                # Set default names for existing test cases
                conn.execute(text("UPDATE test_case SET name = 'Test for ' || original_file_path WHERE name IS NULL"))
                conn.commit()
                print("Updated existing test cases with default names")
                
            print("Database fix completed successfully!")
    except Exception as e:
        print(f"Error fixing database: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    fix_database() 