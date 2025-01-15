from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from src.modules.experiment.models import ExperimentModel, ExperimentStatus, VariantModel
import src.utils.logger as logger
from datetime import datetime, timezone
from src.modules.csl.repository import get_csl_name, get_locale_name
import traceback

logger = logger.logger

def update_experiment_statuses(
    session: Session, 
    app_id: int,
    running_experiments: List[Dict],
    previous_experiments: List[Dict],
    publisher_id: str,
    app_console_id: str
) -> None:
    """
    Update experiment statuses in database based on running and previous experiments
    
    Args:
        session: Database session
        app_id: App ID
        running_experiments: List of running experiments from Play Console
        previous_experiments: List of previous experiments from Play Console
        publisher_id: Publisher Play Console ID
        app_console_id: App Play Console ID
    """
    try:
        # Update running experiments
        for running in running_experiments:
            experiment = session.query(ExperimentModel).filter(
                ExperimentModel.app_id == app_id,
                ExperimentModel.experiment_name_auto_populated == running["experiment_name"]
            ).first()
            
            if experiment:
                experiment.status = ExperimentStatus.IN_PROGRESS
                experiment.google_play_experiment_id = running["experiment_id"]
                experiment.url = f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_console_id}/store-listing-experiments/{running["experiment_id"]}/report'

        # Update previous experiments
        for previous in previous_experiments:
            if "experiment_id" not in previous or not previous["experiment_id"]:
                continue
                
            experiment = session.query(ExperimentModel).filter(
                ExperimentModel.app_id == app_id,
                ExperimentModel.experiment_name_auto_populated == previous["experiment_name"]
            ).first()
            
            if experiment:
                experiment.status = ExperimentStatus.FINISHED
                experiment.google_play_experiment_id = previous["experiment_id"]
                experiment.url = f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_console_id}/store-listing-experiments/{previous["experiment_id"]}/report'

        session.commit()
    except Exception as e:
        logger.error(f"Error updating experiment statuses: {e}")
        session.rollback() 

def get_ready_experiments(session: Session, app_id: int) -> List[ExperimentModel]:
    """
    Get experiments that are ready to be created
    
    Args:
        session: Database session
        app_id: App ID
        
    Returns:
        List of ready experiments
    """
    try:
        return session.query(ExperimentModel).filter(
            ExperimentModel.app_id == app_id,
            ExperimentModel.status == ExperimentStatus.READY
        ).all()
    except Exception as e:
        logger.error(f"Error getting ready experiments: {e}")
        return []

def mark_experiment_as_error(session: Session, experiment: ExperimentModel, error_message: str) -> None:
    """Mark a single experiment as error"""
    try:
        experiment.status = ExperimentStatus.ERROR
        experiment.error = error_message
        session.commit()
    except Exception as e:
        logger.error(f"Error marking experiment as error: {e}")
        session.rollback()

def update_experiments_with_error(
    session: Session, 
    csl_id: str, 
    locale_id: str, 
    error_message: str
) -> None:
    """Update experiments with error status"""
    try:
        experiments = (
            session.query(ExperimentModel)
            .filter(
                ExperimentModel.status == ExperimentStatus.READY,
                ExperimentModel.csl_id == csl_id,
                ExperimentModel.locale_id == locale_id
            )
            .all()
        )
        
        for experiment in experiments:
            experiment.status = ExperimentStatus.ERROR
            experiment.error = error_message
        
        session.commit()
    except Exception as e:
        logger.error(f"Error updating experiments with error: {e}")
        session.rollback()

def update_experiment_after_creation(
    session: Session,
    experiment: ExperimentModel,
    experiment_id: str,
    url: str
) -> None:
    """Update experiment details after successful creation"""
    try:
        experiment.google_play_experiment_id = experiment_id
        experiment.url = url
        experiment.status = ExperimentStatus.IN_PROGRESS
        session.commit()
    except Exception as e:
        logger.error(f"Error updating experiment after creation: {e}")
        session.rollback() 

