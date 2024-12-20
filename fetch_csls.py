import os
from src.clients.play_console_driver import PlayConsoleDriver
from src.utils.sheets_utils import get_apps, get_clients, get_fetch_csls_manuall_run_clients
from src.clients.sheets import GoogleSheetHandler
from dotenv import load_dotenv
import src.utils.utils as utils
import argparse
from src.modules.publisher.repository import get_publishers_with_apps
from src.modules.csl.models import CSLModel, LocaleModel
from src.modules.app.models import AppModel
from sqlalchemy import select
from src.modules.csl.service import add_csls
from src.database.connection import get_db_session
from datetime import datetime, timezone, timedelta
from src.modules.app.schemas import AppStatus
load_dotenv()

gpc = None

 

def main(client_id=None, manuall=None):
    global gpc
    publishers = get_publishers_with_apps()
    for publisher in publishers:
        fetch_csls(publisher)
    if gpc is not None:
        gpc.clean()
        


def fetch_csls(publisher):
    """
    Fetch current CSLs for all the client sheets apps from the play console
    """
    global gpc
    all_csls = _fetch_all_csls(publisher)
    apps_data = _process_csls_by_app(all_csls)
    _update_database(publisher, apps_data)

def _fetch_all_csls(publisher):
    """Fetch CSLs for all apps from the publisher"""
    global gpc
    all_csls = []
    
    for app in publisher.apps:
        if not _should_fetch_app_csls(app):
            continue
            
        gpc = _ensure_gpc_initialized(gpc, publisher, app)
        csls = _fetch_app_csls(gpc, publisher, app)
        if csls:
            all_csls.extend(csls)
            
    return all_csls

def _should_fetch_app_csls(app):
    """Check if app CSLs should be fetched"""
    return app.status == AppStatus.ACTIVE or app.status == AppStatus.CONNECTING

def _ensure_gpc_initialized(gpc, publisher, app):
    """Ensure Google Play Console driver is initialized"""
    if gpc is None:
        gpc = PlayConsoleDriver(
            publisher,
            app,
            email=os.getenv("email"),
            password=os.getenv("password"),
            otp_code=os.getenv("otp_code")
        )
    return gpc

def _fetch_app_csls(gpc, publisher, app):
    """Fetch CSLs for a single app"""
    utils.logger_app_package = app.package_id
    utils.logger = utils.get_logger(utils.logger_app_package)
    utils.logger.info(f"Getting CSLS for {app.package_id}")
    
    gpc.set_app(publisher, app)
    csls = gpc.get_store_csls()
    
    if len(csls) == 0:
        utils.logger.info(f'No CSLs for this {app.package_id}')
        return None
        
    return gpc.get_csls_possible_locales(csls)

def _process_csls_by_app(all_csls):
    """Process and group CSLs by app"""
    apps_data = {}
    for csl in all_csls:
        app = csl["app"]
        if app not in apps_data:
            apps_data[app] = []
        
        for locale in csl["locales"]:
            record = {
                "app": app,
                "csl_play_console_id": csl["csl_play_console_id"],
                "name": csl["name"],
                "locale": locale,
            }
            apps_data[app].append(record)
    return apps_data

def _update_database(publisher, apps_data):
    """Update database with new CSL data"""
    with get_db_session() as session:
        for app, data in apps_data.items():
            add_csls(session, data)
        
        _update_app_sync_status(session, publisher)
        session.commit()

def _update_app_sync_status(session, publisher):
    """Update sync status for all publisher apps"""
    now = datetime.now(timezone.utc)
    for app in publisher.apps:
        app.sync_now = False
        app.last_sync = now
        app.next_sync = now + timedelta(hours=12)




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CSLs from Play Console")

    # Specify the type as int, but also allow None as a default value

    parser.add_argument(
        "--client_id", type=int, default=None, help="an integer for the client ID"
    )

    parser.add_argument(
        "--manuall", type=str, default=None, help="manuall Run based on admin panel"
    )

    # Parse the command-line arguments
    args = parser.parse_args()
    main(client_id=args.client_id, manuall=args.manuall)
