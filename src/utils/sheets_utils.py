from src.utils.utils import number_of_experiments_per_store_listing
import src.utils.utils as utils
import traceback
from datetime import datetime
from src.clients.sheets import GoogleSheetHandler
import os

EXPERIMENTS_SHEET_NAME = "Automated_Testing_Experiments"
VARIANTS_SHEET_NAME = "Automated_Testing_Variants"
APPS_SHEET = "Publisher/App Settings"



def get_clients_rows():
    """
    Fetch all clients from the admin sheet
    """
    clients_sheet =   GoogleSheetHandler(f"utils/aso_experiments.json", os.getenv("admin_sheet")) #=os.getenv("clients").split(",")
    clients_rows = clients_sheet.get_data_as_dict("add clients")
    return  clients_rows

def get_clients():
    """
    Get all active clients from the admin sheet
    """
    clients = []
    clients_rows = get_clients_rows()
    for row in clients_rows:
        if row["active"] == "TRUE":
            clients.append(row)
    return clients

def get_fetch_csls_manuall_run_clients():
    """
    Get only manual run clients from the admin sheet
    """
    clients = []
    clients_rows = get_clients_rows()
    for row in clients_rows:
        if row["fetch_csl_data"] == "TRUE":
            clients.append(row)
    return clients

def get_max_experiment_id(sheets, sheet_name=EXPERIMENTS_SHEET_NAME):
    """
    Get max experiment id from the sheet
    """
    experiments = sheets.get_data_as_dict(sheet_name)
    max_id = 0
    if len(experiments) == 1:
        return 0
    for e in experiments:
        if e["internal_experiment_id"] > max_id:
            max_id = e["internal_experiment_id"]
    return max_id


def get_all_experiments(sheets):
    experiments = sheets.get_data_as_dict(EXPERIMENTS_SHEET_NAME)
    varinats = sheets.get_data_as_dict(VARIANTS_SHEET_NAME)
    for e in experiments:
        e["variants"] = []
        for v in varinats:
            if v["internal_experiment_id"] == e["internal_experiment_id"]:
                e["variants"].append(v)
    return experiments


def get_apps(sheets, app_id=None, manual=False, sheet_name="Publisher/App Settings"):
    """
    Get all apps from the sheet
    sheets: GoogleSheetHandler
    app_id: str (optional) - The app id to filter the apps
    """
    apps = []
    rows = sheets.get_data_as_dict(sheet_name)
    for row in rows:
        # get apps with automated_testing on
        if row["automated_testing"] == "on":
            # if app_id is not None get this app only
            if app_id is not None and row["Abbreviation"] != app_id:
                continue
            # run_now is TRUE for manual and FALSE for automated
            if row["run_now"] == "TRUE" and manual:
                apps.append(row)
                # set run_now to FALSE again
                sheets.update_sheet_cell_based_on_column_condition(sheet_name, "app_package", row["app_package"], "run_now", "FALSE")
                utils.logger.info(f"Set run_now to FALSE for app_name: {row['App Name']}", )
            elif not manual:
                apps.append(row)
    return apps


def get_all_experiments(sheets, sheet_name=EXPERIMENTS_SHEET_NAME):
    """
    Get all experiments from the sheet
    """
    return sheets.get_data_as_dict(sheet_name)


# def set_experiment_status(sheets, experiment_name, status, sheet_name=EXPERIMENTS_SHEET_NAME):
#     experiments = get_all_experiments(sheets)
#     for e in experiments:
#         if e["experiment_name"] == experiment_name:
#             e["status"] = status
#     sheets.reflect_changes_to_sheet(experiments, sheet_name)

all_experiments = None
all_variants = None

