from PIL import Image
from src.clients.drive import download_image_from_drive_api
import logging
import json
from datetime import datetime
import requests
import re
import src.utils.utils as utils
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_target_csls(sheets, app_package):
    csls = dict()
    rows = sheets.get_data_as_dict("CSLs")
    for row in rows:
        if app_package.strip() == row["app_package"].strip():
            if row["name"].strip() not in csls.keys():
                csls[row["name"].strip()] = [row["locale"].split(" – ")[-1].strip()]
            else:
                csls[row["name"].strip()].append(row["locale"].split(" – ")[-1].strip())
    logger.info(csls)
    return csls


def update_image_url(image_url):
    # Check if the URL contains "googleusercontent.com"
    if "googleusercontent.com" in image_url:
        # If the URL already has a size specification, replace it with =w5000-h5000-rw
        if re.search(r"=w\d+-h\d+-rw", image_url) or re.search(r"=h\d+-w\d+-rw", image_url):
            image_url = re.sub(r"=w\d+-h\d+-rw", "=w5000-h5000-rw", image_url)
            image_url = re.sub(r"=h\d+-w\d+-rw", "=w5000-h5000-rw", image_url)
            updated_url = image_url
        else:
            # If there's no size specification, just add =w5000-h5000-rw
            return image_url + "=w5000-h5000-rw"

    # If the URL is not a Google URL, return it unchanged
    return image_url


def download_image_from_url(image_url, image_name):
    image_url = update_image_url(image_url)
    utils.logger.info(f"Updated image url {image_url}")
    # Send a GET request to the image URL
    response = requests.get(image_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in binary write mode
        with open(image_name, "wb") as file:
            # Write the contents of the response to the file
            file.write(response.content)
    else:
        utils.logger.error(
            f"Failed to download image. Status code: {response.status_code}"
        )


def resize_image(image_path, size=(512, 512)):
    # Let's assume we have an image file "example.jpg" that we want to resize
    # First, we need to open the image
    original_image = Image.open(image_path)

    # Now we resize the image to 512x512
    resized_image = original_image.resize(size)

    # To demonstrate, we'll save the resized image as a new file
    resized_image.save(image_path)


def is_16_9_or_9_16(width, height):
    utils.logger.info(f"Checking aspect ratio for {width}x{height}")
    # Calculate the aspect ratio
    aspect_ratio = width / height

    # Check if the aspect ratio is not equal to 16:9 or 9:16
    if abs(aspect_ratio - 16 / 9) > 0.01 and abs(aspect_ratio - 9 / 16) > 0.01:
        return False  # The aspect ratio is not 16:9 or 9:16
    else:
        return True  # The aspect ratio is not 16:9 or 9:16


def resize_image_if_needed(image_path, is_screenshot=False, size=(2208, 1242)):
    # Let's assume we have an image file "example.jpg" that we want to resize
    # First, we need to open the image
    original_image = Image.open(image_path)
    if original_image.format in {"WEBP", "JPEG"}:
        logger.info(f"Changing image type {image_path.split('/')[-1]} to PNG")
        try:
            original_image.save(image_path, "PNG")
            original_image = Image.open(image_path)
        except Exception as e:
            logger.error(f"Failed to convert image to PNG: {e}")
    width, height = original_image.size
    new_width, new_height = size
    if not is_16_9_or_9_16(width, height) and not is_screenshot:
        # Now we resize the image to 512x512
        if new_width > new_height:
            logger.info(
                f"Resizing image from {width}x{height} to {new_width}x{new_height}"
            )
            resized_image = original_image.resize((new_width, new_height))
        else:
            logger.info(
                f"Resizing image from {width}x{height} to {new_height}x{new_width}"
            )
            resized_image = original_image.resize((new_height, new_width))
        # To demonstrate, we'll save the resized image as a new file
        resized_image.save(image_path, "PNG")


def number_of_experiments_per_store_listing(store_listing, running_locals_listings):
    count = 0
    for r in running_locals_listings:
        if r.startswith(store_listing):
            count += 1
    return count


def get_experiment_by_name(name, experiments):
    for e in experiments:
        if e["experiment_name_auto_populated"].strip() == name.strip():
            return e


def parse_drive_id(url):
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return url.split("id=")[1].split("&")[0]


def download_image(url, image_path):
    """
    Either download the image from google play or from google drive
    """
    if (
        url.startswith("https://play")
        or url.startswith("https://storage.googleapis.com")
        or url.startswith("https://cdn.leonardo.ai")
        or url.startswith("https://lh3.googleusercontent.com")
    ):
        logger.info(f"Downloading image from Google Play")
        download_image_from_url(url, image_path)
    else:
        drive_id = parse_drive_id(url)
        download_image_from_drive_api(image_path, drive_id)


def convert_to_percentage(s):
    """
    This function takes a string and converts it to a float percentage value.
    """
    return float(s.strip("%"))

