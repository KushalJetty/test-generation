import sqlite3
import os

def update_database(db_path):
    print(f"Checking database at {db_path}")
    if not os.path.exists(db_path):
        print(f"Database at {db_path} doesn't exist, skipping...")
        return
        
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if test_case table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_case'")
    if not cursor.fetchone():
        print(f"test_case table doesn't exist in {db_path}, skipping...")
        conn.close()
        return
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(test_case)")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Existing columns in {db_path}: {columns}")
    
    # Add columns if they don't exist
    try:
        if 'name' not in columns:
            print(f"Adding 'name' column to test_case table in {db_path}...")
            cursor.execute("ALTER TABLE test_case ADD COLUMN name TEXT DEFAULT 'Unnamed Test'")
            print(f"'name' column added successfully to {db_path}")
            
        if 'description' not in columns:
            print(f"Adding 'description' column to test_case table in {db_path}...")
            cursor.execute("ALTER TABLE test_case ADD COLUMN description TEXT")
            print(f"'description' column added successfully to {db_path}")
            
        # Update existing test cases with default names based on file paths
        cursor.execute("UPDATE test_case SET name = 'Test for ' || original_file_path WHERE name IS NULL")
        print(f"Updated existing test cases with default names in {db_path}")
        
        # Commit changes
        conn.commit()
        print(f"Updates to {db_path} committed successfully!")
    except sqlite3.Error as e:
        print(f"Error updating {db_path}: {e}")
    finally:
        conn.close()

def main():
    # Check both possible database locations
    print("Starting database update process...")
    update_database('streamzai.db')
    update_database('instance/streamzai.db')
    print("Database update completed!")

if __name__ == "__main__":
    main() 