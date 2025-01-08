from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import MYSQL
from sqlalchemy.orm import DeclarativeBase
from contextlib import contextmanager, AbstractContextManager
from typing import Callable
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import create_engine, orm, exc
from src.utils.logger import get_logger
from sqlalchemy.engine.url import URL

logger = get_logger(__name__)

class Base(DeclarativeBase):
    pass

def create_db_engine():
    """Create SQLAlchemy engine from settings"""
    connection_url = URL.create(
        "mysql+mysqlconnector",
        username=MYSQL['USER'],
        password=MYSQL['PASSWORD'],
        host=MYSQL['HOST'],
        port=MYSQL['PORT'],
        database=MYSQL['DATABASE']
    )
    
    return Database(connection_url)

def get_db_session() -> Session:
    """Get SQLAlchemy session"""
    engine = create_db_engine()
    SessionLocal = sessionmaker(bind=engine.engine)
    return SessionLocal()

class Database:
    """
    Database connection manager for SQLAlchemy sessions.
    
    This class manages database connections and provides a context manager
    for safe session handling, including automatic cleanup and rollback
    on exceptions.
    
    Attributes:
        engine: SQLAlchemy engine instance
        _session_factory: Scoped session factory for creating new sessions
    """

    def __init__(self, db_url: str, echo: bool = False) -> None:
        """
        Initialize database connection manager.
        
        Args:
            db_url: Database connection URL
            echo: If True, enables SQLAlchemy's debug logging (default: False)
        """
        # Create SQLAlchemy engine with connection pool settings
        self.engine = create_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600,   # Recycle connections after 1 hour
            pool_size=5,         # Maximum number of connections
            max_overflow=10      # Allow up to 10 connections over pool_size
        )
        
        # Create thread-safe session factory
        self._session_factory = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            ),
        )

    @contextmanager
    def session(self):
        """
        Provide a transactional scope around a series of operations.
        
        Yields:
            Session: SQLAlchemy session object
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()