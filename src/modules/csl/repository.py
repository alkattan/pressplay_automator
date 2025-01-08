from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.modules.csl.models import CSLModel, LocaleModel
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_csl_name(csl_id: int, session: Session) -> Optional[str]:
    """
    Get CSL name by ID
    
    Args:
        csl_id: CSL ID
        session: Database session
        
    Returns:
        CSL name if found, None otherwise
    """
    try:
        csl = session.query(CSLModel).filter(CSLModel.id == csl_id).first()
        if csl is None:
            logger.error(f"CSL with ID {csl_id} not found")
            return None
        return csl.name
    except Exception as e:
        logger.error(f"Error getting CSL name for ID {csl_id}: {e}")
        return None


def get_locale_name(locale_id: int, session: Session) -> Optional[str]  :
    try:
        locale = session.query(LocaleModel).filter(LocaleModel.id == locale_id).first()
        if locale is None:
            logger.error(f"Locale with ID {locale_id} not found")
            return None
        return locale.name
    except Exception as e:
        logger.error(f"Error getting Locale name for ID {locale_id}: {e}")
        return None

def add_csls(session: Session, csls_data: List[Dict]) -> None:
    """
    Add CSLs and locales to database, preserving existing CSLs and their IDs
    
    Args:
        session: Database session
        csls_data: List of CSL data dictionaries
    """
    try:
        # Group CSLs by app and play_console_id
        csls_by_app = {}
        for csl_data in csls_data:
            app = csl_data["app"]
            app_id = app.id  # Get the app's ID instead of using the app object
            
            if app_id not in csls_by_app:
                csls_by_app[app_id] = {}
            
            csl_id = csl_data["csl_play_console_id"]
            if csl_id not in csls_by_app[app_id]:
                csls_by_app[app_id][csl_id] = []
            
            csls_by_app[app_id][csl_id].append(csl_data)

        # Process each app's CSLs
        for app_id, app_csls in csls_by_app.items():
            # Get all existing CSLs for this app in one query with composite key
            existing_csls = {}
            for csl in (session.query(CSLModel)
                       .filter(CSLModel.app_id == app_id)
                       .all()):
                key = f"{app_id}_{csl.play_console_id}"
                existing_csls[key] = csl

            for csl_id, csl_entries in app_csls.items():
                # Use composite key to find existing CSL
                composite_key = f"{app_id}_{csl_id}"
                
                if composite_key in existing_csls:
                    # CSL exists, only check for new locales
                    existing_csl = existing_csls[composite_key]
                    
                    # Get existing locale associations
                    existing_locale_names = {
                        locale.name for locale in existing_csl.locales
                    }
                    
                    # Add only new locales and associations
                    for entry in csl_entries:
                        locale_name = entry["locale"]
                        if locale_name not in existing_locale_names:
                            # Check if locale exists in database
                            locale = (session.query(LocaleModel)
                                    .filter(LocaleModel.name == locale_name)
                                    .first())
                            
                            if not locale:
                                # Create new locale if it doesn't exist
                                locale = LocaleModel(name=locale_name)
                                session.add(locale)
                                session.flush()
                            
                            # Add association
                            existing_csl.locales.append(locale)
                            logger.info(f"Added new locale {locale_name} to existing CSL {csl_id} (ID: {existing_csl.id})")
                else:
                    # Create new CSL
                    new_csl = CSLModel(
                        app_id=app_id,
                        play_console_id=csl_id,
                        name=csl_entries[0]["name"]
                    )
                    session.add(new_csl)
                    session.flush()  # Get the new CSL ID

                    # Add locales and associations for new CSL
                    for entry in csl_entries:
                        locale_name = entry["locale"]
                        
                        # Check if locale exists
                        locale = (session.query(LocaleModel)
                                .filter(LocaleModel.name == locale_name)
                                .first())
                        
                        if not locale:
                            # Create new locale if it doesn't exist
                            locale = LocaleModel(name=locale_name)
                            session.add(locale)
                            session.flush()
                        
                        # Add association
                        new_csl.locales.append(locale)
                    
                    logger.info(f"Added new CSL {csl_id} with {len(csl_entries)} locales (ID: {new_csl.id})")

        session.commit()
        
    except Exception as e:
        logger.error(f"Error adding CSLs: {e}")
        session.rollback()
        raise