from sqlalchemy import create_engine, inspect, text
import os
from dotenv import load_dotenv
import sys

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def view_table_info():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Get all tables
    for table_name in inspector.get_table_names():
        print(f"\nTable: {table_name}")
        print("-" * 50)
        
        # Get columns
        columns = inspector.get_columns(table_name)
        print("Columns:")
        for column in columns:
            print(f"- {column['name']}: {column['type']}")
        
        # Get sample data
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
            rows = result.fetchall()
            if rows:
                print("\nSample Data:")
                for row in rows:
                    print(row)

if __name__ == "__main__":
    view_table_info() 