# Copyright (c) Cosmo Tech.
# Licensed under the MIT license.

from azure.identity import DefaultAzureCredential
import cosmotech_api
from cosmotech_api import Configuration
from cosmotech_api import ApiClient
from cosmotech_api.api import organization_api
from cosmotech_api.api import workspace_api
from dataclasses import dataclass
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


def get_apiclient(config_file):
    host = config_file['platform']['url']
    scope = config_file['platform']['scope']

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


def migrate_organizations(config):
    logger.info("Migrating organizations")
    try:
        api_organization = organization_api.OrganizationApi(config.api_client)
        organizations = api_organization.find_all_organizations()
        logger.debug(organizations)
        for organization in organizations:
            migrate_organization(config, organization)
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "organization_api->find_all_datasets: " +
                f"{e}"
                )


def migrate_organization(config, organization):
    logger.info("Migrating organization: " +
                f"{organization.id} - " +
                f"{organization.name}")
    workspaces = migrate_workspaces(config, organization)


def migrate_workspaces(config, organization):
    logger.info("Migrating workspaces")
    try:
        api_workspace = workspace_api.WorkspaceApi(config.api_client)
        workspaces = api_workspace.find_all_workspaces(organization)
        logger.debug(workspaces)
        for workspace in workspaces:
            migrate_workspace(config, workspace)
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "workspace_api->find_all_workspaces: " +
                f"{e}"
                )


def migrate_workspace(config, workspace):
    logger.info("Migrating workspace: " +
                f"{workspace.key} - " +
                f"{workspace.id} - " +
                f"{workspace.name}")


def get_config():
    with open('config.yaml', 'r') as config_file:
        return yaml.safe_load(config_file)


def build_config(api_client, config_file):
    return Config(
            api_client=api_client,
            config_file=config_file
            )


def migrate():
    """Migrate a platform oid to RBAC security v2"""
    logging.info("Migration start")
    config_file = get_config()
    with get_apiclient(config_file) as api_client:
        config = build_config(api_client, config_file)
        migrate_organizations(config)


@dataclass
class Config(object):
    api_client: str
    config_file: str


if __name__ == "__main__":
    migrate()
