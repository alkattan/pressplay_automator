import os
from playwright.sync_api import Locator, sync_playwright
import random
import time
import pyotp
from datetime import datetime
from src.utils.utils import resize_image, download_image, resize_image_if_needed
import traceback
import socket
from urllib.error import HTTPError
from src.modules.publisher.models import PublisherModel
from src.modules.app.models import AppModel
from src.modules.publishing_overview.repository import create_publishing_change
from sqlalchemy.orm import Session
# Logger
import src.utils.logger as logger
import re
from typing import List
from src.modules.experiment.repository import get_experiment_attributes, get_experiment_variants
from src.modules.experiment.models import ExperimentModel, VariantModel

print('working_dir', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


# Slow down the script to make it easier to debug or just make it more human-like
SLOW_MO = 0

# Playwright timeout
PLAYWRIGHT_TIMEOUT = 20000

# Used by locators (eg: page.locator('text=foo').inner_text(timeout=LOCATOR_TIMEOUT))
LOCATOR_TIMEOUT = 6000


class PlayConsoleDriver:
    # Xpath locators for the experiment tables
    live_table_xpath = '//console-section[@htmltitle="In progress"]'
    completed_table_xpath = '//console-section[@htmltitle="Completed"]'
    past_table_xpath = '//console-section[@htmltitle="Past experiments"]'

    def __init__(self, publisher: PublisherModel, app: AppModel, email: str, password: str, otp_code: str, session: Session):
        self.publisher = publisher
        self.app = app
        self.play_console_publisher = publisher.play_console_id
        self.play_console_app = app.play_console_id
        self.app_package = app.package_id
        self.automated_testing = app.automated_testing
        self.automated_send_for_review = app.automated_send_for_review
        self.automated_publishing = app.automated_publishing
        self.otp_code = otp_code
        self.email = email
        self.password = password
        self.session = session
        self.logger = logger.logger
        self.playwright = sync_playwright().start()
        self.browser = self.start_browser()
        if not self.is_logged_in():
            self.logger.debug("Not logged in Google")
            for t in range(3):
                try:
                    self.login_google()
                    break
                except Exception as e:
                    self.logger.debug("Login failed, trying again")
                    self.logger.debug(e)
                    continue
        self.logger.info("Logged in successfully")

        if not self.email:
            self.logger.error("No email found")
            return

        if not self.password:
            self.logger.error("No password found")
            return

        if not self.otp_code:
            self.logger.error("No OTP code found")
            return

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

    def clean(self):
        if self.browser is not None:
            self.browser.close_browser()
            self.logger.error("Browser closed")

    def set_publisher_app(self, publisher: PublisherModel, app: AppModel):
        self.publisher = publisher
        self.app = app
        self.play_console_publisher = publisher.play_console_id
        self.play_console_app = app.play_console_id
        self.app_package = app.package_id
        self.automated_testing = app.automated_testing
        self.automated_send_for_review = app.automated_send_for_review
        self.automated_publishing = app.automated_publishing
        self.logger = logger.logger

    @property
    def base_url(self) -> str:
        return "https://play.google.com"

    @property
    def create_experiments_url(self) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/store-listing-experiments/create"
        )

    @property
    def experiments_url(self) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/store-listing-experiments/overview"
        )

    def experiment_url(self, experiment_id: str) -> str:
        # https://play.google.com/console/u/0/developers/7486557340409834297/app/4976064066216321309/store-listing-experiments/8929258306411079787/report
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/store-listing-experiments/{experiment_id}/report"
        )

    def csls_url(self) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/custom-store-listings"
        )

    @property
    def main_csl_url(self) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/main-store-listing"
        )

    def csl_url(self, csl_id) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/custom-store-listings/"
            f"{csl_id}"
        )

    @property
    def publishing_overview(self) -> str:
        return (
            f"https://play.google.com/console/u/0/developers"
            f"/{self.play_console_publisher}/app"
            f"/{self.play_console_app}"
            f"/publishing"
        )

    def random_sleep(self, start: int = 5, end: int = 10):
        time.sleep(random.randint(start, end))

    def create_short_description_experiment(self):
        pass

    def create_icon_experiment(self):
        pass

    def create_experiment(self, experiment: ExperimentModel, variants: List[VariantModel], publisher_id, app_id):
        """Create experiment in Play Console"""
        # Get experiment attributes in dictionary format
        experiment_data = get_experiment_attributes(self.session, experiment)
        variant_data = get_experiment_variants(experiment)
        
        # Check where is the folder based on env
        if socket.gethostname().startswith("scraper"):
            self.logger.info("Running on scraper")
            path_images = "/aso_automation"
        else:
            path_images = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Create the folder if it doesn't exist
        path_images = f"{path_images}/images/{publisher_id}/{app_id}"
        os.makedirs(path_images, exist_ok=True)
        self.logger.info(f"Folder created at {path_images}")

        try:
            self.page.goto(self.create_experiments_url)
            self.logger.info("Experiments page opened")
            ## First Page
            # fill in experiment name
            self.page.fill(
                "xpath=//console-form-row/div/div/div/material-input/label/input",
                experiment_data["experiment_name_auto_populated"],
            )

            # fill in experiment store listing
            self.page.click(
                "xpath=//console-form-row/div/div/div/material-dropdown-select/dropdown-button"
            )

            # Try one of these clicks
            try:
                # Fun games
                self.page.click(
                    'xpath=//dynamic-component/listing-option/div[contains(text(),"'
                    + experiment_data["csl_name"]  # Updated from store_listing_auto_populated
                    + '")]'
                )
            except Exception:
                # Wildlife
                self.page.click(
                    'xpath=//simple-html/span[contains(text(),"'
                    + experiment_data["csl_name"]  # Updated from store_listing_auto_populated
                    + '")]'
                )

            # short description experiments
            # Click on Localised experiment
            if experiment_data["locale_name"] != "Default Graphics":  # Updated from experiment_type_auto_populated
                self.page.click("text=Localized experiment")
                time.sleep(2)
                # Click on select locales 1st drop down
                self.logger.info("clicking on select locales 2nd drop down")
                self.page.locator(
                    "//material-stepper/div/div/targeting-step/console-section/div/div/console-block-1-column/div/div/console-form/console-form-row/div/div/div/material-dropdown-select/dropdown-button/div/span"
                ).nth(1).click()

                self.logger.info("click on search")
                # Search for Locale
                self.page.fill(
                    "xpath=//material-select-searchbox/material-input/div/div/label/input",
                    experiment_data["locale_name"]  # Updated from experiment_type_auto_populated
                )  # en-US

                # click on the selected locale
                self.page.click(
                    "xpath=//material-select-dropdown-item/dynamic-component/language-option/div"
                )
            # icon experiments
            elif experiment_data["locale_name"] == "Default Graphics":  # Updated from experiment_type_auto_populated
                self.page.click("text=Default graphics experiment")
                time.sleep(2)

            time.sleep(7)
            # Click on Next button first page
            self.logger.info("go to second page")
            self.page.click(
                'xpath=//material-button/button/div[contains(text(),"Next")]'
            )

            ## Second Page
            # now selecting the default of A/B test
            self.page.click(
                'xpath=//label[contains(text(), "' + experiment_data["target_metric"] + '")]'
            )

            # Click on Variants
            self.page.locator('xpath=//span[contains(text(),"1 (A/B test)")]').click()
            variants_len = len(variants)

            # Select which variant combination to use
            if variants_len == 1:
                self.page.locator("text=1 (A/B test)").nth(1).click()
                self.logger.info("1 variant")
            elif variants_len == 2:
                self.page.locator("text=2 (A/B/C test)").click()
                self.logger.info("2 variants")
            elif variants_len == 3:
                self.page.locator("text=3 (A/B/C/D test)").click()
                self.logger.info("3 variants")
            time.sleep(2)

            # # Minimum detectable effect
            #     self.page.locator('text=2.5%').nth(1).click()

            if experiment_data["minimum_detectable_effect"] != "2.5%":
                self.page.locator('xpath=//material-dropdown-select/dropdown-button/div/span[contains(text(),"2.5%")]').click()
                time.sleep(1)
                mdf=experiment_data['minimum_detectable_effect']
                self.page.locator(
                    f'xpath=//material-select-dropdown-item/dynamic-component/description-option/div/div[contains(text(), "{mdf}")]'
                ).click()

            # # Confidence Interval
            if experiment_data["confidence_interval"] != "90%":
                self.page.locator('xpath=//material-dropdown-select/dropdown-button/div/span[contains(text(),"90%")]').click()
                time.sleep(1)
                # Click on the desired confidence interval using a more specific selector
                self.page.locator(
                    f'xpath=//material-select-dropdown-item/dynamic-component/description-option/div/div[contains(text(), "{experiment_data["confidence_interval"]}")]'
                ).click()

            # Click on Next button second page
            self.page.click(
                'xpath=//material-button/button/div[contains(text(),"Next")]'
            )

            ## Third Page
            # Click on the experiment type
            if len(variants[0].icon or "") > 0:
                self.page.locator(f"text=App icon").click()

            if len(variants[0].short_description or "") > 0:
                self.page.locator(f"text=Short description").click()

            if len(variants[0].feature_graphic or "") > 0:
                self.page.locator(f"text=Feature graphic").click()

            if len(variants[0].screen1 or "") > 0:
                self.page.locator(f"text=Screenshots").click()

            if len(variants[0].promo_video or "") > 0:
                self.page.locator('xpath=//material-checkbox/div/label[contains(text(), "Video")]').click()

            time.sleep(1)
            # Loop over variants and create them
            for i_v, variant in enumerate(variants):
                edit_variant_name = f"text=Edit Variant {i_v+1}"
                self.page.locator(edit_variant_name).click()
                self.logger.info(f"Creating variant {i_v+1}")

                # Generate a timestamp to append to image filenames
                timestamp = int(time.time())

                if len(variant.short_description or "") > 0:
                    self.page.fill(
                        'xpath=//input[@aria-label="Variant name"]',
                        f"{variant.name}",
                    )
                    self.page.fill(
                        'xpath=//input[@aria-label="Short description of the app"]',
                        f"{variant.short_description}",
                    )
                if len(variant.icon or "") > 0:
                    self.page.fill(
                        'xpath=//material-input[@debug-id="name-input"]/label/input',
                        f"{variant.name}",
                    )
                    image = f"{path_images}/{self._sanitize_filename(variant.name)}_{timestamp}.png"
                    download_image(variant.icon, image)
                    resize_image(image, (512, 512))
                    self.page.set_input_files(
                        'xpath=//app-image-uploader[@debug-id="icon-uploader"]/console-graphic-uploader/input[@type="file"]',
                        image,
                    )
                    time.sleep(1)
                if len(variant.feature_graphic or "") > 0:
                    self.page.fill(
                        'xpath=//material-input[@debug-id="name-input"]/label/input',
                        f"{variant.name}",
                    )
                    image = f"{path_images}/{self._sanitize_filename(variant.name)}_{timestamp}.png"
                    download_image(variant.feature_graphic, image)
                    resize_image(image, (1024, 500))
                    self.page.set_input_files(
                        'xpath=//app-image-uploader[@debug-id="feature-graphic-uploader"]/console-graphic-uploader/input[@type="file"]',
                        image,
                    )
                    time.sleep(5)
                if len(variant.screen1 or "") > 0:
                    self.page.fill(
                        'xpath=//material-input[@debug-id="name-input"]/label/input',
                        f"{variant.name}",
                    )
                    screens = []
                    screens_7 = []
                    screens_10 = []
                    for i in range(1, 9):
                        if len(variant[f"screen{i}"]) == 0:
                            break
                        image = f"{path_images}/{self._sanitize_filename(variant.name)}_{timestamp}_{i}.png"
                        download_image(variant[f"screen{i}"], image)
                        resize_image_if_needed(image, True)
                        screens.append(image)
                    for i in range(1, 9):
                        if len(variant[f"screen{i}_7inch"]) == 0:
                            break
                        image = f"{path_images}/{self._sanitize_filename(variant.name)}_{timestamp}_7inch_{i}.png"
                        download_image(variant[f"screen{i}_7inch"], image)
                        resize_image_if_needed(image, True)
                        screens_7.append(image)
                    for i in range(1, 9):
                        if len(variant[f"screen{i}_10inch"]) == 0:
                            break
                        image = f"{path_images}/{self._sanitize_filename(variant.name)}_{timestamp}_10inch_{i}.png"
                        download_image(variant[f"screen{i}_10inch"], image)
                        resize_image_if_needed(image, True)
                        screens_10.append(image)
                    self.logger.info(screens)
                    self.page.set_input_files(
                        'xpath=//app-screenshots-uploader[@debug-id="phone-screenshots-uploader"]/console-graphic-uploader/input[@type="file"]',
                        screens,
                    )
                    self.page.set_input_files(
                        'xpath=//app-screenshots-uploader[@debug-id="tablet-small-screenshots-uploader"]/console-graphic-uploader/input[@type="file"]',
                        screens_7,
                    )
                    self.page.set_input_files(
                        'xpath=//app-screenshots-uploader[@debug-id="tablet-regular-screenshots-uploader"]/console-graphic-uploader/input[@type="file"]',
                        screens_10,
                    )
                    time.sleep(30)
                if len(variant.promo_video or "") > 0:
                    self.page.fill(
                        'xpath=//material-input[@debug-id="name-input"]/label/input',
                        f"{variant.name}",
                    )
                    self.page.fill(
                        'xpath=//material-input[@debug-id="promo-video-input"]/label/input',
                        f"{variant.promo_video}",
                    )
                    time.sleep(5)
                self.page.click("text=Apply")

            time.sleep(5)
            self.logger.info("Click on Save")
            self.page.locator(
                'xpath=//*[@id="main-content"]/div/div[1]/page-router-outlet/page-wrapper/div/create-store-listing-experiment-page/publishing-bottom-bar/form-bottom-bar/bottom-bar-base/div/div/div/div[2]/console-button-set/div[3]/overflowable-item[2]/button/span'
            ).click()

            # Go to Publishing overview
            self.page.click("text=Go to overview")
            # self.accept_publishing_changes()

        # HTTP Excpetion
        except HTTPError as err:
            return False, str(err)

        except Exception as se:
            error_message = str(se)
            if "material-select-dropdown-item/dynamic-component/language-option/div" in error_message:
                error_message = "Locale not found"
                return False, error_message
            self.logger.error(f"Something went wrong {str(se)}")
            self.logger.error(traceback.format_exc())
            return False, str(se)
        time.sleep(10)
        return True,  None

    def check_url(self, url):
        # Navigate to the URL
        response = self.page.goto(url)

        # Check if the page loaded successfully
        if response.ok:
            self.logger.info(f"The page at {url} loaded successfully.")
            return True
        else:
            self.logger.info(
                f"Failed to load the page at {url}. Status code: {response.status_code}"
            )
            return False

    def accept_publishing_changes(self):
        """Accept any pending publishing changes"""
        self.logger.info("Checking review_and_publishing_changes")
        publish = True
        review = True
        changes = []
        
        self.page.goto(self.publishing_overview)
        # Changes ready to publish
        time.sleep(8)
        table_exists = self.page.locator(
                "xpath=//console-table[@debug-id='changes-table']/div/div/ess-table/ess-particle-table/div/div/div/div"
            ).count() > 0
        self.logger.info(f"table_exists={table_exists} automated_publishing={self.automated_publishing} automated_send_for_review={self.automated_send_for_review}")
        # check if changes table exists
        if table_exists:
            changes_tag = self.page.locator(
                "xpath=//console-table[@debug-id='changes-table']/div/div/ess-table/ess-particle-table/div/div/div/div"
            ).all()
            
            for row_change in changes_tag:
                entry = ""
                try:
                    track = row_change.locator("xpath=./span").text_content()
                    entry += track
                except Exception:
                    pass
                row_tags = row_change.locator("xpath=./ess-cell/text-field").all()
                for section in row_tags:
                    entry += section.text_content().replace("\n", "") + " "
                if len(entry) > 0:
                    changes.append(entry + "\n")

            for breaking_change in [
                "Production",
                "Closed testing - Alpha",
                "Closed testing - Beta",
                "rollout"
            ]:
                # check if there is a breaking change
                if (
                    self.page.locator(
                        f'xpath=//span[contains(text(), "{breaking_change}")  and @role="gridcell"]'
                    ).count() > 0
                ):
                    # Log the breaking change and quit
                    self.logger.info(
                        f"\nNotice:\nThere is a {breaking_change} change so quiting"
                    )
                    publish = False
                    review = False
                    
            # if automated publishing is on
            if self.automated_publishing:
                self.logger.info("Automated Publishing")
                if publish:
                    self.logger.info("Changes being sent to publish")
                    try:
                        # log
                        self.logger.info("Sending changes to publish")
                        self.page.click(
                            'xpath=//publishing-changes-section[@debug-id="go-live-changes"]/console-section/div/console-header/div/div/div/div/div/console-button-set/div/div/button[@debug-id="go-live-button"]'
                        )
                        time.sleep(2)
                        # Click on Publish Changes button
                        try:
                            # log
                            self.logger.info("Publishing changes ok")
                            self.page.click(
                                'xpath=//button/span[contains(text(), "Publish changes")]'
                            )
                        except Exception:
                            pass
                        # Click on Add changes
                        try:
                            self.page.click("text=Add changes")
                        except Exception:
                            pass
                    except Exception as ee:
                        self.logger.info("Nothing to Publish")

            # if automated send for review is on
            if self.automated_send_for_review:
                # Changes ready for review
                if review:
                    self.logger.info("Changes being sent for review")
                    try:
                        # send changes for review button with numbers
                        try:
                            # log
                            self.logger.info("Sending changes for review")
                            self.page.click(
                                'xpath=//publishing-changes-section[@debug-id="not-sent-for-review-changes"]/console-section/div/console-header/div/div/div/div/div/console-button-set/div/div/button[@debug-id="send-for-review-button"]'
                            )
                        except Exception:
                            pass
                        time.sleep(2)
                        try:
                            # Send changes for review dialog button
                            # log
                            self.logger.info("clicking ok button")
                            self.page.click(
                                "xpath=//footer/div/div/console-button-set/div/button[@debug-id='yes-button']"
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        self.logger.info(f"Nothing to send for review {str(e)}")
                        
                # add changes to the database if they exist
                if len(changes) > 0:
                    try:
                        create_publishing_change(
                            self.session,
                            self.app.id,
                            "\n".join(changes),
                            publish,
                            review
                        )
                    except Exception as e:
                        self.logger.error(f"Error saving publishing changes to database: {e}")

    def process_variant(self, variant_stat: Locator, variant_data: Locator) -> dict:
        """
        This function process one variant in the detail page

        :param variant_stat: variant stat element
        :param variant_data: variant data element
        :return: variant data
        """
        data = (
            variant_data.locator(
                "//table-drilldown-row",
            )
            .inner_text()
            .split("\n")
        )
        stats = variant_stat.inner_text().split("\n")

        stats_len = len(stats)

        variant = {
            "name": stats[1],
            "audience": stats[2].replace("%", "").replace("-", ""),
            "installs": stats[3].replace(",", "").replace("-", ""),
            "installs_scaled": stats[4].replace(",", "").replace("-", ""),
        }

        label = data[0].lower().replace(" ", "_")

        try:
            data[1]
            for metadata in chunks(data, 2):
                variant[metadata[0].lower().replace(" ", "_")] = metadata[1]
        except Exception:
            pass

        try:
            screenshots = variant_data.locator(
                '//img[@alt="Phone screenshots"]',
            ).all()
            for i, s in enumerate(screenshots):
                variant[f"screen{str(i + 1)}"] = s.get_attribute("src")
        except Exception:
            pass

        try:
            t7_screenshots = variant_data.locator(
                '//img[@alt="7-inch tablet screenshots"]',
            ).all()
            for i, s in enumerate(t7_screenshots):
                variant[f"t7_screen{str(i + 1)}"] = s.get_attribute("src")
        except Exception:
            pass

        try:
            t10_screenshots = variant_data.locator(
                '//img[@alt="10-inch tablet screenshots"]',
            ).all()
            for i, s in enumerate(t10_screenshots):
                variant[f"t10_screen{str(i + 1)}"] = s.get_attribute("src")
        except Exception:
            pass

        if label == "app_icon":
            icon = variant_data.locator('//img[@alt="App icon"]')
            variant["icon"] = icon.get_attribute("src")

        if label == "feature_graphic":
            feature_graphic = variant_data.locator(
                '//img[@alt="Feature graphic"]',
            )
            variant["feature_graphic"] = feature_graphic.get_attribute("src")

        if stats_len <= 6:
            variant["performance_start"] = 0
            variant["performance_end"] = 0
        else:
            try:
                variant["performance_start"] = float(
                    stats[5].replace("%", "").replace(",", ".")
                )
                variant["performance_end"] = float(
                    stats[6].replace("%", "").replace(",", ".")
                )
            except Exception as e:
                self.logger.debug("Error while parsing performance stats")
                self.logger.debug(e)
                self.logger.debug("Stats:")
                self.logger.debug(stats)

        return variant

    def get_running_experiments(self, csls) -> list:
        # Accept publishing changes first TODO
        # self.accept_publishing_changes()
        # skip the header row
        for t in range(4):
            self.logger.info(f"Getting running experiments try={t}")

            try:
                # Select 100 instead of 10 for Completed experiments
                # Get running experiments second
                self.page.goto(self.experiments_url)
                try:
                    self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                if (
                    self.page.locator(
                        'xpath=//console-table[@debug-id="complete-experiment-table"]/pagination-bar/div/div/div/material-dropdown-select/dropdown-button/div[@aria-label="Show rows: 10 selected."]'
                    ).count()
                    > 0
                ):
                    self.page.locator(
                        'xpath=//console-table[@debug-id="complete-experiment-table"]/pagination-bar/div/div/div/material-dropdown-select/dropdown-button/div[@aria-label="Show rows: 10 selected."]'
                    ).click()
                    self.page.wait_for_load_state("networkidle")

                    self.page.click(
                        'xpath=//material-select-dropdown-item/span[contains(text(),"200")]'
                    )

                if (
                    self.page.locator(
                        'xpath=//console-table[@debug-id="in-progress-experiment-table"]/pagination-bar/div/div/div/material-dropdown-select/dropdown-button/div[@aria-label="Show rows: 10 selected."]'
                    ).count()
                    > 0
                ):
                    self.page.locator(
                        'xpath=//console-table[@debug-id="in-progress-experiment-table"]/pagination-bar/div/div/div/material-dropdown-select/dropdown-button/div[@aria-label="Show rows: 10 selected."]'
                    ).click()
                    self.page.wait_for_load_state("networkidle")

                    self.page.click(
                        'xpath=//material-select-dropdown-item/span[contains(text(),"200")]'
                    )

                try:
                    self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                running_experiments_with_headers = self.page.locator(
                    "xpath=//live-experiments-table/console-block-1-column/div/div/console-section/div/div/console-table/div/div/ess-table/ess-particle-table/div/div/div/div"
                ).all()
                if len(running_experiments_with_headers) < 2:
                    self.logger.info("No running experiments")
                    return []
                else:
                    self.logger.info(
                        f"Running experiments found {len(running_experiments_with_headers) - 1}"
                    )

                self.logger.info("trying processing found experiments")
                running_experiments = []
                i = 0
                for i, row in enumerate(running_experiments_with_headers):
                    # go to page
                    self.logger.info(f"Processing Experiment number={i}")
                    # assign the row again
                    try:
                        row = running_experiments_with_headers[i]
                        row_text = row.text_content()
                        # Skip headers
                        if "Experiment name" in row_text:
                            # i+=1
                            # self.logger.info("Skipping headers")
                            continue
                        # i+=1
                    except Exception as e:

                        self.logger.info(
                            f"Failed to get the row i={i} running={len(running_experiments_with_headers)} {str(e)}"
                        )
                        continue

                    experiment_name = row_text.split("\n")[0]
                    # self.logger.info(row_text.split("\n"))
                    try:
                        start_date = datetime.strptime(
                            row_text.split("\n")[1].split(")")[-1], "%b %d, %Y"
                        )
                    except Exception:
                        try:
                            start_date = datetime.strptime(
                                row_text.split("\n")[1].split("All languages")[1],
                                "%b %d, %Y",
                            )
                        except Exception as e:
                            self.logger.info(f"No start date found {str(e)} {row_text}")
                            start_date = None
                    # try translated other wise Default graphics experiment
                    try:
                        store_listing = (
                            row_text.split("\n")[1]
                            .split("Custom store listing")[1]
                            .split("Tra")[0]
                            .strip()
                        )
                        if store_listing not in csls.keys():
                            store_listing = (
                                row_text.split("\n")[1]
                                .split("Default graphics")[0]
                                .split("listing")[1]
                                .strip()
                            )
                    except Exception:
                        store_listing = "Default store listing"
                    #print(store_listing)
                    try:
                        locale_text=" ".join(row_text.split("\n")[1:])
                        locale = locale_text.split("(")[1].split(")")[0]
                    except Exception:
                        locale = "All languages"

                    if "Translated" in row_text:
                        experiment_type = "Translated"
                    elif "Default graphics" in row_text:
                        experiment_type = "Default graphics"
                    # Click on go to experiment page
                    # row.locator("xpath=/ess-cell").nth(-1).click()
                    experiment_link = row.locator("xpath=//ess-cell/console-table-main-action-cell/a").get_attribute("href")
                    new_page = self.context.new_page()
                    new_page.goto(self.base_url + experiment_link)
                    time.sleep(2)
                    # Reload the page to get the correct url
                    # self.page.reload()
                    experiment_id = new_page.url.split("/")[-2]

                    time.sleep(3)
                    variants = []

                    # if start_date is None experiment is a draft so default everything
                    if start_date is None:
                        result = None
                        start_time = None
                    # experiment is not a draft
                    else:
                        try:
                            result = new_page.locator(
                                "xpath=//icon-text/simple-html/span/strong"
                            ).text_content()
                        except Exception as e:
                            self.logger.info(f"Failed to get the result {str(e)}")
                            continue
                        started_stopped = (
                            new_page.locator(
                                "xpath=//p[@debug-id='experiment-description-text']"
                            )
                            .text_content()
                            .split(".")[0]
                            .split("Started on ")[1]
                        )
                        started_stopped = started_stopped.encode('ascii', 'ignore').decode('ascii')
                        self.logger.info(f"start_time={started_stopped}")
                        try:
                            start_time = datetime.strptime(
                                started_stopped, "%b %d, %Y %I:%M %p"
                            )
                        except Exception as e:
                            start_time = datetime.strptime(
                                started_stopped, "%b %d, %Y %I:%M%p"
                            )

                        # Process Variants
                        variants_stats = new_page.locator(
                            f'xpath=//experiments-stats-table/console-block-1-column/div/div/console-table/div/div/ess-table//div/div/div/div[contains(@class, "particle-table-row") and not(contains(@class, "particle-table-drilldown-row"))]',
                        ).all()
                        variants_stats_len = len(variants_stats)
                        # self.logger.info("variants_stats_len", variants_stats_len)
                        # open all dropdown menus for variants
                        for variant in variants_stats:
                            variant.get_by_role("button", name="Expand row").click()

                        variants_data = new_page.locator(
                            f'xpath=//experiments-stats-table/console-block-1-column/div/div/console-table/div/div/ess-table//div/div/div/div[contains(@class, "particle-table-drilldown-row")]',
                        ).all()
                        variants_data_len = len(variants_data)
                        # self.logger.info("variants_data_len", variants_data_len)
                        # process variants
                        for variant_stat, variant_data in zip(
                            variants_stats, variants_data
                        ):
                            variant = self.process_variant(variant_stat, variant_data)
                            # change to int
                            try:
                                variant["installs"] = int(variant["installs"])
                            except Exception as e:
                                variant["installs"] = 0
                            try:
                                variant["installs_scaled"] = int(
                                    variant["installs_scaled"]
                                )
                            except Exception as e:
                                variant["installs_scaled"] = 0
                            variants.append(variant)

                    exp= {
                            "app_id": self.app.id,
                            "experiment_name": experiment_name,
                            "experiment_id": experiment_id,
                            "locale": locale,
                            "store_listing": store_listing,
                            "experiment_type": experiment_type,
                            "start_date": start_date,
                            "start_time": start_time,
                            "status": result,
                            "variants": variants,
                        }
                    running_experiments.append(exp)
                    new_page.close()
            except Exception as s:
                self.logger.error(f"Something went wrong {str(s)}")
                self.logger.error(traceback.format_exc())
                if t >= 3:
                    self.logger.info("Failed to get running experiments")
                    return []
                continue
            break

        self.logger.info(
            f"\nnumber_of_running_experiments_fetched: {len(running_experiments)} "
        )
        return running_experiments

    def get_previous_experiments(self, csls) -> list:
        for t in range(4):
            self.logger.info(f"Getting previous experiments try={t}")

            try:
                # Select 100 instead of 10 for Completed experiments
                # Get running experiments second
                self.page.goto(self.experiments_url)
                time.sleep(7)

                previous_experiments_with_headers = self.page.locator(
                    "xpath=//terminated-experiments-table/console-table/div/div/ess-table/ess-particle-table/div/div/div/div"
                ).all()
                if len(previous_experiments_with_headers) < 2:
                    self.logger.info("No previous experiments")
                    return []
                else:
                    self.logger.info(
                        f"Previous experiments found {len(previous_experiments_with_headers) - 1}"
                    )

                self.logger.info("trying processing found Previous experiments")
                previous_experiments = []
                i = 0
                # while len(running_experiments) <= len(running_experiments_with_headers) - 1:
                for i, row in enumerate(previous_experiments_with_headers):
                    # go to page
                    self.logger.info(f"Processing previous Experiment number={i}")
                    try:
                        row = previous_experiments_with_headers[i]
                        row_text = row.text_content()
                        # Skip headers
                        if "Experiment name" in row_text:
                            # i+=1
                            continue
                        # i+=1
                    except Exception as e:
                        self.logger.info(
                            f"Previous Failed to get the row {i} {len(previous_experiments_with_headers)} {str(e)}"
                        )
                        continue

                    # ['PHI-000011-es-419: Game Mode Focus', ' Default store listing  Translated (es-419)Oct 27, 2023', ' 3 variants 75% of usersView PHI-000011-es-419: Game Mode Focusarrow_right_altarrow_right_alt ']
                    experiment_name = row_text.split("\n")[0]
                    self.logger.info("hi "+row_text.split("\n")[1].split(")")[-1])
                    try:
                        start_date = datetime.strptime(
                            row_text.split("\n")[1].split(")")[-1], "%b %d, %Y"
                        )
                    except Exception:
                        try:
                            start_date = datetime.strptime(
                                row_text.split("\n")[1].split("All languages")[1],
                                "%b %d, %Y",
                            )
                        # 
                        except Exception as e:
                            self.logger.info(f"No start date found {str(e)} {row_text}")
                            start_date = None
                            if row_text.strip() == "":
                                self.logger.info("Skipping empty row")
                                continue
                    try:
                        store_listing = (
                            row_text.split("\n")[1]
                            .split("Custom store listing")[1]
                            .split("Tra")[0]
                            .strip()
                        )
                        if store_listing not in csls.keys():
                            store_listing = (
                                row_text.split("\n")[1]
                                .split("Default graphics")[0]
                                .split("listing")[1]
                                .strip()
                            )
                    except Exception:
                        store_listing = "Default store listing"
                    try:
                        locale = row_text.split("(")[1].split(")")[0]
                    except Exception:
                        locale = "All languages"

                    if "Translated" in row_text:
                        experiment_type = "Translated"
                    elif "Default graphics" in row_text:
                        experiment_type = "Default graphics"
                    # Click on go to experiment page
                    # row.locator("xpath=/ess-cell").nth(-1).click()
                    experiment_link = row.locator("xpath=//ess-cell/console-table-main-action-cell/a").get_attribute("href")
                    new_page = self.context.new_page()
                    new_page.goto(self.base_url + experiment_link)

                    time.sleep(2)
                    # Reload the page to get the correct url
                    # self.page.reload()
                    experiment_id = new_page.url.split("/")[-2]

                    time.sleep(3)
                    variants = []

                    # if start_date is None experiment is a draft so default everything
                    if start_date is None:
                        result = None
                        start_time = None
                        need_to_kill = False
                    # experiment is not a draft
                    else:
                        try:
                            result = new_page.locator(
                                "xpath=//icon-text/simple-html/span/strong"
                            ).text_content()
                        except Exception as e:
                            self.logger.info(f"Failed to get the result {str(e)}")
                            continue
                        started_stopped = (
                            new_page.locator(
                                "xpath=//p[@debug-id='experiment-description-text']"
                            )
                            .text_content()
                            .split(".")[0]
                            .split("Started on ")[1]
                        )
                        start_time = datetime.strptime(
                            started_stopped, "%b %d, %Y %I:%M %p"
                        )

                        # Process Variants
                        variants_stats = new_page.locator(
                            f'xpath=//experiments-stats-table/console-block-1-column/div/div/console-table/div/div/ess-table//div/div/div/div[contains(@class, "particle-table-row") and not(contains(@class, "particle-table-drilldown-row"))]',
                        ).all()

                        # open all dropdown menus for variants
                        for variant in variants_stats:
                            variant.get_by_role("button", name="Expand row").click()

                        variants_data = new_page.locator(
                            f'xpath=//experiments-stats-table/console-block-1-column/div/div/console-table/div/div/ess-table//div/div/div/div[contains(@class, "particle-table-drilldown-row")]',
                        ).all()

                        # process variants
                        for variant_stat, variant_data in zip(
                            variants_stats, variants_data
                        ):
                            variant = self.process_variant(variant_stat, variant_data)
                            # change to int
                            try:
                                variant["installs"] = int(variant["installs"])
                            except Exception as e:
                                variant["installs"] = 0
                            try:
                                variant["installs_scaled"] = int(
                                    variant["installs_scaled"]
                                )
                            except Exception as e:
                                variant["installs_scaled"] = 0
                            variants.append(variant)
                        need_to_kill = any(
                            [
                                (
                                    True
                                    if v["performance_end"] < 0
                                    and v["performance_start"] < 0
                                    else False
                                )
                                for v in variants
                            ]
                        )

                    previous_experiments.append(
                        {
                            "experiment_name": experiment_name,
                            "experiment_id": experiment_id,
                            "locale": locale,
                            "store_listing": store_listing,
                            "experiment_type": experiment_type,
                            "start_date": start_date,
                            "start_time": start_time,
                            "status": result,
                            "variants": variants,
                            "kill": need_to_kill,
                        }
                    )
                    new_page.close()
            except Exception as s:
                self.logger.error(f"Something went wrong {str(s)}")
                self.logger.error(traceback.format_exc())
                if t >= 3:
                    self.logger.info("Failed to get previous experiments")
                    return []
                continue
            break

        self.logger.info(
            f"\nnumber_of_previous_experiments_fetched: {len(previous_experiments)} "
        )
        return previous_experiments

    def get_store_csls(self):
        """
        Get all Custom Store Listings for an app on the Play Console
        """
        csls = []
        self.page.goto(self.csls_url())
        time.sleep(6)
        try:
            csls_tags = self.page.locator(
                'xpath=//console-table[@debug-id="custom-listings-overview-table"]/div/div/ess-table/ess-particle-table/div/div/div/div'
            ).all()
            self.logger.info(f"csls_tags ={len(csls_tags)}")
            for csl in csls_tags[1:]:
                name = (
                    csl.locator("xpath=./ess-cell/console-table-text-cell/div/div/span")
                    .nth(0)
                    .text_content()
                )
                link = csl.locator(
                    "xpath=./ess-cell/console-table-main-action-cell/a"
                ).get_attribute("href")
                csl_id = link.split("custom-store-listings/")[1]
                if "URL" not in csl.text_content() and "Google Ad" not in csl.text_content():
                    csls.append(
                        {
                            "app": self.app,
                            "name": name,
                            "csl_play_console_id": csl_id,
                        }
                    )
        except Exception as e:
            self.logger.info(str(e))
        csls.append(
            {
                "app": self.app,
                "name": "Default store listing",
                "csl_play_console_id": "",
            }
        )
        return csls

    def get_csls_possible_locales(self, csls):
        """
        Get all possible locales for each Custom Store Listing
        """
        self.logger.info("Get possible locales")
        for csl in csls:
            for t in range(3):
                try:
                    if csl["name"] != "Default store listing":
                        self.page.goto(self.csl_url(csl["csl_play_console_id"]))
                        time.sleep(5)
                        csl["locales"] = []
                        self.page.click(
                            'xpath=//console-control[@placeholdertext="Select language"]/material-dropdown-select/dropdown-button'
                        )
                        locales = self.page.locator(
                            "xpath=//div/div/div/div/div/material-list/div/div/material-select-dropdown-item/dynamic-component/language-option/status-text/span"
                        ).all()
                        self.logger.info(f"len_csls={len(locales)}")
                        for locale_tag in locales:
                            locale = locale_tag.text_content()
                            if locale not in csl["locales"]:
                                csl["locales"].append(locale)
                    else:
                        self.page.goto(self.main_csl_url)
                        time.sleep(5)
                        csl["locales"] = []
                        self.page.click(
                            'xpath=//console-control[@placeholdertext="Select language"]/material-dropdown-select/dropdown-button'
                        )
                        locales = self.page.locator(
                            "xpath=//div/div/div/div/div/material-list/div/div/material-select-dropdown-item/dynamic-component/language-option/status-text/span"
                        ).all()
                        self.logger.info(f"main_locales_len={len(locales)}")
                        for locale_tag in locales:
                            locale = locale_tag.text_content()
                            if locale not in csl["locales"]:
                                csl["locales"].append(locale)
                    break
                except Exception as e:
                    self.logger.info(
                        f"multi_lang_error {csl['name']} {str(e)} trying single language"
                    )
                    try:
                        locale = self.page.locator(
                            "xpath=//language-control/div[@debug-id='single-language-text']"
                        ).text_content()
                        csl["locales"].append(locale)
                    except Exception as e:
                        self.logger.info(f"single_language_error, {str(e)}")
                    break
        return csls

    def stop_experiment(self, experiment_id: str):
        """
        Stop Experiment based on experiment id

        :param experiment_id: experiment id
        """
        try:
            url = self.experiment_url(experiment_id)
            self.logger.info(url)
            self.page.goto(url)
            time.sleep(5)

            self.logger.info("Waiting to stop")

            # Click on Stop button
            self.page.click("text=Stop experiment")

            self.page.locator("xpath=//button[@debug-id='yes-button']").click()
            time.sleep(5)
            # self.accept_publishing_changes()
            return True
        except Exception as e:
            self.logger.info(f"stopping experiment failed {str(e)}")
            return False

    def apply_experiment(self, experiment_id: str, winning_variant: str):
        """
        Applies the winning variant in the Experiment based on experiment id

        :param experiment_id: experiment id
        """
        try:
            url = self.experiment_url(experiment_id)
            self.logger.info(url)
            self.page.goto(url)
            time.sleep(5)
            # Get variants table
            variants = self.page.locator(
                f'xpath=//experiments-stats-table/console-block-1-column/div/div/console-table/div/div/ess-table//div/div/div/div[contains(@class, "particle-table-row") and not(contains(@class, "particle-table-drilldown-row"))]',
            ).all()
            # loop over variants until you find the winning one
            for row in variants:
                if winning_variant in row.text_content():
                    # Click on Apply button
                    row.locator("xpath=/ess-cell").nth(-1).click()

            # Click on Stop button
            # self.page.click("text=Stop experiment")
            # confirm the apply
            try:
                self.page.locator("xpath=//button[@debug-id='yes-button']").click()
            except Exception as e:
                self.logger.info(f"Failed to apply {winning_variant} {str(e)}")
                return False
            time.sleep(5)
            # self.accept_publishing_changes()
            return True
        except Exception as e:
            self.logger.info(f"applying experiment failed {str(e)}")
            return False

    def start_browser(self):
        self.browser = self.playwright.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=SLOW_MO,
            timeout=15000,
            args=["--full-screen"],
        )
        self.context = self.browser.new_context(viewport={"width": 1500, "height": 800})
        self.context.set_default_timeout(40000)
        self.page = self.context.new_page()
        self.page.set_default_timeout(PLAYWRIGHT_TIMEOUT)
        self.logger.info("Browser started")

    def is_logged_in(self) -> bool:
        """
        Check if user is logged in Google,
        by checking if the "email" address used for logging is visible on the page:
        https://play.google.com/console/u/0/developers

        :return: bool: True if logged in, False otherwise
        """
        self.logger.info("Checking if logged in to Google")
        for _ in range(3):
            try:
                self.page.goto("https://play.google.com/console/developers")
                time.sleep(3)
                element = self.page.get_by_text(self.email, exact=True)
                self.logger.info(f"Logged in={element.is_visible()}")
                return element.is_visible()
            except Exception as e:
                self.logger.info(str(e))
        return False

    def login_google(self, try_count=3):
        """
        Login to Google account

        :param user: email address
        :param password: password
        :param otp_code: OTP code
        :return: None
        """
        self.logger.info("Logging in Google now")
        totp = pyotp.TOTP(self.otp_code.replace(" ", ""))

        self.page.goto(
            "https://superuser.com/users/login?ssrc=head&returnurl=https%3a%2f%2fsuperuser.com%2f"
        )
        self.random_sleep(start=5, end=10)
        self.logger.debug("Google login page opened")

        # click on google button
        self.page.get_by_text("Log in with Google").click()
        self.page.wait_for_load_state("networkidle")
        self.logger.debug("Google button clicked")
        self.random_sleep()

        # enter email
        element = self.page.locator('//input[@type="email"]')
        element.fill(self.email)
        self.page.keyboard.press("Enter")
        self.logger.debug("Email entered")
        self.random_sleep()

        # enter password
        element = self.page.locator('//input[@type="password"]')
        element.fill(self.password)
        self.page.keyboard.press("Enter")
        self.logger.debug("Password entered")
        self.random_sleep()

        # enter 2FA code
        element = self.page.locator('//input[@id="totpPin"]')
        element.fill(totp.now())
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")
        self.logger.debug("2FA code entered")
        self.random_sleep()

        try:
            self.logger.info("Sending 2FA code again")
            element = self.page.locator('//input[@id="totpPin"]')
            time.sleep(20)
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.press("Backspace")
            # enter 2FA code
            element.fill(totp.now())
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            self.logger.debug("2FA code entered")
            self.random_sleep()
        except Exception as eee:
            self.logger.info(eee)

        self.random_sleep(10, 15)

        if not self.is_logged_in():
            if try_count > 0:
                self.logger.debug("Login failed, trying again")
                self.login_google(try_count - 1)
            else:
                self.logger.error("Login failed")
                raise Exception("Login failed")

    def close_browser(self):
        self.logger.info("Closing the browser")
        if self.browser is not None:
            self.browser.close()
            self.playwright.stop()
            self.logger.info("Browser closed")
        else:
            self.logger.info("Browser is already closed")

    def _sanitize_filename(self, filename, max_length=255):
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        # Replace any character that is not alphanumeric, underscore, hyphen, or period with an underscore
        filename = re.sub(r'[^\w.-]', '_', filename)

        # Truncate filename to the specified max length
        filename = filename[:max_length]

        return filename