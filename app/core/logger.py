# app/logger.py
import logging
import os

# Create a custom logger
logger = logging.getLogger('app_logger')

# Set the logging level
logger.setLevel(logging.DEBUG)

# Create a console handler and set the logging level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a file handler and set the logging level
log_path = os.path.join(os.path.dirname(__file__), 'app.log')
fh = logging.FileHandler(log_path)
fh.setLevel(logging.INFO)

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)
logger.addHandler(fh)

# Log the start of the application
logger.info('Logger initialized successfully.')
