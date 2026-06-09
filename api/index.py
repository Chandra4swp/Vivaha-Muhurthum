import sys
import os
import logging

# Set up logging to help debug issues
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app
    logger.info("Successfully imported Flask app from app.py")
except Exception as e:
    logger.error(f"Failed to import Flask app: {e}", exc_info=True)
    raise

# Export the app for Vercel to use
handler = app
