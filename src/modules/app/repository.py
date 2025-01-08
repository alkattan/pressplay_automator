from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from src.modules.app.models import AppModel, AppStatus
from src.modules.csl.models import CSLModel
from src.utils.logger import get_logger
from src.database.connection import get_db_session
from datetime import datetime, timezone, timedelta
logger = get_logger(__name__)

def get_publisher_apps(publisher_id: int, session: Session) -> List[AppModel]:
    """
    Get all apps for a publisher with CSLs and locales eagerly loaded
    
    Args:
        publisher_id: Publisher ID
        session: Database session
        
    Returns:
        List of AppModel instances with related CSLs and locales loaded
    """
    try:
        apps = (session.query(AppModel)
               .filter(AppModel.publisher_id == publisher_id)
               .filter(AppModel.status == AppStatus.ACTIVE)
               .options(
                   joinedload(AppModel.csls).joinedload(CSLModel.locales)
               )
               .all())
        
        return apps
    except Exception as e:
        logger.error(f"Error fetching apps for publisher {publisher_id}: {e}")
        return []

def get_app_csls(app: AppModel) -> Dict[str, List[str]]:
    """
    Get CSLs and their locales for an app
    
    Args:
        app: AppModel instance with eagerly loaded CSLs and locales
        
    Returns:
        Dictionary mapping CSL IDs to lists of locale names
    """
    try:
        return {
            csl.id: [locale.name for locale in csl.locales] 
            for csl in app.csls
        }
    except Exception as e:
        logger.error(f"Error getting CSLs for app {app.package_id}: {e}")
        return {}

def update_app_sync_status(app: AppModel, session: Session) -> None:
    """
    Update app sync status after processing
    
    Args:
        app: AppModel instance to update
        session: Database session
    """
    try:
        app.last_sync = datetime.now(timezone.utc)
        app.next_sync = app.last_sync + timedelta(hours=3)
        app.sync_now = False
        session.commit()
    except Exception as e:
        logger.error(f"Error updating sync status for app {app.package_id}: {e}")
        session.rollback() 