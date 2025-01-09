from datetime import datetime
from src.utils import utils
from src.utils.file import get_sent_wins, save_sent_wins
from src.services.slack import send_message_to_slack_channel
from src.modules.experiment.models import ExperimentModel
from src.modules.experiment.models import ExperimentStatus, ApplySetting
from typing import List, Dict
from sqlalchemy.orm import Session
from src.modules.app.models import AppModel
from src.clients.play_console_driver import PlayConsoleDriver
from src.modules.experiment.models import ExperimentSettingsModel
from src.config.settings import SLACK_HOOKS
import src.utils.logger as logger

logger = logger.logger

def experiment_negative_performance_kill(experiment, experiment_settings):
    """
    Kill the experiment if all variants have negative performance
    
    Args:
        experiment (dict): Experiment data from Play Console
        experiment_settings (ExperimentSettingsModel): Experiment settings from database
    """
    try:
        kill_performance_value = float(experiment_settings.kill_performance_value)
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
    if need_to_kill and running_for_days >= experiment_settings.max_duration_days:
        return True
    return False


def experiment_1000_installs_kill(experiment, experiment_settings):
    """
    Kill the experiment if the variant has more than min_installs
    and the conversion is less than early_kill_cvr_decrease
    
    Args:
        experiment (dict): Experiment data from Play Console
        experiment_settings (ExperimentSettingsModel): Experiment settings from database
    """
    min_installs = int(experiment_settings.early_kill_min_installs)
    try:
        cvr = float(experiment_settings.early_kill_cvr_decrease)
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

        # Check if at least 1 variant installs > min_installs
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

        # Check if at least 1 variant installs < min_installs
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
        


