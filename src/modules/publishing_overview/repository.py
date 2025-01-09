from typing import List, Optional
from sqlalchemy.orm import Session
from src.modules.publishing_overview.models import PublishingOverviewModel
import src.utils.logger as logger
from datetime import datetime, timezone

logger = logger.logger

def get_pending_publishing_changes(session: Session, app_id: int) -> List[PublishingOverviewModel]:
    """
    Get pending publishing changes for an app
    
    Args:
        session: Database session
        app_id: App ID
        
    Returns:
        List of pending publishing changes
    """
    try:
        return session.query(PublishingOverviewModel).filter(
            PublishingOverviewModel.app_id == app_id,
            PublishingOverviewModel.publish_decision == False,
            PublishingOverviewModel.review_decision == False
        ).all()
    except Exception as e:
        logger.error(f"Error getting pending publishing changes: {e}")
        return []

def create_publishing_change(
    session: Session,
    app_id: int,
    changes: str,
    publish_decision: bool = False,
    review_decision: bool = False
) -> Optional[PublishingOverviewModel]:
    """
    Create a new publishing change record
    
    Args:
        session: Database session
        app_id: App ID
        changes: Description of changes
        publish_decision: Whether changes are published
        review_decision: Whether changes are reviewed
        
    Returns:
        Created PublishingOverviewModel instance or None if error
    """
    try:
        publishing_change = PublishingOverviewModel(
            app_id=app_id,
            changes=changes,
            publish_decision=publish_decision,
            review_decision=review_decision,
            created_at=datetime.now(timezone.utc)
        )
        session.add(publishing_change)
        session.commit()
        return publishing_change
    except Exception as e:
        logger.error(f"Error creating publishing change: {e}")
        session.rollback()
        return None

def update_publishing_decisions(
    session: Session,
    publishing_change_id: int,
    publish_decision: bool = True,
    review_decision: bool = True
) -> bool:
    """
    Update publishing and review decisions
    
    Args:
        session: Database session
        publishing_change_id: Publishing change ID
        publish_decision: New publish decision value
        review_decision: New review decision value
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        publishing_change = session.query(PublishingOverviewModel).get(publishing_change_id)
        if publishing_change:
            publishing_change.publish_decision = publish_decision
            publishing_change.review_decision = review_decision
            session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating publishing decisions: {e}")
        session.rollback()
        return False 