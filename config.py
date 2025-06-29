# src/config.py

import os
import logging

# --- Database Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # accountingtest/src/ -> accountingtest/
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_NAME = "accounting_data.db"
DATABASE_PATH = os.path.join(DATA_DIR, DB_NAME)

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- Logging Configuration ---
LOGS_DIR = os.path.join(os.path.dirname(BASE_DIR), "logs") # accountingtest/logs/
LOG_FILE_NAME = "app.log"
LOG_FILE_PATH = os.path.join(LOGS_DIR, LOG_FILE_NAME)

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': logging.DEBUG,
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': LOG_FILE_PATH,
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'level': logging.INFO,
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': logging.DEBUG,
    },
}

# --- Application Settings (Defaults that might be overridden by DB settings) ---
DEFAULT_CURRENCY = "IRR" # Example, can be changed
COMPANY_NAME = "نام شرکت شما" # Example, can be loaded from DB Settings
# تنظیمات لاگ‌گیری
LOG_LEVEL = logging.DEBUG  # می‌توانید از logging.INFO, logging.WARNING, logging.ERROR هم استفاده کنید
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s.%(funcName)s:%(lineno)d - %(message)s'