def get_next_experiment_and_variants(sheets, all_experiments, all_variants,  csls, app_id, running):
    try:
        # Experiments which are ready to run
        experiments = []
        # Experiments which are not ready to run
        non_ready_experiments = []
        # Get all running experiments locales and storelistings
        running_locals_listings = [f'{e["store_listing"]}--{e["locale"]}' for e in running]
        utils.logger.info(f"Current running locales and listings: {running_locals_listings}", )
        for experiment in all_experiments:
            # skip all experiments not for this app or not ready
            if experiment["app_id_auto_populated"] != app_id or experiment["status"] != "ready":
                non_ready_experiments.append(experiment)
                continue
            # check if experiment CSL exists in the CSLs
            try:
                csls[experiment["store_listing_auto_populated"]]
            except KeyError:
                sheets.update_sheet_cell_based_on_three_column_conditions(
                            EXPERIMENTS_SHEET_NAME,
                            "status",
                            "ready",
                            "store_listing_auto_populated",
                            experiment["store_listing_auto_populated"],
                            "experiment_type_auto_populated",
                            experiment["experiment_type_auto_populated"],
                            "error",
                            f'error: {experiment["store_listing_auto_populated"]} store listing not found in CSLs',
                        )
                sheets.update_sheet_cell_based_on_three_column_conditions(
                        EXPERIMENTS_SHEET_NAME,
                        "status",
                        "ready",
                        "store_listing_auto_populated",
                        experiment["store_listing_auto_populated"],
                        "experiment_type_auto_populated",
                        experiment["experiment_type_auto_populated"],
                        "status",
                        "error",
                    )
                continue
            

            number_per_store_listing = number_of_experiments_per_store_listing(experiment["store_listing_auto_populated"], running_locals_listings)
            number_of_default_graphics_experiments=len([r for r in running if r["store_listing"] == experiment["store_listing_auto_populated"] and r["experiment_type"] == "Default graphics"])
            # we can run max one experiment per locale per CSL or 1 default graphics experiment
            csl_locale = f'{experiment["store_listing_auto_populated"]}--{experiment["experiment_type_auto_populated"]}'
            # check if experiment csl/locale combination isn't already running

            if csl_locale not in running_locals_listings \
            and number_per_store_listing < len(csls[experiment["store_listing_auto_populated"]]) \
            and number_per_store_listing < 5 \
            and number_of_default_graphics_experiments == 0:
                # utils.logger.info(f"store_listing={experiment['store_listing']} number_per_store_listing= {number_per_store_listing}  max_locals={len(csls[experiment['store_listing']])}")
                experiments.append(experiment)
            # if an experiment already running for this store listing and locale skip
            else:
                non_ready_experiments.append(experiment)
        # if no experiments to start quit
        utils.logger.info(f"number_of_possible_experiments: {len(experiments)}", )
        if len(experiments) == 0:
            return None, None, non_ready_experiments
        # Sort by priority
        experiments = sorted(experiments, key=lambda x: int(x["priority"]), reverse=True)
        for e in experiments[0:20]:
            utils.logger.info(f"id={e['internal_experiment_id']} Experiment: {e['experiment_title']}, type={e['type']} Priority: {e['priority']}", )
        # for e in non_ready_experiments:
        #     utils.logger.info(f"Non ready Experiment: {e['internal_experiment_id']} {e['experiment_title']}")
                                                                                                            
        # Get the first experiment
        experiment = experiments[0]
        # Remove the experiment from the list
        experiments.remove(experiments[0]) 
        # Get the variants for this experiment
        variants = []
        for variant in all_variants:
            if variant["internal_experiment_id"] == experiment["internal_experiment_id"]:
                variants.append(variant)
        # Return the experiment and variants
        return experiment, variants, experiments + non_ready_experiments  # Return the rest
    except Exception as e:
        utils.logger.error(f"Error in get_next_experiment_and_variants: {e}", )
        utils.logger.error(traceback.format_exc())
        return None, None, None

def update_the_experiments_sheet(sheets, publisher_id, app_id, running, experiment, rest, number_of_created, experiments_sheet_name=EXPERIMENTS_SHEET_NAME):
    """
    Update the experiment sheet with the running experiments as in_progress
    """
    # 5- loop over current running and update the sheet
    for r in running:
        # Update the experiment in sheet
        if experiment is not None:
            if r["experiment_name"] == experiment["experiment_name_auto_populated"] and number_of_created > 0:
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name,"experiment_name_auto_populated", experiment["experiment_name_auto_populated"], "google_play_experiment_id", f'{r["experiment_id"]}')
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name, "experiment_name_auto_populated", experiment["experiment_name_auto_populated"], "url", f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_id}/store-listing-experiments/{r["experiment_id"]}/report')
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name, "experiment_name_auto_populated", experiment["experiment_name_auto_populated"], "status", "in_progress")
        # Update all running experiments in sheet
        if rest is not None:
            for e in rest:
                if r["experiment_name"] == e["experiment_name_auto_populated"]:
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name, "experiment_name_auto_populated", e["experiment_name_auto_populated"], "google_play_experiment_id", f'{r["experiment_id"]}')
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name, "experiment_name_auto_populated", e["experiment_name_auto_populated"], "url", f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_id}/store-listing-experiments/{r["experiment_id"]}/report')
                    sheets.update_sheet_cell_based_on_column_condition(experiments_sheet_name, "experiment_name_auto_populated", e["experiment_name_auto_populated"], "status", "in_progress")        

def update_the_experiment_sheet_with_previous(sheets, publisher_id, app_id, previous_experiments, rest):
    """
    Update the experiment sheet with the previous experiments as finished
    """
    if rest is None:
        return
    sheets_names = [r["experiment_name_auto_populated"] for r in rest]
    # loop over previous experiments and update the sheet
    for p in previous_experiments:
        # only update if the experiment is in the sheet and has an experiment id
        if p["experiment_name"] in sheets_names and len(p.get("experiment_id","")) > 0:
            sheets.update_sheet_cell_based_on_column_condition(EXPERIMENTS_SHEET_NAME, "experiment_name_auto_populated", p["experiment_name"], "google_play_experiment_id", f'{p["experiment_id"]}')
            sheets.update_sheet_cell_based_on_column_condition(EXPERIMENTS_SHEET_NAME, "experiment_name_auto_populated", p["experiment_name"], "url", f'https://play.google.com/console/u/0/developers/{publisher_id}/app/{app_id}/store-listing-experiments/{p["experiment_id"]}/report')
            sheets.update_sheet_cell_based_on_column_condition(EXPERIMENTS_SHEET_NAME, "experiment_name_auto_populated", p["experiment_name"], "status", "finished")