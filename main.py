# Copyright (c) Cosmo Tech.
# Licensed under the MIT license.

from azure.identity import DefaultAzureCredential
import cosmotech_api
import logging
import sys

logger = logging.getLogger()
fileHandler = logging.FileHandler("application.log")
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)
logger.setLevel(logging.DEBUG)

def migrate():
    """Migrate a platform oid to RBAC security v2"""
    logging.info("Migration start")


if __name__ == "__main__":
    migrate()