def send_win_notification_for_experiment(running_experiment : Dict, experiment_settings : ExperimentSettingsModel):
    """
    Send a winning notification if applicable
    
    Args:
        experiment_data (dict): Experiment data from Play Console
        experiment_settings (ExperimentSettingsModel): Experiment settings from database
    """
    utils.logger.info("check if we can send a winning notification")
    messages = []
    win_notification = False
    app_id = running_experiment["app_id"]
    sent_notifications = get_sent_wins(app_id)

    experiment_name = running_experiment["experiment_name"]
    apply_setting = experiment_settings.apply_setting
    start_time = running_experiment["start_time"]
    running_for_days = (datetime.now() - start_time).days
    
    if running_experiment["status"] not in [
                "More data needed",
                "Not enough data",
                "Current listing won",
                "Draw"]:
        try:
            advanced_1000_installs_kill, advanced_kill_message = experiment_1000_installs_kill(
                running_experiment, experiment_settings
            )
        except Exception as ad:
            utils.logger.error(str(ad))
            advanced_1000_installs_kill = False
            advanced_kill_message = ""

        winning_variant_name = running_experiment["status"].split(" won")[0]
        # check if the same experiment notification has already been sent
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
status={running_experiment['status']}
apply_setting={apply_setting}
running_for={running_for_days}
min_days={experiment_settings.min_duration_days}
max_days={experiment_settings.max_duration_days}
{advanced_kill_message}
            """)

    return win_notification, messages

def process_running_experiments(running : List[Dict], app : AppModel, gpc : PlayConsoleDriver, session : Session):
    """
    Process the running experiments
    
    Args:
        running (List[Dict]): List of running experiments from Play Console
        app (AppModel): App model instance
        gpc (PlayConsoleDriver): Play Console driver instance
        session (Session): Database session
    """
    stopped_messages = []
    applied_messages = []
    win_messages = []
    number_of_applied = 0
    number_of_stopped = 0

    for running_experiment in running:
        try:
            experiment_name = running_experiment["experiment_name"]
            experiment = session.query(ExperimentModel).filter(
                ExperimentModel.app_id == app.id,
                ExperimentModel.experiment_name_auto_populated == experiment_name
            ).first()
            
            if not experiment:
                continue

            # send winning notification
            win, win_message = send_win_notification_for_experiment(
                running_experiment, 
                experiment.settings
            )
            win_messages.extend(win_message)
            
            # stop if experiment is losing
            stop, stopped_message = stop_losing_experiment(
                running_experiment, 
                experiment, 
                gpc, 
                session
            )
            stopped_messages.extend(stopped_message)
            
            if not stop:
                # apply if experiment is winning
                apply, applied_message = apply_winning_experiment(
                    running_experiment, 
                    experiment.settings, 
                    gpc, 
                    session
                )
                applied_messages.extend(applied_message)
                if apply:
                    number_of_applied += 1
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
    _send_slack_notifications(
        app,
        win_messages,
        stopped_messages,
        applied_messages
    )
    
    return number_of_applied, number_of_stopped

def _send_slack_notifications(app, win_messages, stopped_messages, applied_messages):
    """Send notifications to Slack channels"""
    phiture_hook = SLACK_HOOKS['PHITURE_HOOK']
    slack_hook = app.slack_hook_url or ""
    
    # win notifications
    win_message = "\n".join(win_messages)
    win_message = win_message.strip()
    if len(win_messages) > 0:
        send_message_to_slack_channel(
            phiture_hook,
            win_message,
            "Winning Play console Experiments",
            "",
            f"App {app.package_id}",
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
                f"App {app.package_id}",
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
            f"App {app.package_id}",
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
                f"App {app.package_id}",
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
            f"App {app.package_id}",
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
                f"App {app.package_id}",
                "Pressplay",
                "",
                "#00FF00",
                "Medium",
            )


def stop_losing_experiment(r, experiment, gpc, session):
    """
    Stop experiment if it meets the stopping criteria
    
    Args:
        r (dict): Experiment data from Play Console
        experiment (ExperimentModel): Experiment from database
        gpc (PlayConsoleDriver): Play Console driver instance
        session (Session): Database session
    """
    experiment_settings = experiment.settings
    stop_decision = False
    messages = []
    experiment_name = r["experiment_name"]
    experiment_id = r["experiment_id"]
    variants = r["variants"]
    start_time = r["start_time"]
    running_for_days = (datetime.now() - start_time).days
    apply_setting = experiment_settings.apply_setting

    # Check if experiment should be stopped based on performance
    try:
        performance_kill = experiment_negative_performance_kill(r, experiment_settings)
        advanced_1000_installs_kill, advanced_kill_message = experiment_1000_installs_kill(
            r, experiment_settings
        )
    except Exception as e:
        utils.logger.error(str(e))
        performance_kill = False
        advanced_1000_installs_kill = False
        advanced_kill_message = ""

    # never apply setting
    if apply_setting == ApplySetting.NEVER:
        if running_for_days >= experiment_settings.min_duration_days:
            stop_res = gpc.stop_experiment(experiment_id)
            if stop_res:
                utils.logger.info(
                    f"Experiment {experiment_name} stopped due to never apply setting {stop_res}"
                )
                stop_decision = True
                
                # Update experiment status in database
                experiment = session.query(ExperimentModel).filter(
                    ExperimentModel.experiment_name_auto_populated == experiment_name
                ).first()
                if experiment:
                    experiment.status = ExperimentStatus.FINISHED
                    session.commit()
                
                messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
    Stopped due to never apply setting: 
    - status={r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={experiment_settings.min_duration_days} 
    - max_days={experiment_settings.max_duration_days}"""
                )
            return stop_decision, messages

        # stop a win experiment if it is running for more than min_duration_days
        if running_for_days >= experiment_settings.min_duration_days:
            apply_min_installs_experiment = False
            apply_min_installs_variants = False
            
            # Check total installs threshold
            if experiment_settings.apply_min_installs_experiment is not None:
                total_installs = sum(variant["installs"] for variant in variants)
                if total_installs > experiment_settings.apply_min_installs_experiment:
                    apply_min_installs_experiment = True
                    
            # Check per-variant installs threshold
            if experiment_settings.apply_min_installs_variants is not None:
                apply_min_installs_variants = all(
                    variant["installs"] > experiment_settings.apply_min_installs_variants
                    for variant in variants
                )

            # Stop if conditions are met
            if (apply_min_installs_experiment and apply_min_installs_variants 
                and r["status"] not in ["More data needed", "Not enough data", "Current listing won", "Draw"]):
                stop_res = gpc.stop_experiment(experiment_id)
                if stop_res:
                    utils.logger.info(
                        f"Experiment {experiment_name} stopped due to winning conditions {stop_res}"
                    )
                    stop_decision = True
                    
                    # Update experiment status
                    experiment = session.query(ExperimentModel).filter(
                        ExperimentModel.experiment_name_auto_populated == experiment_name
                    ).first()
                    if experiment:
                        experiment.status = ExperimentStatus.FINISHED
                        session.commit()
                    
                    messages.append(
                        f"""\n:red_circle:  Experiment: {experiment_name} 
    Stopped a Winning Experiment due to reaching min_days: 
    - status={r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={experiment_settings.min_duration_days} 
    - max_days={experiment_settings.max_duration_days}"""
                    )

    # Handle win apply setting
    if apply_setting == ApplySetting.WIN:
        if (running_for_days >= experiment_settings.min_duration_days 
            and r["status"] in ["Current listing won", "Draw"]):
            apply_min_installs_experiment = False
            apply_min_installs_variants = False
            
            # Check total installs threshold
            if experiment_settings.apply_min_installs_experiment is not None:
                total_installs = sum(variant["installs"] for variant in variants)
                if total_installs > experiment_settings.apply_min_installs_experiment:
                    apply_min_installs_experiment = True
                    
            # Check per-variant installs threshold
            if experiment_settings.apply_min_installs_variants is not None:
                apply_min_installs_variants = all(
                    variant["installs"] > experiment_settings.apply_min_installs_variants
                    for variant in variants
                )

            # Stop if conditions are met
            if (apply_min_installs_experiment and apply_min_installs_variants 
                and r["status"] not in ["More data needed", "Not enough data", "Current listing won", "Draw"]):
                stop_res = gpc.stop_experiment(experiment_id)
                if stop_res:
                    utils.logger.info(
                        f"Experiment {experiment_name} stopped due to draw conditions {stop_res}"
                    )
                    stop_decision = True
                    
                    # Update experiment status
                    experiment = session.query(ExperimentModel).filter(
                        ExperimentModel.experiment_name_auto_populated == experiment_name
                    ).first()
                    if experiment:
                        experiment.status = ExperimentStatus.FINISHED
                        session.commit()
                    
                    messages.append(
                        f"""\n:red_circle:  Experiment: {experiment_name} 
    Stopped a Draw Experiment due to reaching min_days: 
    - status={r['status']} 
    - running_for={running_for_days}
    - apply_setting={apply_setting}
    - min_days={experiment_settings.min_duration_days} 
    - max_days={experiment_settings.max_duration_days}"""
                    )

    # Stop experiment if conditions are met
    if (
        (r["status"] in ["More data needed", "Not enough data", "Current listing won", "Draw"]
         and running_for_days >= experiment_settings.max_duration_days)
        or performance_kill
        or advanced_1000_installs_kill
    ):
        utils.logger.info(
            f"\nStop experiment {experiment_name} result={r['status']} running_for={running_for_days} days max={experiment_settings.max_duration_days}\n{r}"
        )
        
        stop_result = gpc.stop_experiment(experiment_id)
        utils.logger.info(
            f"Stopped Experiment: {stop_result} performance_start_end_below_zero_kill_with_min_days={performance_kill} advanced_cvr_kill={advanced_1000_installs_kill}\n"
        )
        
        if stop_result:
            stop_decision = True
            
            # Update experiment status
            experiment = session.query(ExperimentModel).filter(
                ExperimentModel.experiment_name_auto_populated == experiment_name
            ).first()
            if experiment:
                experiment.status = ExperimentStatus.FINISHED
                session.commit()
            
            # Add appropriate message based on stop reason
            if r["status"] in ["Current listing won", "Draw"]:
                messages.append(
                    f"""\n:red_circle:  Experiment: {experiment_name} 
Killed due to: {r['status']} 
- running_for={running_for_days} 
- min_days={experiment_settings.min_duration_days} 
- max_days={experiment_settings.max_duration_days}"""
                )
            elif performance_kill:
                messages.append(
                    f"""\n:red_circle:  Experiment:  {experiment_name}
Killed due to: Minimum duration passed, poor performance
- running_for={running_for_days} 
- min_days={experiment_settings.min_duration_days} 
- max_days={experiment_settings.max_duration_days}"""
                )
            elif advanced_1000_installs_kill:
                messages.append(
                    f"""\n:red_circle:   {experiment_name}
Killed due to: Early kill rules 
- running_for={running_for_days} 
- min_days={experiment_settings.min_duration_days} 
- max_days={experiment_settings.max_duration_days}
- early_kill_rule={round(experiment_settings.early_kill_cvr_decrease*100,2)}
- early_kill_min_installs={experiment_settings.early_kill_min_installs}
{advanced_kill_message}
"""
                )
    # stop experiment if loss of stopp
    elif r["status"] == "Current listing won" or experiment.status == ExperimentStatus.STOPPING:
        utils.logger.info(
            f"\nStop experiment {experiment_name} result={r['status']} running_for={running_for_days} days max={experiment_settings.max_duration_days}\n{r}"
        )
        # stop experiment in the console
        stop_result = gpc.stop_experiment(experiment_id)
        if stop_result:
            stop_decision = True
            messages.append(
                f"""\n:red_circle:  Experiment: {experiment_name} 
Killed due to: {r['status']} 
- running_for={running_for_days} 
- min_days={experiment_settings.min_duration_days} 
- max_days={experiment_settings.max_duration_days}"""
            )
    else:
        utils.logger.info(
            f"Experiment {experiment_name} status={r['status']} running_for={running_for_days} days"
        )

    return stop_decision, messages




