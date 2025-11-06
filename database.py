from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Database connection - lazy initialization
engine = None
SessionLocal = None
_db_available = False

def initialize_database():
    """Initialize database connection if available"""
    global engine, SessionLocal, _db_available
    
    try:
        from models import Base
        from config import DATABASE_URL
        
        # Only create engine if DATABASE_URL is set and not a default placeholder
        if DATABASE_URL and "postgresql://" in DATABASE_URL:
            engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            # Test connection
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            _db_available = True
            logger.info("Database connection initialized successfully")
            return True
        else:
            logger.info("Database URL not configured, skipping database initialization")
            return False
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Running without database.")
        _db_available = False
        return False

def create_tables():
    """Create all database tables"""
    if not _db_available:
        raise Exception("Database not available")
    
    try:
        from models import Base
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise

def get_db():
    """Dependency to get database session - yields None if database unavailable"""
    if not _db_available or engine is None or SessionLocal is None:
        yield None
        return
    
    try:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        yield None
