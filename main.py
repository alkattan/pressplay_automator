from dotenv import load_dotenv
import os
from src.clients.play_console_driver import PlayConsoleDriver
import src.utils.logger as logger
from src.services.slack import send_message_to_slack_channel 
import argparse
import time
import traceback
from src.utils.helpers import process_running_experiments
from src.modules.publisher.repository import get_publishers_with_apps
from src.modules.app.models import AppModel
from src.modules.experiment.models import ExperimentModel, ExperimentStatus
from src.database.connection import get_db_session
from sqlalchemy.orm import Session
from src.modules.app.repository import get_publisher_apps, get_app_csls, update_app_sync_status
from src.modules.experiment.repository import update_experiment_statuses, get_next_experiment_and_variants, update_experiments_with_error, update_experiment_after_creation
from typing import List, Dict, Tuple
from src.config.settings import SLACK_HOOKS
load_dotenv(override=True)


gpc = None


def main(app_id: str = None, client_id: int = None, manual: bool = False):
    """
    Main function to run the automation
    
    Args:
        app_id: str Google Play Console App ID
        client_id: int Client ID
        manual: bool If True, only process apps with sync_now=True
    """
    global gpc
    # Get publishers with apps from database
    publishers = get_publishers_with_apps(active_only=True)

    if client_id is not None:
        # Filter for specific publisher if client_id provided
        publishers = [p for p in publishers if p.id == client_id]

    for publisher in publishers:
        logger.logger.info(f"Processing publisher {publisher.name}")
        
        # Filter apps based on manual flag
        apps_to_process = []
        for app in publisher.apps:
            if manual:
                # In manual mode, only process apps with sync_now=True
                if app.sync_now:
                    apps_to_process.append(app)
            else:
                # In automatic mode, process all apps
                apps_to_process.append(app)
        
        # Update publisher's apps to only process the filtered ones
        publisher.apps = apps_to_process
        
        if apps_to_process:
            process_publisher(publisher)

    if gpc is not None:
        gpc.clean()

def process_publisher(publisher):
    """Process on publisher apps"""
    global gpc
    session = get_db_session()
    
    try:
        # Get apps with eager loaded relationships
        apps = get_publisher_apps(publisher.id, session)
        
        if not apps:
            return
            
        # Initialize GPC with first app
        app = apps[0]
        if gpc is None:
            gpc = PlayConsoleDriver(
                publisher,
                app,
                email=os.getenv("email"),
                password=os.getenv("password"),
                otp_code=os.getenv("otp_code"),
                session=session
            )

        # Process each app
        for app in apps:
            try:
                logger.logger_app_package = app.package_id
                logger.logger = logger.get_logger(logger.logger_app_package)
                
                # Get CSLs mapping
                csls = get_app_csls(app)
                print(f"csls: {csls}")
                # Run automation
                automate_experiments_for_app(session, app, gpc, csls)
                
                # Update sync status
                update_app_sync_status(app, session)
                
            except Exception as e:
                logger.logger.error(str(e))
                logger.logger.error(f"Error in processing app {app.package_id}")
                logger.logger.error(traceback.format_exc())
                continue
    finally:
        session.close()

def automate_experiments_for_app(session, app: AppModel, gpc: PlayConsoleDriver, csls):
    """
    Run experiments automation for an app
    
    Args:
        session: Database session
        app: App model instance
        gpc: Play Console driver instance
        csls: Dictionary mapping CSL IDs to locale names
    """
    logger.logger.info("-------------------------------------")
    logger.logger.info(f"Running experiments automation for app {app.package_id}")

    # Set the app for the GPC Driver
    gpc.set_publisher_app(app.publisher, app)

    # 1- Check if we have console access
    # response = gpc.check_url(gpc.experiments_url)
    # if response == False:
    #     logger.logger.error(f"Cannot load the app page {app.package_id}")
    #     return False

    # 2- Accept publishing changes
    logger.logger.info("\n2- Accept Publishing Changes")
    # gpc.accept_publishing_changes()
    
    # 3- Get running experiments
    running_experiments = gpc.get_running_experiments(csls)
    print(f"running_experiments: {running_experiments}")
    # 4- Process running experiments
    number_of_applied, number_of_stopped = process_running_experiments(
        running_experiments, 
        app, 
        gpc, 
        session
    )
    
    # 5- Refresh running experiments if any changes
    if number_of_applied > 0 or number_of_stopped > 0:
        running_experiments = gpc.get_running_experiments(csls)

    # 6- Create new experiments
    logger.logger.info("\n6- Create experiments")
    number_of_created, rest = create_experiments(
        running_experiments,
        app.experiments,
        gpc,
        csls,
        app.publisher.play_console_id,
        app.play_console_id,
        app.package_id,
        session,
        SLACK_HOOKS['PHITURE_BUGS'],
        SLACK_HOOKS['PHITURE_HOOK'],
        app.slack_hook_url,
    )

    # 7- Accept any pending changes
    # gpc.accept_publishing_changes()

    # 8- Refresh running experiments if new ones created
    if number_of_created > 0:
        running_experiments = gpc.get_running_experiments(csls)

    # 9- Get previous experiments
    logger.logger.info("\n8- Fetch Previous Changes")
    previous_experiments = gpc.get_previous_experiments(csls)

    # 10- Update experiment statuses in database
    update_experiment_statuses(
        session,
        app.id,
        running_experiments,
        previous_experiments,
        app.publisher.play_console_id,
        app.play_console_id
    )

    # Log results
    logger.logger.info(f"number_of_stopped_experiments={number_of_stopped}")
    logger.logger.info(f"number_of_applied_experiments={number_of_applied}")
    logger.logger.info(f"number_of_created_experiments={number_of_created}")
    logger.logger.info(
        f"Max experiments are running {len(running_experiments)} for app {app.package_id}"
    )

