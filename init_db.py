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
        
    except Exception as e:
        if "database" in str(e) and "does not exist" in str(e):
            try:
                # Extract database name and create default connection URL
                db_name = DATABASE_URL.rsplit('/', 1)[1]
                default_db_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
                
                # Connect to default postgres database
                temp_engine = create_engine(default_db_url)
                
                # Create new connection with autocommit
                conn = temp_engine.execution_options(isolation_level="AUTOCOMMIT").connect()
                
                # Create database if it doesn't exist
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                conn.close()
                temp_engine.dispose()
                
                # Try again with the new database
                engine = create_engine(DATABASE_URL)
                Base.metadata.create_all(engine)
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                
                return engine, SessionLocal
                
            except Exception as inner_e:
                raise Exception(f"Failed to create database. Original error: {str(e)}. Creation error: {str(inner_e)}") from inner_e
        else:
            raise Exception(f"Database connection failed: {str(e)}") from e

if __name__ == "__main__":
    init_database() 