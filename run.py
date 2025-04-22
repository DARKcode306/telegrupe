#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram Bot Runner Script
This script is used to start the Telegram bot separately from any web application.
"""

import os
import sys
import logging
import traceback
from main import main

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        print("Starting Telegram bot...")
        # Run the main function from main.py
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)