def get_next_experiment_and_variants(
    session: Session,
    all_experiments: List[ExperimentModel],
    csls: Dict[str, List[str]],
    running: List[Dict]
) -> Tuple[Optional[ExperimentModel], Optional[List[Dict]], Optional[List[ExperimentModel]]]:
    """
    Get next experiment to create and its variants
    
    Args:
        session: Database session
        all_experiments: List of all experiments
        csls: Dictionary of CSL IDs to locale lists
        running: List of running experiments from Play Console
        
    Returns:
        Tuple of (selected experiment, variants, remaining experiments)
    """
    try:
        # Get ready experiments
        ready_experiments = [
            exp for exp in all_experiments 
            if exp.status == ExperimentStatus.READY
        ]

        if not ready_experiments:
            return None, None, None

        # Process running experiments
        running_listings_locales = set()
        for r in running:
            if "experiment_type" in r and r["experiment_type"] == "Default graphics":
                continue
            running_listings_locales.add(f'{r["store_listing"]}--{r["locale"]}')

        experiments = []
        non_ready_experiments = []

        for experiment in ready_experiments:
            try:
                csl_name = get_csl_name(experiment.csl_id, session)
                number_per_store_listing = _count_experiments_per_store_listing(
                    csl_name,
                    running_listings_locales
                )
                number_of_default_graphics_experiments = len([
                    r for r in running 
                    if r["store_listing"] == experiment.csl_id 
                    and r["experiment_type"] == "Default graphics"
                ])
                # get experiment csl name
                logger.info(f"experiment.csl_id: {experiment.csl_id}, experiment.locale_id: {experiment.locale_id}")
                locale_name = get_locale_name(experiment.locale_id, session).split(" – ")[1]
                
                csl_locale = f'{csl_name}--{locale_name}'
                logger.info(f"csl_locale: {csl_locale}")
                logger.info(f"running_locals_listings: {running_listings_locales}")
                logger.info(f"number_per_store_listing: {number_per_store_listing}")
                logger.info(f"number_of_default_graphics_experiments: {number_of_default_graphics_experiments}")

                if (csl_locale not in running_listings_locales
                    and number_per_store_listing < len(csls[csl_name])
                    and number_per_store_listing < 5
                    and number_of_default_graphics_experiments == 0):
                    experiments.append(experiment)
                else:
                    non_ready_experiments.append(experiment)

            except Exception as e:
                logger.error(f"Error processing experiment: {e}")
                logger.error(traceback.format_exc())
                continue

        if not experiments:
            return None, None, non_ready_experiments

        # Sort by priority
        experiments.sort(key=lambda x: x.priority, reverse=True)

        # Get the first experiment and its variants
        selected_experiment = experiments[0]
        variants = selected_experiment.variants

        return selected_experiment, variants, experiments[1:] + non_ready_experiments

    except Exception as e:
        logger.error(f"Error in get_next_experiment_and_variants: {e}")
        logger.error(traceback.format_exc())
        return None, None, None

def _count_experiments_per_store_listing(csl_name: str, running_csl_locales: set) -> int:
    """
    Count number of experiments for a store listing
    
    Args:
        csl_id: CSL ID
        running_locals_listings: Set of running local listings
        
    Returns:
        Number of experiments for the store listing
    """
    return len([
        r for r in running_csl_locales 
        if r.startswith(f'{csl_name}--')
    ]) 

def get_experiment_attributes(session: Session, experiment: ExperimentModel) -> Dict:
    """
    Get experiment attributes in dictionary format for Play Console
    
    Args:
        session: Database session
        experiment: ExperimentModel instance
        
    Returns:
        Dictionary with experiment attributes
    """
    # Get CSL and locale names using repository functions
    csl_name = get_csl_name(experiment.csl_id, session) or ""
    locale_name = get_locale_name(experiment.locale_id, session) or ""
    
    return {
        "experiment_name_auto_populated": experiment.experiment_name_auto_populated,
        "csl_name": csl_name,
        "locale_name": locale_name,
        "target_metric": experiment.settings.target_metric.value,
        "minimum_detectable_effect": experiment.settings.minimum_detectable_effect.value,
        "confidence_interval": experiment.settings.confidence_interval.value
    }

def get_experiment_variants(experiment: ExperimentModel) -> List[Dict]:
    """
    Get experiment variants in dictionary format for Play Console
    
    Args:
        experiment: ExperimentModel instance
        
    Returns:
        List of variant dictionaries
    """
    variants = []
    for variant in experiment.variants:
        variant_dict = {
            "variant_name": variant.name,
            "short_description": variant.short_description or "",
            "icon": variant.icon or "",
            "feature_graphic": variant.feature_graphic or "",
            "promo_video": variant.promo_video or "",
        }
        
        # Add screenshots
        for i in range(1, 9):
            variant_dict[f"screen{i}"] = getattr(variant, f"screen{i}", "") or ""
            variant_dict[f"screen{i}_7inch"] = getattr(variant, f"screen{i}_7inch", "") or ""
            variant_dict[f"screen{i}_10inch"] = getattr(variant, f"screen{i}_10inch", "") or ""
            
        variants.append(variant_dict)
        
    return variants 