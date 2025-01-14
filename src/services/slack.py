import requests
import json
import src.utils.utils as utils

# This function will send a message to a slack channel
def send_message_to_slack_channel(
    url,  # Slack webhook URL
    text,  # Text message to be sent
    author_name,  # Name of the author of the message
    author_icon,  # URL to the icon of the author
    title,  # Title of the message attachment
    footer,  # Footer displayed at the end of the message
    footer_icon,  # URL to the icon in the footer
    color,  # Color code of the message attachment
    priority  # Priority of the message
):
    """
    This function sends a message to a specified Slack channel using their Webhook URL. 
    
    The function takes several inputs:
    url: The URL of the incoming webhook that's been set up in Slack.
    text: The text message to be sent.
    author_name: The name of the person sending the message.
    author_icon: The URL of an image to use as the sender's icon.
    title: The title of the message attachement.
    footer: A footer to add to the end of the message.
    footer_icon: The URL of an image to use for the footer icon.
    color: The hexadecimal code of the color you want to use for the attachement.
    priority: A value specifying the priority of the message.
    This function creates a dictionary with all the necessary data for the message, 
    and then sends it to the Slack API using the requests library. Before sending the message, 
    it checks if the provided URL is valid (i.e., not None) and long enough.
    """
    utils.logger.info(f"Sending message to Slack channel: {url} {text}")
    
    # Create dictionary with message data
    data = {
        "text": title,
        "attachments": [
            {
                "author_name": author_name,
                "color": color,
                "author_icon": author_icon,
                "text": text,
                "footer": footer,
                "footer_icon": footer_icon,
                "fields": [{"title": "Priority", "value": priority, "short": "false"}],
            },
        ],
    }
    headers = {"Content-type": "application/json"}
    if url is not None:
        # skip when short url
        if len(url) > 15:
            try:
                requests.post(url, data=json.dumps(data), headers=headers)
                utils.logger.info(f"Message sent to Slack channel: {url} {text}")
                return True
            except Exception as e:
                utils.logger.error(f"Error sending message to Slack channel: {e}")
                return False
        