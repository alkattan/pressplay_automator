from dotenv import load_dotenv
import os
from src.clients.google.sheets import GoogleSheetHandler
from clients.google.play_console_driver import PlayConsoleDriver
from utils.sheets_utils import (
    get_apps,
    get_all_experiments,
    update_the_experiments_sheet,
    update_the_experiment_sheet_with_previous,
    get_next_experiment_and_variants,
    get_clients,
    EXPERIMENTS_SHEET_NAME,
    VARIANTS_SHEET_NAME,
    APPS_SHEET
)
from utils.utils import (get_target_csls, 
                         get_experiment_by_name, 
                         convert_to_percentage,
                         get_sent_wins,
                         save_sent_wins,
                         )
import utils.utils as utils
from src.slack import send_message_to_slack_channel
from datetime import datetime, timedelta
import typer
import argparse
import time
import traceback

load_dotenv(override=True)


gpc = None
# Define the experiments sheet
# typer_app = typer.Typer()



# @typer_app.command()
# def main(app_id: int = typer.Option(None, help="Google Play Console App ID")):
def main(app_id: str = None, client_id: int = None, manual: bool=False):
    """
    Main function to run the automation
    app_id: str Google Play Console App ID
    client_id: int Client ID
    manual: bool Manual run
    """
    global gpc
    # Get clients sheets_ids from .env
    clients = get_clients()

    if client_id is not None:
        client = clients[client_id]
        clients = [client]

    print(clients)
    for row in clients:
        sheets_id = row["google_sheets"].split("/d/")[1].split("/edit")[0]
        # Define the experiments sheet
        client_spreadsheet = GoogleSheetHandler(f"utils/aso_experiments.json", sheets_id)

        apps = get_apps(client_spreadsheet, app_id, manual)
        if len(apps) == 0:
            utils.logger.info(f"No app found for client {sheets_id}, app_id {app_id} maybe manual run?")
            continue
        all_experiments = client_spreadsheet.get_data_as_dict(EXPERIMENTS_SHEET_NAME)
        all_variants = client_spreadsheet.get_data_as_dict(VARIANTS_SHEET_NAME)
        process_client(client_spreadsheet, apps, all_experiments, all_variants)
    if gpc is not None:
        gpc.clean()


def process_client(sheets, apps, all_experiments, all_variants):
    """
    Process on client apps
    """
    global gpc
    # Get first app to initialize the GPC browser
    app = apps[0]

    if gpc is None:
        # Login to Google Play Console
        gpc = PlayConsoleDriver(
            app,
            email=os.getenv("email"),
            password=os.getenv("password"),
            otp_code=os.getenv("otp_code"),
            sheets=sheets,
        )

    for app in apps:
        try:
            utils.logger_app_package = app["app_package"]
            utils.logger = utils.get_logger(utils.logger_app_package)
            csls = get_target_csls(sheets, app["app_package"])
            automate_experiments_for_app(
                sheets, app, gpc, csls, all_experiments, all_variants
            )
        except Exception as e:
            utils.logger.error(str(e))
            utils.logger.error(f"Error in processing app {app['app_package']}")
            utils.logger.error(traceback.format_exc())
            continue


def experiment_negative_performance_kill(experiment, sheet_experiment):
    """
    Kill the experiment if all variants have negative performance
    """
    try:
        kill_performance_value = float(sheet_experiment["kill_performance_value"])
    except Exception:
        kill_performance_value = 0
    # if all tested variants are negative kill the experiment
    variants = experiment["variants"]
    variants_without_control = [variant for variant in variants if variant["name"] != "Current listing"]
    need_to_kill = all(
        [
            (
                True
                if v["performance_end"] < kill_performance_value
                and v["performance_start"] < kill_performance_value
                else False
            )
            for v in variants_without_control
        ]
    )
    start_time = experiment["start_time"]
    running_for_days = (datetime.now() - start_time).days
    # kill if performance for all variants is below zero and max duration days passed
    if need_to_kill and running_for_days >= sheet_experiment["max_duration_days"]:
        return True
    return False


