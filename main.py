# Copyright (c) Cosmo Tech.
# Licensed under the MIT license.

from azure.identity import DefaultAzureCredential
import cosmotech_api
from cosmotech_api import Configuration
from cosmotech_api import ApiClient
from cosmotech_api.api import organization_api
from cosmotech_api.api import workspace_api
from cosmotech_api.api import scenario_api
from cosmotech_api.model.organization import Organization
from cosmotech_api.model.workspace import Workspace
from cosmotech_api.model.scenario import Scenario
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
logger.setLevel(logging.INFO)
TRACE_DOCUMENTS = False


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
        if TRACE_DOCUMENTS:
            logger.debug(organizations)
        for organization in organizations:
            context = Context()
            context.organization = organization
            migrate_organization(config, context)
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "organization_api->find_all_organizations: " +
                f"{e}"
                )


def migrate_organization(config, context):
    logger.info("Migrating organization: " +
                f"{context.organization.id} - " +
                f"{context.organization.name}")
    migrate_workspaces(config, context)


def migrate_workspaces(config, context):
    logger.info("Migrating workspaces")
    try:
        api_workspace = workspace_api.WorkspaceApi(config.api_client)
        workspaces = api_workspace.find_all_workspaces(context.organization.id)
        if TRACE_DOCUMENTS:
            logger.debug(workspaces)
        workspacesOwners = []
        for workspace in workspaces:
            context.workspace = workspace
            workspaceOwners = migrate_workspace(config, context)
            workspacesOwners.extend(workspaceOwners)
        return workspacesOwners
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "workspace_api->find_all_workspaces: " +
                f"{e}"
                )


def migrate_workspace(config, context):
    logger.info("Migrating workspace: " +
                f"{context.workspace.key} - " +
                f"{context.workspace.id} - " +
                f"{context.workspace.name}")
    owners = migrate_scenarios(config, context)
    return owners


def migrate_scenarios(config, context):
    logger.info("Migrating scenarios")
    try:
        api_scenario = scenario_api.ScenarioApi(config.api_client)
        scenarios = api_scenario.find_all_scenarios(
                context.organization.id,
                context.workspace.id)
        if TRACE_DOCUMENTS:
            logger.debug(scenarios)
        scenariosOwners = []
        for scenario in scenarios:
            context.scenario = scenario
            logger.info(
                    "Scenario: " +
                    f"{context.scenario.id} - " +
                    f"{context.scenario.name} - " +
                    f"{context.scenario.owner_id}"
                    )
            scenariosOwners.append(context.scenario.owner_id)
        logger.info(f"Owners: {scenariosOwners}")
        return scenariosOwners
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "scenario_api->find_all_scenarios: " +
                f"{e}"
                )


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


class Context:
    organization: Organization
    workspace: Workspace
    scenario: Scenario


if __name__ == "__main__":
    migrate()