def apply_winning_experiment(r, experiment_settings, gpc, session):
    """
    Apply winning experiment if conditions are met
    
    Args:
        r (dict): Experiment data from Play Console
        experiment_settings (ExperimentSettingsModel): Experiment settings from database
        gpc (PlayConsoleDriver): Play Console driver instance
        session (Session): Database session
    """
    utils.logger.info("check if we can apply the experiment")
    messages = []
    apply_decision = False
    
    variants = r["variants"]
    experiment_name = r["experiment_name"]
    experiment_id = r["experiment_id"]
    apply_setting = experiment_settings.apply_setting
    start_time = r["start_time"]
    running_for_days = (datetime.now() - start_time).days
    max_percentile = 0
    max_variant_name = ""

    # Check apply type
    if apply_setting == ApplySetting.WIN:
        # Skip if not a win
        if r["status"] in ["More data needed", "Not enough data", "Current listing won", "Draw"]:
            return apply_decision, messages
            
        # Check variant install thresholds
        if experiment_settings.apply_min_installs_variants is not None:
            if any(variant["installs"] < experiment_settings.apply_min_installs_variants 
                  for variant in variants):
                return apply_decision, messages
                
        # Check total installs threshold
        if experiment_settings.apply_min_installs_experiment is not None:
            total_installs = sum(variant["installs"] for variant in variants)
            if total_installs < experiment_settings.apply_min_installs_experiment:
                return apply_decision, messages
                
        # Check minimum duration
        if running_for_days < experiment_settings.min_duration_days:
            return apply_decision, messages

    # Handle percentile-based application
    elif apply_setting == ApplySetting.ON_PERCENTILE:
        # Check minimum duration
        if running_for_days < experiment_settings.min_duration_days:
            return apply_decision, messages
            
        # Check variant install thresholds
        if experiment_settings.apply_min_installs_variants is not None:
            if any(variant["installs"] < experiment_settings.apply_min_installs_variants 
                  for variant in variants):
                return apply_decision, messages
                
        # Check total installs threshold
        if experiment_settings.apply_min_installs_experiment is not None:
            total_installs = sum(variant["installs"] for variant in variants)
            if total_installs < experiment_settings.apply_min_installs_experiment:
                return apply_decision, messages
                
        # Calculate percentiles
        for variant in variants:
            try:
                variant["percentile"] = variant["performance_end"] / (
                    abs(variant["performance_start"]) + abs(variant["performance_end"])
                )
            except ZeroDivisionError:
                variant["percentile"] = 0

            if variant["percentile"] > max_percentile:
                max_percentile = variant["percentile"]
                max_variant_name = variant["name"]
                
        # Check percentile threshold
        if (variant["percentile"] == max_percentile and 
            variant["percentile"] >= experiment_settings.apply_on_percentile.value / 100):
            utils.logger.info(
                "Applying experiment on percentile",
                variant["percentile"],
                experiment_settings.apply_on_percentile
            )
            winning_variant_name = max_variant_name
        else:
            return apply_decision, messages
            
        utils.logger.info(
            f"winning_variant_name={winning_variant_name} percentile={max_percentile} apply_on_percentile={experiment_settings.apply_on_percentile}"
        )

    elif apply_setting == ApplySetting.NEVER:
        return apply_decision, messages
    else:
        utils.logger.error(f"Unknown apply setting {experiment_settings.apply_setting}")
        return apply_decision, messages

    utils.logger.info(
        f"Applying experiment {experiment_name} {apply_setting} running_for={running_for_days} days max={experiment_settings.max_duration_days}\n{r}"
    )
    
    # Get winning variant name
    if "won" in r["status"]:
        winning_variant_name = r["status"].split(" won")[0]
    else:
        print(f"Winning variant name not found {winning_variant_name}, {r['status']}")

    # Apply experiment
    res = gpc.apply_experiment(experiment_id, winning_variant_name)
    utils.logger.info(f"Experiment Applied: {res} \n")
    
    if res:
        apply_decision = True
        utils.logger.info(f"Experiment {experiment_name} applied")
        
        # Update experiment status
        experiment = session.query(ExperimentModel).filter(
            ExperimentModel.experiment_name_auto_populated == experiment_name
        ).first()
        if experiment:
            experiment.status = ExperimentStatus.FINISHED
            session.commit()
        
        # Add success message
        messages.append(
            f"""Experiment {experiment_name} applied apply_setting={apply_setting}
winning_variant_name={winning_variant_name} percentile={max_percentile} apply_on_percentile={experiment_settings.apply_on_percentile}\n"""
        )
    else:
        utils.logger.info(
            f"Experiment {experiment_name} status={r['status']} running_for={running_for_days} days could not be applied"
        )
        
    return apply_decision, messages