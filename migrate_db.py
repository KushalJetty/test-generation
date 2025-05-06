import sqlite3

def migrate_database():
    # Connect to the database
    conn = sqlite3.connect('streamzai.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(test_case)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add name column if it doesn't exist
    if 'name' not in columns:
        print("Adding 'name' column to test_case table...")
        try:
            cursor.execute("ALTER TABLE test_case ADD COLUMN name TEXT DEFAULT 'Unnamed Test'")
        except sqlite3.OperationalError as e:
            print(f"Error adding 'name' column: {e}")
    else:
        print("'name' column already exists")
    
    # Add description column if it doesn't exist
    if 'description' not in columns:
        print("Adding 'description' column to test_case table...")
        try:
            cursor.execute("ALTER TABLE test_case ADD COLUMN description TEXT")
        except sqlite3.OperationalError as e:
            print(f"Error adding 'description' column: {e}")
    else:
        print("'description' column already exists")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Migration completed!")

if __name__ == "__main__":
    migrate_database() 