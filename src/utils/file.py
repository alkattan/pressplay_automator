import json

def get_sent_wins(app_id):
    """
    Read experiment json from disk
    """
    name = f"/tmp/sent_wins_notifications_{app_id}.json"
    try:
        with open(name, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return dict()


def save_sent_wins(sent_notifications, app_id):
    """
    Save experiment json to disk
    """
    name = f"/tmp/sent_wins_notifications_{app_id}.json"
    with open(name, "w") as f:
        json.dump(sent_notifications, f, indent=4)