import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Authentication
OTP_CODE = os.getenv('otp_code')
EMAIL = os.getenv('email')
PASSWORD = os.getenv('password')

# Security Keys
SECRET_KEY = os.getenv('SECRET_KEY')
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')

# Sentry Configuration
SENTRY_DSN = os.getenv('SENTRY_DSN')

# MySQL Database Configuration
MYSQL = {
    'HOST': os.getenv('MYSQL_HOST'),
    'PORT': int(os.getenv('MYSQL_PORT', 3306)),
    'USER': os.getenv('MYSQL_USER'),
    'PASSWORD': os.getenv('MYSQL_PASSWORD'),
    'DATABASE': os.getenv('MYSQL_DATABASE'),
}

# Google Sheets Configuration
SHEETS = {
    'CREDENTIAL_FILE': 'utils/aso_experiments.json',
    'EXPERIMENTS_SHEET_NAME': 'Automated_Testing_Experiments',
    'VARIANTS_SHEET_NAME': 'Automated_Testing_Variants',
    'APPS_SHEET': 'Publisher/App Settings',
    'DEFAULT_SPREADSHEET_ID': '16img22ajmEOcVyWrS3sdXSneN0imFqT0VDYpYpCfLe8'
}

# Logging Configuration
LOGGING = {
    'DEFAULT_LEVEL': 'DEBUG',
    'LOG_DIR': '/tmp',
    'DATE_FORMAT': '%Y-%m-%d_%H-%M'
}

# Playwright Configuration
PLAYWRIGHT = {
    'TIMEOUT': 20000,
    'LOCATOR_TIMEOUT': 6000,
    'SLOW_MO': 0,
    'VIEWPORT': {
        'width': 1500,
        'height': 800
    }
}

# Image Processing
IMAGE_SETTINGS = {
    'DEFAULT_ICON_SIZE': (512, 512),
    'DEFAULT_FEATURE_SIZE': (1024, 500),
    'DEFAULT_SCREENSHOT_SIZE': (2208, 1242),
    'SUPPORTED_FORMATS': {'PNG', 'JPEG', 'WEBP'},
    'OUTPUT_FORMAT': 'PNG'
}

# API URLs
URLS = {
    'PLAY_CONSOLE_BASE': 'https://play.google.com',
    'PLAY_CONSOLE_DEVELOPERS': 'https://play.google.com/console/developers',
    'LOGIN_URL': 'https://superuser.com/users/login?ssrc=head&returnurl=https%3a%2f%2fsuperuser.com%2f'
}

# File Paths
PATHS = {
    'ASO_EXPERIMENTS_JSON': 'utils/aso_experiments.json',
    'TEMP_DIR': '/tmp',
    'CERTS_DIR': 'certs'
}

# Retry Configuration
RETRY = {
    'MAX_ATTEMPTS': 3,
    'DELAY_SECONDS': 80
} 

# Slack Hooks
SLACK_HOOKS = {
    'PHITURE_BUGS': os.getenv('BUGS_SLACK_HOOK_URL'),
    'PHITURE_HOOK': os.getenv('NOTIFICATION_SLACK_HOOK_URL')
}