def experiment_1000_installs_kill(experiment, sheet_experiment):
    """
    Kill the experiment if the variant has more than 1000 installs
    and the conversion is less than -2.5%
    """
    min_installs = int(sheet_experiment["early_kill_min_installs"])
    try:
        cvr = float(sheet_experiment["early_kill_cvr_decrease"])
    except ValueError:
        return False, ""

    variants = experiment["variants"]

    utils.logger.info(variants)
    len_variants = len(variants)
    if len_variants == 2:
        current_variant = variants[0]
        variant = variants[1]
        if variant["installs"] < min_installs:
            return False, f"{variant['installs']} < {min_installs}"
        conversion_improvement = (
            variant["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]
        message = f"""- Variant {variant['name']}:
            installs={variant['installs']} 
            conversion_improvement={round(conversion_improvement*100,2)}
        """
        if conversion_improvement <= cvr:
            return True, message
        else:
            return False, message
    if len_variants == 3:
        current_variant = variants[0]
        variant = variants[1]
        variant2 = variants[2]

        # Check if at least 1 variant installs > 1000 (min_installs)
        if variant["installs"] < min_installs and variant2["installs"] < min_installs:
            return False, f"Both variants installs < {min_installs}"
        conversion_improvement_variant1 = (
            variant["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]
        conversion_improvement_variant2 = (
            variant2["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]

        message = f"""- Variant {variant['name']}:
            installs={variant['installs']} 
            conversion_improvement={round(conversion_improvement_variant1*100,2)}
        - Variant {variant2['name']}:
            installs={variant2['installs']}
            conversion_improvement={round(conversion_improvement_variant2*100,2)}
        """
        if (
            conversion_improvement_variant1 <= cvr
            and conversion_improvement_variant2 <= cvr
        ):
            return True, message
        else:
            return False, message
    if len_variants == 4:
        current_variant = variants[0]
        variant = variants[1]
        variant2 = variants[2]
        variant3 = variants[3]

        # Check if at least 1 variant installs < 1000
        if (
            variant["installs"] < min_installs
            and variant2["installs"] < min_installs
            and variant3["installs"] < min_installs
        ):
            return False, f"One variants installs < {min_installs}"
        conversion_improvement_variant1 = (
            variant["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]
        conversion_improvement_variant2 = (
            variant2["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]
        conversion_improvement_variant3 = (
            variant3["installs_scaled"] - current_variant["installs_scaled"]
        ) / current_variant["installs_scaled"]
        message = f"""- Variant {variant['name']}:
            installs={variant['installs']} 
            conversion_improvement={round(conversion_improvement_variant1*100,2)}
        - Variant {variant2['name']}:
            installs={variant2['installs']}
            conversion_improvement={round(conversion_improvement_variant2*100,2)} 
        - Variant {variant3['name']}:
            installs={variant3['installs']}
            conversion_improvement={round(conversion_improvement_variant3*100,2)} 
        """

        if (
            conversion_improvement_variant1 <= cvr
            and conversion_improvement_variant2 <= cvr
            and conversion_improvement_variant3 <= cvr
        ):
            return True, message
        else:
            return False, message


def create_experiments(
    running,
    all_experiments,
    all_variants,
    gpc,
    csls,
    publisher_id,
    app_id,
    app_package,
    sheets,
    phiture_bugs_hook,
    phiture_hook,
    slack_hook,
):
    """
    Keep creating experiments until we either hit the limit or tries
    or no more experiments to create
    """
    number_of_created = 0
    utils.logger.info("check if we can create experiments")

    for t in range(40):  # Max 5 experiments at a time per csl
        created_message = ""
        experiment, variants, rest = get_next_experiment_and_variants(
            sheets, all_experiments, all_variants, csls, app_id, running
        )
        if experiment is None:
            utils.logger.info(
                f"No more experiment to run for {app_package} and possible csls running={len(running)}"
            )
            break

        utils.logger.info(f"Try={t} We can run a new experiment running={len(running)}")
        utils.logger.info("---------------------")
        utils.logger.info(experiment)
        # Create priority experiments to the limit
        for creation_try in range(3):
            created, error = gpc.create_experiment(experiment, variants, publisher_id, app_id)
            # if experiment is created
            if created:
                utils.logger.info(
                    f'Experiment {experiment["experiment_name_auto_populated"]} created'
                )
                # messages.append(
                created_message =f""":large_blue_circle: Experiment {experiment["experiment_name_auto_populated"]}
CSL={experiment["store_listing_auto_populated"]}  
Locale={experiment["experiment_type_auto_populated"]}\n
:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually
"""
                
                number_of_created += 1
                sheets.update_sheet_cell_based_on_column_condition(
                    EXPERIMENTS_SHEET_NAME,
                    "experiment_name_auto_populated",
                    experiment["experiment_name_auto_populated"],
                    "status",
                    "in_progress",
                )

                # Get running experiments after creating a new one only
                running = gpc.get_running_experiments(csls)
                update_the_experiments_sheet(
                    sheets, publisher_id, app_id, running, experiment, rest, created
                )
                break
            # if experiment isn't created
            else:
                utils.logger.warning(
                    f'Experiment {experiment["experiment_name_auto_populated"]} not created try={creation_try}'
                )
                # Reload the page
                try:
                    gpc.page.reload()
                    time.sleep(15)
                except Exception as e:
                    utils.logger.info(e)
                if creation_try >= 2:
                    utils.logger.error(
                        f'Cannot create the experiment {experiment["experiment_name_auto_populated"]} so setting the CSL {experiment["store_listing_auto_populated"]} to error running={len(running)}'
                    )
                    # if there is an error message. Set all the experiments with the same store listing to error
                    if error:
                        sheets.update_sheet_cell_based_on_three_column_conditions(
                            EXPERIMENTS_SHEET_NAME,
                            "status",
                            "ready",
                            "store_listing_auto_populated",
                            experiment["store_listing_auto_populated"],
                            "experiment_type_auto_populated",
                            experiment["experiment_type_auto_populated"],
                            "error",
                            error,
                        )
                        send_message_to_slack_channel(
                        phiture_bugs_hook,
                        f"""experiment={experiment}
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
                    # Set all the experiments with the same store listing to error
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
                    # Get all experiments from the sheet again
                    all_experiments = sheets.get_data_as_dict(EXPERIMENTS_SHEET_NAME)
                    break
                # if less than 2 tries just log it
                else:
                    utils.logger.error(
                        f"Current fetched running={len(running)} so getting running experiments again"
                    )
                    running = gpc.get_running_experiments(csls)

        # 12- Send Slack messages
        # created_message = "\n".join(created_message)
        created_message = created_message.strip()
        if len(created_message) > 0:
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
            if len(slack_hook) > 1 and slack_hook != phiture_hook:
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
    # # create message footer
    # if len(messages) > 0:
    #     messages.append("\n:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually")
    return number_of_created, rest#, messages


def send_win_notification_for_experiment(r, sheet_experiment):
    """
    Send a winning notification if applicable
    """
    utils.logger.info("check if we can send a winning notification")
    messages = []
    win_notification = False
    app_id = sheet_experiment["app_id_auto_populated"]
    sent_notifications = get_sent_wins(app_id)

    experiment_name = r["experiment_name"]
    apply_setting = sheet_experiment["apply_setting"]
    start_time = r["start_time"]
    running_for_days = (datetime.now() - start_time).days
    if r["status"] not in [
                "More data needed",
                "Not enough data",
                "Current listing won",
                "Draw"]:
        try:
            advanced_1000_installs_kill, advanced_kill_message = experiment_1000_installs_kill(
                r, sheet_experiment
            )
        except Exception as ad:
            utils.logger.error(str(ad))
            advanced_1000_installs_kill = False
            advanced_kill_message = ""

        winning_variant_name = r["status"].split(" won")[0]
        # check if the same experiment notification has already been sent based on a json file
        # if so don't send it again
        if sent_notifications.get(experiment_name) is not None:
            utils.logger.info(
                f"Experiment {experiment_name} already sent a winning notification"
            )
            return win_notification, messages
        else:
            sent_notifications[experiment_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_sent_wins(sent_notifications, app_id)
            win_notification = True

        messages.append(
            f""":large_green_circle:  {experiment_name}
Experiment has reached all the minimum thresholds.
status={r['status']}
apply_setting={apply_setting}
running_for={running_for_days}
min_days={sheet_experiment['min_duration_days']}
max_days={sheet_experiment['max_duration_days']}
{advanced_kill_message}
            """)

    return win_notification, messages

def stop_losing_experiment(r, sheet_experiment, gpc, sheets):
    utils.logger.info("check if we can stop the experiment")
    messages = []
    stop_decision = False
    experiment_name = r["experiment_name"]
    experiment_id = r["experiment_id"]
    apply_setting = sheet_experiment["apply_setting"]
    start_time = r["start_time"]
    running_for_days = (datetime.now() - start_time).days
    variants = r["variants"]

    performance_kill = experiment_negative_performance_kill(r, sheet_experiment)
    try:
        advanced_1000_installs_kill, advanced_kill_message = experiment_1000_installs_kill(
            r, sheet_experiment
        )
    except Exception as ad:
        utils.logger.error(str(ad))
        advanced_1000_installs_kill = False
        advanced_kill_message = ""
    
    # apply_settings never
    if apply_setting == "never":
        # stop an experiment if it is running for more than max_duration_days
        if running_for_days > sheet_experiment["max_duration_days"]:
            stop_res = gpc.stop_experiment(experiment_id)
            if stop_res:
                utils.logger.info(
                    f"Experiment {experiment_name} stopped due to never apply setting {stop_res}"
                )
                stop_decision = True
                sheets.update_sheet_cell_based_on_column_condition(
                    EXPERIMENTS_SHEET_NAME,
                    "experiment_name_auto_populated",
                    experiment_name,
                    "status",
                    "finished",
                )
                messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
    Killed due to: {r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={sheet_experiment['min_duration_days']} 
    - max_days={sheet_experiment['max_duration_days']}"""
                )
            return stop_decision, messages
        # stop a win experiment if it is running for more than min_duration_days
        if running_for_days >= sheet_experiment["min_duration_days"]:
            apply_min_installs_experiment = False
            apply_min_installs_variants = False
            # and the total installs of the experiment is more than the apply_min_installs_experiment
            if sheet_experiment["apply_min_installs_experiment"] is not None:
                total_installs = 0
                for variant in variants:
                    total_installs += variant["installs"]
                if ( total_installs > sheet_experiment["apply_min_installs_experiment"]):
                    apply_min_installs_experiment = True
            # and all variant have more than the apply_min_installs_variant installs
            if sheet_experiment["apply_min_installs_variants"] is not None:
                apply_min_installs_variants = all(
                    [
                        (
                            True
                            if variant["installs"]
                            > sheet_experiment["apply_min_installs_variants"]
                            else False
                        )
                        for variant in variants
                    ]
                )
            # stop  if the experiment is a win and apply_min_installs_experiment and apply_min_installs_variants
            if apply_min_installs_experiment and apply_min_installs_variants \
            and r["status"] not in ["More data needed", "Not enough data", "Current listing won", "Draw"]:
                stop_res = gpc.stop_experiment(experiment_id)
                if stop_res:
                    utils.logger.info(
                        f"Experiment {experiment_name} stopped due to never apply setting {stop_res}"
                    )
                    stop_decision = True
                    sheets.update_sheet_cell_based_on_column_condition(
                        EXPERIMENTS_SHEET_NAME,
                        "experiment_name_auto_populated",
                        experiment_name,
                        "status",
                        "finished",
                    )
                    messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
    Stopped a Winning Experiment due to reaching min_days: 
    - status={r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={sheet_experiment['min_duration_days']} 
    - max_days={sheet_experiment['max_duration_days']}"""
                )

    if apply_setting == "win":
        if running_for_days >= sheet_experiment["min_duration_days"] \
        and r["status"] in ["Current listing won", "Draw"]:
            apply_min_installs_experiment = False
            apply_min_installs_variants = False
            # and the total installs of the experiment is more than the apply_min_installs_experiment
            if sheet_experiment["apply_min_installs_experiment"] is not None:
                total_installs = 0
                for variant in variants:
                    total_installs += variant["installs"]
                if ( total_installs > sheet_experiment["apply_min_installs_experiment"]):
                    apply_min_installs_experiment = True
            # and all variant have more than the apply_min_installs_variant installs
            if sheet_experiment["apply_min_installs_variants"] is not None:
                apply_min_installs_variants = all(
                    [
                        (
                            True
                            if variant["installs"]
                            > sheet_experiment["apply_min_installs_variants"]
                            else False
                        )
                        for variant in variants
                    ]
                )
            # stop  if the experiment is a win and apply_min_installs_experiment and apply_min_installs_variants
            if apply_min_installs_experiment and apply_min_installs_variants \
            and r["status"] not in ["More data needed", "Not enough data", "Current listing won", "Draw"]:
                stop_res = gpc.stop_experiment(experiment_id)
                if stop_res:
                    utils.logger.info(
                        f"Experiment {experiment_name} stopped due to never apply setting {stop_res}"
                    )
                    stop_decision = True
                    sheets.update_sheet_cell_based_on_column_condition(
                        EXPERIMENTS_SHEET_NAME,
                        "experiment_name_auto_populated",
                        experiment_name,
                        "status",
                        "finished",
                    )
                    messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
    Stopped a Draw Experiment due to reaching min_days: 
    - status={r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={sheet_experiment['min_duration_days']} 
    - max_days={sheet_experiment['max_duration_days']}"""
                )

    # stop experiment if one of the following conditions is met
    if (
        # if the experiment is running for more than max_duration_days
        (
            r["status"]
            in [
                "More data needed",
                "Not enough data",
                "Current listing won",
                "Draw",
            ]
            and running_for_days >= sheet_experiment["max_duration_days"]
        )
        # or if perfromance start and performance end below zero
        or performance_kill
        # or if 1000 installs kill
        or advanced_1000_installs_kill
    ):
        
        utils.logger.info(
            f"\nStop experiment {experiment_name} result={r['status']} running_for={running_for_days} days max={sheet_experiment['max_duration_days']}\n{r}"
        )
        # stop experiment in the console
        stop_result = gpc.stop_experiment(experiment_id)
        utils.logger.info(
            f"Stopped Experiment: {stop_result} performance_start_end_below_zero_kill_with_min_days={performance_kill} advanced_cvr_kill={advanced_1000_installs_kill}\n"
        )
        if stop_result:
            stop_decision = True
            # set_experiment_status(sheets, experiment_name, "finished")
            sheets.update_sheet_cell_based_on_column_condition(
                EXPERIMENTS_SHEET_NAME,
                "experiment_name_auto_populated",
                experiment_name,
                "status",
                "finished",
            )
            # Append Slack message only if the experiment is stopped
            # Current listing won or draw
            if r["status"] in ["Current listing won", "Draw"]:

                messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
Killed due to: {r['status']} 
- running_for={running_for_days} 
- min_days={sheet_experiment['min_duration_days']} 
- max_days={sheet_experiment['max_duration_days']}"""
                )
            # performance start and performance end below zero
            if performance_kill:
                messages.append(
                    f"""\n:red_circle:  Experiment:  {experiment_name}
Killed due to: Minimum duration passed, poor performance
- running_for={running_for_days} 
- min_days={sheet_experiment['min_duration_days']} 
- max_days={sheet_experiment['max_duration_days']}"""
                )
            # 1000 installs kill
            if advanced_1000_installs_kill:
                messages.append(
                    f"""\n:red_circle:   {experiment_name}
Killed due to: Early kill rules 
- running_for={running_for_days} 
- min_days={sheet_experiment['min_duration_days']} 
- max_days={sheet_experiment['max_duration_days']}
- early_kill_rule={round(sheet_experiment['early_kill_cvr_decrease']*100,2)}
- early_kill_min_installs={sheet_experiment['early_kill_min_installs']}
{advanced_kill_message}
"""
                )
    # Running or finished or win
    else:
        utils.logger.info(
            f"Experiment {experiment_name} status={r['status']} running_for={running_for_days} days"
        )

    return stop_decision, messages


def apply_winning_experiment(r, sheet_experiment, gpc, sheets):
    utils.logger.info("check if we can apply the experiment")
    messages = []
    apply_decision = False
    # for all current running experiments
    variants = r["variants"]
    experiment_name = r["experiment_name"]
    experiment_id = r["experiment_id"]
    apply_setting = sheet_experiment["apply_setting"]
    start_time = r["start_time"]
    running_for_days = (datetime.now() - start_time).days
    max_percentile = 0
    max_variant_name = ""

    # Check apply type
    # apply_settings win
    if apply_setting == "win":
        # if not a win continue
        if r["status"] in [
            "More data needed",
            "Not enough data",
            "Current listing won",
            "Draw",
        ]:
            return apply_decision, messages
        # all variant have less than the apply_min_installs_variant installs
        if sheet_experiment["apply_min_installs_variants"] is not None:
            for variant in variants:
                if (
                    variant["installs"]
                    < sheet_experiment["apply_min_installs_variants"]
                ):
                    return apply_decision, messages
        # the total installs of the experiment is less than the apply_min_installs_experiment
        if sheet_experiment["apply_min_installs_experiment"] is not None:
            total_installs = 0
            for variant in variants:
                total_installs += variant["installs"]
            if (
                total_installs
                < sheet_experiment["apply_min_installs_experiment"]
            ):
                return apply_decision, messages
        if running_for_days < sheet_experiment["min_duration_days"]:
            return apply_decision, messages

    # apply_settings on_percentile
    elif apply_setting == "on_percentile":
        # ensure that the min duration time has passed
        if running_for_days < sheet_experiment["min_duration_days"]:
            return apply_decision, messages
        # all variant have less than the apply_min_installs_variant installs
        if sheet_experiment["apply_min_installs_variants"] is not None:
            for variant in variants:
                if (
                    variant["installs"]
                    < sheet_experiment["apply_min_installs_variants"]
                ):
                    return apply_decision, messages
        # the total installs of the experiment is less than the apply_min_installs_experiment
        if sheet_experiment["apply_min_installs_experiment"] is not None:
            total_installs = 0
            for variant in variants:
                total_installs += variant["installs"]
            if (
                total_installs
                < sheet_experiment["apply_min_installs_experiment"]
            ):
                return apply_decision, messages
        # the experiment is in the top percentile
        for variant in variants:
            try:
                variant["percentile"] = variant["performance_end"] / (
                    abs(variant["performance_start"])
                    + abs(variant["performance_end"])
                )
            except ZeroDivisionError:
                variant["percentile"] = 0

            if variant["percentile"] > max_percentile:
                max_percentile = variant["percentile"]
                max_variant_name = variant["name"]
        # IF (performance_end/(absolute(performance_start)+absolute(performance_end)) >= apply_on_percentile): apply
        if variant["percentile"] == max_percentile and variant[
            "percentile"
        ] >= convert_to_percentage(sheet_experiment["apply_on_percentile"]):
            utils.logger.info(
                "Applying experiment on percentile",
                variant["percentile"],
                sheet_experiment["apply_on_percentile"],
            )

            winning_variant_name = max_variant_name
        # don't apply if the winning variant is not in the top percentile
        else:
            return apply_decision, messages
        utils.logger.info(
            f"winning_variant_name={winning_variant_name} percentile={max_percentile} apply_on_percentile={sheet_experiment['apply_on_percentile']}"
        )

    elif apply_setting == "never":
            return apply_decision, messages
    else:
        utils.logger.error(
            f"Unknown apply setting {sheet_experiment['apply_setting']}"
        )
        return apply_decision, messages

    utils.logger.info(
        f"\Applying experiment {experiment_name} {apply_setting} running_for={running_for_days} days max={sheet_experiment['max_duration_days']}\n{r}"
    )
    if "won" in r["status"]:
        winning_variant_name = r["status"].split(" won")[0]
    else:
        print(f"Winnig variant name not found {winning_variant_name}, {r['status']}")
    # win notification
    

    # apply experiment in the console
    res = gpc.apply_experiment(experiment_id, winning_variant_name)
    utils.logger.info(f"Experiment Applied: {res} \n")
    if res:
        apply_decision = True
        utils.logger.info(f"Experiment {experiment_name} applied")
        sheets.update_sheet_cell_based_on_column_condition(
            EXPERIMENTS_SHEET_NAME,
            "experiment_name_auto_populated",
            experiment_name,
            "status",
            "finished",
        )
        # Send Slack message
        messages.append(
            f"""Experiment {experiment_name} applied apply_setting={apply_setting}
winning_variant_name={winning_variant_name} percentile={max_percentile} apply_on_percentile={sheet_experiment['apply_on_percentile']}\n"""
        )
    # already stopped or applied
    else:
        utils.logger.info(
            f"Experiment {experiment_name} status={r['status']} running_for={running_for_days} days could not be applied"
        )
    return apply_decision, messages


def process_running_experiments(running, sheets_all_experiments,  gpc, sheets, app_package, phiture_hook, slack_hook):
    """
    Process the running experiments
    """
    stopped_messages = []
    applied_messages = []
    win_messages = []
    number_of_applied = 0
    number_of_stopped = 0

    for r in running:
        try:
            experiment_name = r["experiment_name"]
            sheet_experiment = get_experiment_by_name(
                experiment_name, sheets_all_experiments
            )
            if sheet_experiment is None:
                # utils.logger.info(
                #     f"Experiment {experiment_name} not found in sheet so we can't stop it {experiment_name}"
                # )
                continue
            

            # send winning notification
            win, win_message = send_win_notification_for_experiment(r, sheet_experiment)
            win_messages.extend(win_message)
            # stop if experiment is losing
            stop, stopped_message = stop_losing_experiment(r, sheet_experiment, gpc, sheets)
            stopped_messages.extend(stopped_message)
            if not stop:
                # apply if experiment is winning
                apply, applied_message= apply_winning_experiment(r, sheet_experiment, gpc, sheets)
                applied_messages.extend(applied_message)
                if apply:
                    number_of_applied +=1
            else:
                number_of_stopped += 1
    


        except Exception as e:
            utils.logger.error(str(e))
            utils.logger.error(
                f"Error in processing experiment {experiment_name} {str(e)}"
            )
            continue
    
    if len(win_messages) > 0:
        win_messages.append("\n:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually")
    if len(stopped_messages) > 0:
        stopped_messages.append("\n:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually")
    if len(applied_messages) > 0:
        applied_messages.append("\n:alphabet-white-exclamation: Note: if auto send for review or auto publish are not set to on for your app, please action this manually")


    # Send Slack messages
    # win notifications
    win_message = "\n".join(win_messages)
    win_message = win_message.strip()
    if len(win_messages) > 0:
        send_message_to_slack_channel(
            phiture_hook,
            win_message,
            "Winning Play console Experiments",
            "",
            f"App {app_package}",
            "Pressplay",
            "",
            "#00FF00",
            "High",
        )
        if len(slack_hook) > 1 and slack_hook != phiture_hook:
            send_message_to_slack_channel(
                slack_hook,
                win_message,
                "Winning Play console Experiments",
                "",
                f"App {app_package}",
                "Pressplay",
                "",
                "#00FF00",
                "High",
            )
    # stopped
    stopped_message = "\n".join(stopped_messages)
    stopped_message = stopped_message.strip()
    if len(stopped_message) > 0:
        send_message_to_slack_channel(
            phiture_hook,
            stopped_message,
            "Stopped Play console Experiments",
            "",
            f"App {app_package}",
            "Pressplay",
            "",
            "#FF0000",
            "High",
        )
        if len(slack_hook) > 1 and slack_hook != phiture_hook:
            send_message_to_slack_channel(
                slack_hook,
                stopped_message,
                "Stopped Play console Experiments",
                "",
                f"App {app_package}",
                "Pressplay",
                "",
                "#FF0000",
                "High",
            )
    # applied
    applied_message = "\n".join(applied_messages)
    applied_message = applied_message.strip()
    if len(applied_messages) > 0:
        send_message_to_slack_channel(
            phiture_hook,
            applied_message,
            "Applied Play console Experiments",
            "",
            f"App {app_package}",
            "Pressplay",
            "",
            "#00FF00",
            "Medium",
        )
        if len(slack_hook) > 1 and slack_hook != phiture_hook:
            send_message_to_slack_channel(
                slack_hook,
                applied_message,
                "Applied Play console Experiments",
                "",
                f"App {app_package}",
                "Pressplay",
                "",
                "#00FF00",
                "Medium",
            )
    return number_of_applied, number_of_stopped
    
    

def automate_experiments_for_app(sheets, app, gpc, csls, all_experiments, all_variants):
    utils.logger.info("-------------------------------------")
    utils.logger.info(f"Running experiments automation for app {app['app_package']}")
    phiture_hook = "https://hooks.slack.com/services/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"
    phiture_bugs_hook = "https://hooks.slack.com/services/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"
    # Get all experiments from the sheet
    sheets_all_experiments = get_all_experiments(sheets)

    # Get app info
    app_package = app["app_package"]
    publisher_id = app["publisher_id"]
    app_id = app["app_id"]
    slack_hook = app["slack_hook"]
    experiment = None

    # Set the app for the GPC Driver
    gpc.set_app(app)

    # 1- Check if we have console access
    # in case we lost access or the play console is not loading
    response = gpc.check_url(gpc.experiments_url)
    if response == False:
        utils.logger.error(f"Cannot load the app page {app_package}")
        return False

    # 2- Get current running experiments from console for this app
    utils.logger.info("\n2- Accept Publishing Changes")
    gpc.accept_publishing_changes()
    
    running = gpc.get_running_experiments(csls)

    number_of_applied, number_of_stopped= process_running_experiments(running, sheets_all_experiments, gpc, sheets, app_package, phiture_hook, slack_hook)
    if number_of_applied > 0 or number_of_stopped > 0:
        running = gpc.get_running_experiments(csls)
    # 6- Create new experiments if there is a place
    utils.logger.info("\n6- Create experiments")
    number_of_created, rest = create_experiments(
        running,
        all_experiments,
        all_variants,
        gpc,
        csls,
        publisher_id,
        app_id,
        app_package,
        sheets,
        phiture_bugs_hook,
        phiture_hook,
        slack_hook,
    )

    gpc.accept_publishing_changes()

    # 7- Refetch running experiments after creating a new one even once
    if number_of_created > 0:
        running = gpc.get_running_experiments(csls)

    # 8- Fetch Previous experiments
    utils.logger.info("\n8- Fetch Previous Changes")
    previous_experiments = gpc.get_previous_experiments(csls)

    # 9- Update the experiment sheet with the previous experiments
    utils.logger.info("9- Update experiment sheet with Previous")
    update_the_experiment_sheet_with_previous(
        sheets, publisher_id, app_id, previous_experiments, rest
    )

    # 10- Update the sheet with the running experiments
    utils.logger.info("10- Update the experiment sheet with the running experiments")
    update_the_experiments_sheet(
        sheets, publisher_id, app_id, running, experiment, rest, number_of_created
    )

    # 11- Log the results
    utils.logger.info(f"number_of_stopped_experiments={number_of_stopped}")
    utils.logger.info(f"number_of_applied_experiments={number_of_applied}")
    utils.logger.info(f"number_of_created_experiments={number_of_created}")
    utils.logger.info(
        f"Max experiments are running {len(running)} for app {app_package}"
    )

      
    
    
    # 13 Update last run for app
    sheets.update_sheet_cell_based_on_column_condition(APPS_SHEET, "app_package", app_package, "last_run", datetime.now().strftime("%Y-%m-%d_%H:%M"))
    sheets.update_sheet_cell_based_on_column_condition(APPS_SHEET, "app_package", app_package, "next_run",(datetime.now()+ timedelta(hours=4)).strftime("%Y-%m-%d_%H:%M"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASO experiments automation.")

    # Add the 'app_id' argument
    # Specify the type as int, but also allow None as a default value
    parser.add_argument(
        "--app_id", type=str, default=None, help="app shortcut"
    )
    parser.add_argument(
        "--client_id", type=int, default=None, help="an integer for the client ID"
    )

    parser.add_argument(
        "--manual", type=bool, default=False, help="A manual run based on the client sheets run_now column"
    )

    # Parse the command-line arguments
    args = parser.parse_args()
    main(args.app_id, args.client_id, args.manual)
    # typer_app()


# TODO An unexpected error has occurred. Please try again. (6F3A10C7)
