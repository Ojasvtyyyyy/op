from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv
from models import Base

# Load environment variables
load_dotenv()

def init_database():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Handle special case for Render PostgreSQL URL
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        return engine, SessionLocal
        
    except OperationalError as e:
        # If database doesn't exist, create it
        if "database" in str(e) and "does not exist" in str(e):
            # Create default database
            default_db_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
            temp_engine = create_engine(default_db_url)
            
            # Connect with autocommit to create database
            conn = temp_engine.connect()
            conn.execute(text("commit"))
            
            # Get database name from URL
            db_name = DATABASE_URL.rsplit('/', 1)[1]
            
            # Create database
            conn.execute(f"CREATE DATABASE {db_name}")
            conn.close()
            
            # Try again with the new database
            engine = create_engine(DATABASE_URL)
            Base.metadata.create_all(engine)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            return engine, SessionLocal
        else:
            raise

if __name__ == "__main__":
    init_database() 