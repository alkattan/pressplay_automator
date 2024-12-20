from typing import List
from sqlalchemy.orm import Session, joinedload
from src.modules.publisher.models import PublisherModel, PublisherStatus
from src.modules.app.models import AppModel
from src.database.connection import get_db_session
from src.utils.logger import get_logger
import traceback
logger = get_logger(__name__)

def get_publishers_with_apps(active_only: bool = True) -> List[PublisherModel]:
    """
    Get all publishers and their associated apps in a single query
    
    Args:
        active_only: If True, only return active publishers
    
    Returns:
        List of PublisherModel with apps preloaded
    """
    session = get_db_session()
    try:
        query = (
            session.query(PublisherModel)
            .options(
                joinedload(PublisherModel.apps)
            )
        )
        
        if active_only:
            query = query.filter(PublisherModel.status == PublisherStatus.ACTIVE)
            
        publishers = query.all()
        
        # # Log some info about what we found
        # for publisher in publishers:
        #     logger.info(
        #         f"Publisher {publisher.name} (ID: {publisher.id}) "
        #         f"has {len(publisher.apps)} automated testing apps"
        #     )
        #     for app in publisher.apps:
        #         logger.info(
        #             f"- App: {app.name} "
        #             f"(Package: {app.package_id}, "
        #             f"Status: {app.status.value}, "
        #             f"Automated: testing={app.automated_testing}, "
        #             f"review={app.automated_send_for_review}, "
        #             f"publishing={app.automated_publishing})"
        #         )
                
        return publishers
    except Exception as e:
        logger.error(f"Error fetching publishers with apps: {e}")
        traceback.print_exc()
        return []
    finally:
        session.close()

def get_publisher_with_apps(publisher_id: int) -> PublisherModel:
    """
    Get a specific publisher and its apps in a single query
    
    Args:
        publisher_id: ID of the publisher to fetch
    
    Returns:
        PublisherModel with apps preloaded, or None if not found
    """
    session = get_db_session()
    try:
        publisher = (
            session.query(PublisherModel)
            .options(
                joinedload(PublisherModel.apps)
                .filter(AppModel.automated_testing == True)
            )
            .filter(PublisherModel.id == publisher_id)
            .first()
        )
        
        if publisher:
            logger.info(
                f"Found publisher {publisher.name} with "
                f"{len(publisher.apps)} automated testing apps"
            )
            for app in publisher.apps:
                logger.info(
                    f"- App: {app.name} "
                    f"(Package: {app.package_id}, "
                    f"Status: {app.status.value})"
                )
        else:
            logger.warning(f"No publisher found with ID {publisher_id}")
            
        return publisher
    except Exception as e:
        logger.error(f"Error fetching publisher {publisher_id} with apps: {e}")
        return None
    finally:
        session.close()

def get_manual_run_publishers_with_apps() -> List[PublisherModel]:
    """
    Get publishers marked for manual CSL fetch with their apps
    
    Note: This is a placeholder implementation. You might want to add a 
    manual_fetch field to PublisherModel to properly implement this.
    """
    return get_publishers_with_apps(active_only=True)

def get_app_by_package_id(package_id: str) -> AppModel:
    """
    Get an app by its package ID
    
    Args:
        package_id: The package ID of the app to fetch
    
    Returns:
        AppModel or None if not found
    """
    session = get_db_session()
    try:
        app = (
            session.query(AppModel)
            .filter(AppModel.package_id == package_id)
            .first()
        )
        
        if app:
            logger.info(
                f"Found app {app.name} "
                f"(Package: {app.package_id}, "
                f"Publisher: {app.publisher.name})"
            )
        else:
            logger.warning(f"No app found with package ID {package_id}")
            
        return app
    except Exception as e:
        logger.error(f"Error fetching app with package ID {package_id}: {e}")
        return None
    finally:
        session.close() 