def create_experiments(
    running: List[Dict],
    all_experiments: List[ExperimentModel],
    gpc: PlayConsoleDriver,
    csls: Dict[str, List[str]],
    publisher_id: str,
    app_id: str,
    app_package: str,
    session: Session,
    phiture_bugs_hook: str,
    phiture_hook: str,
    slack_hook: str,
) -> Tuple[int, List[ExperimentModel]]:
    """
    Keep creating experiments until we either hit the limit or tries
    or no more experiments to create
    """
    number_of_created = 0
    logger.logger.info("check if we can create experiments")

    for t in range(40):  # Max 5 experiments at a time per csl
        created_message = ""
        experiment, variants, rest = get_next_experiment_and_variants(
            session, all_experiments, csls, running
        )
        print(f"experiment: {experiment}")
        print(f"variants: {variants}")
        print(f"rest: {rest}")
        if experiment is None:
            logger.logger.info(
                f"No more experiment to run for {app_package} and possible csls running={len(running)}"
            )
            break

        logger.logger.info(f"Try={t} We can run a new experiment running={len(running)}")
        logger.logger.info("---------------------")
        logger.logger.info(experiment)

        # Create priority experiments to the limit
        for creation_try in range(3):
            created, error = gpc.create_experiment(experiment, variants, publisher_id, app_id)
            
            # if experiment is created
            if created:
                logger.logger.info(
                    f'Experiment {experiment.experiment_name_auto_populated} created'
                )
                created_message = f""":large_blue_circle: Experiment {experiment.experiment_name_auto_populated}
CSL={experiment.csl_id}  
Locale={experiment.locale_id}\n
:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually
"""
                number_of_created += 1
                
                # Update experiment in database
                experiment_url = f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_id}/store-listing-experiments/{experiment.google_play_experiment_id}/report'
                update_experiment_after_creation(session, experiment, experiment.google_play_experiment_id, experiment_url)

                # Get running experiments after creating a new one
                running = gpc.get_running_experiments(csls)
                break
                
            # if experiment isn't created
            else:
                logger.logger.warning(
                    f'Experiment {experiment.experiment_name_auto_populated} not created try={creation_try}'
                )
                try:
                    gpc.page.reload()
                    time.sleep(15)
                except Exception as e:
                    logger.logger.info(e)
                    
                if creation_try >= 2:
                    logger.logger.error(
                        f'Cannot create the experiment {experiment.experiment_name_auto_populated} so setting the CSL {experiment.csl_id} to error running={len(running)}'
                    )
                    if error:
                        update_experiments_with_error(
                            session,
                            experiment.csl_id,
                            experiment.locale_id,
                            error
                        )
                        send_message_to_slack_channel(
                            phiture_bugs_hook,
                            f"""experiment={experiment.experiment_name_auto_populated}
                            variants={variants}
                            """,
                            error,
                            "",
                            f"App {app_package}",
                            "Pressplay",
                            "",
                            "#0000FF",
                            "Low",
                        )
                    break

        # Send Slack messages for created experiments
        if created_message:
            send_message_to_slack_channel(
                phiture_hook,
                created_message,
                "Created Play console Experiments",
                "",
                f"App {app_package}",
                "Pressplay",
                "",
                "#0000FF",
                "Low",
            )
            if slack_hook and slack_hook != phiture_hook:
                send_message_to_slack_channel(
                    slack_hook,
                    created_message,
                    "Created Play console Experiments",
                    "",
                    f"App {app_package}",
                    "Pressplay",
                    "",
                    "#0000FF",
                    "Low",
                )

    return number_of_created, rest

def _update_experiment_after_creation(session, publisher_id, app_id, running_experiments, experiment, rest, created):
    """Update experiment details after successful creation"""
    for r in running_experiments:
        if r["experiment_name"] == experiment.experiment_name_auto_populated and created:
            experiment.google_play_experiment_id = r["experiment_id"]
            experiment.url = f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_id}/store-listing-experiments/{r["experiment_id"]}/report'
            experiment.status = ExperimentStatus.IN_PROGRESS
            session.commit()

def _update_experiments_with_error(session, csl_id, locale_id, error_message):
    """Update experiments with error status"""
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

def _mark_experiment_as_error(session, experiment, error_message):
    """Mark a single experiment as error"""
    experiment.status = ExperimentStatus.ERROR
    experiment.error = error_message
    session.commit()

def _count_experiments_per_store_listing(csl_id, running_locals_listings):
    """Count number of experiments for a store listing"""
    return len([
        r for r in running_locals_listings 
        if r.startswith(f'{csl_id}--')
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASO experiments automation.")

    parser.add_argument(
        "--app_id", 
        type=str, 
        default=None, 
        help="app shortcut"
    )
    
    parser.add_argument(
        "--client_id", 
        type=int, 
        default=None, 
        help="an integer for the client ID"
    )

    parser.add_argument(
        "--manual", 
        type=bool, 
        default=False, 
        help="If True, only process apps with sync_now=True"
    )

    args = parser.parse_args()
    
    main(args.app_id, args.client_id, args.manual)