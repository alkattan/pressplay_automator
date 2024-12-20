from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import io
from googleapiclient.http import MediaIoBaseDownload
import src.utils.utils as utils
import io


def list_files_in_google_drive_folder(folder_id, ):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = "utils/aso_experiments.json"

    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    page_token = None
    while True:
        response = drive_service.files().list(q=f"'{folder_id}' in parents",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            utils.logger.info('Found file: %s (%s)' % (file.get('name'), file.get('id')))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

def upload_file_to_folder(asset_name, asset_path, service_account_file, folder_id):
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']

        credentials = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=credentials)
        file_metadata = {'name': asset_name,
                        'parents': [folder_id]}
        #files = drive_service.files().list().execute()
        file_path = asset_path
        media = MediaFileUpload(file_path)

        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        utils.logger.info(f'File ID: {file.get("id")}')
        return file.get("id")
    except Exception as e:
        utils.logger.error(f"Error uploading file: {e}")


def download_image_from_drive_api(file_name, file_id):
    try:
        # Path to your service account key file
        SERVICE_ACCOUNT_FILE = "utils/aso_experiments.json"
        # Define the scopes
        SCOPES = ['https://www.googleapis.com/auth/drive']
        # Authenticate and create the service
        credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        # Request the file
        request = service.files().get_media(fileId=file_id)
        # Download the file
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            utils.logger.info("Download Progress: {}%".format(int(status.progress() * 100)))
        # Save the file locally
        with open(file_name, 'wb') as f:
            f.write(fh.getbuffer())
        utils.logger.info(f"File Downloaded {file_name}")
    except Exception as e:
        utils.logger.error(f"Error downloading file: {e}")
        raise e