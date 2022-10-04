# Copyright (c) Cosmo Tech.
# Licensed under the MIT license.

from azure.identity import DefaultAzureCredential
import cosmotech_api
from cosmotech_api import Configuration
from cosmotech_api import ApiClient
from cosmotech_api.api import organization_api
import logging
import sys
import yaml

logger = logging.getLogger()
fileHandler = logging.FileHandler("application.log")
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)
logger.setLevel(logging.DEBUG)


def get_apiclient(config):
    host = config['platform']['url']
    scope = config['platform']['scope']

    logger.debug("logging in")
    credential = DefaultAzureCredential()
    logger.debug("Getting token")
    token = credential.get_token(scope)

    configuration = Configuration(
        host=host,
        discard_unknown_keys=True,
        access_token=token.token
    )

    return ApiClient(configuration)


def migrate_organizations(config, api_client):
    try:
        api_organization = organization_api.OrganizationApi(api_client)
        organizations = api_organization.find_all_organizations()
        logger.debug(organizations)
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "organization_api->find_all_datasets: " +
                f"{e}"
                )


def get_config():
    with open('config.yaml', 'r') as config_file:
        return yaml.safe_load(config_file)


def migrate():
    """Migrate a platform oid to RBAC security v2"""
    logging.info("Migration start")
    config = get_config()
    with get_apiclient(config) as api_client:
        migrate_organizations(config, api_client)


if __name__ == "__main__":
    migrate()
