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
from azure.graphrbac import GraphRbacManagementClient
from azure.common.credentials import UserPassCredentials
import logging
import sys
import yaml
import getpass

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


def get_graphclient(config_file):
    if config_file['options']['fetch_from_azure_ad'] == 'true':
        logger.info("logging in for graph API")
        print()
        credentials = UserPassCredentials(
                   config_file['azure']['user'],
                   getpass.getpass(
                       prompt='Please enter Azure account password: '
                       ),
                   resource="https://graph.windows.net"
           )
        tenant_id = config_file['azure']['tenant']
        graphrbac_client = GraphRbacManagementClient(
           credentials,
           tenant_id
        )
        return graphrbac_client
    else:
        logger.info(
                "Option to fetch users from Azure AD is disabled in config"
                )
        return None


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
            get_mail(config, context.scenario.owner_id)
            scenariosOwners.append(context.scenario.owner_id)
        logger.info(f"Owners: {scenariosOwners}")
        return scenariosOwners
    except cosmotech_api.ApiException as e:
        logger.error(
                "Exception when calling " +
                "scenario_api->find_all_scenarios: " +
                f"{e}"
                )


def get_mail(config, oid):
    if oid not in config.mapping:
        if config.config_file['options']['fetch_from_azure_ad'] == 'true':
            user = config.graph_client.users.get(oid)
            logger.debug("New user info fetch:")
            logger.debug(user)
            logger.info(f"Adding user {user.object_id} - " +
                        f"{user.user_principal_name} - " +
                        f"{user.display_name}")
            config.mapping[user.object_id] = user.user_principal_name
        else:
            logger.info(f"User {oid} not found and Azure AD disabled")
    logger.info(f"Getting user {oid} from mapping")
    mail = config.mapping.get(oid)
    if mail is None:
        logger.debug(f"Cannot find user {oid} in mapping")
        mail = config.config_file['options']['fallback_admin']
        logger.info(f"Cannot find user {oid} in mapping. " +
                    f"fallback admin to {mail}")

    if not mail:
        logger.error(f"Bad mail info provided for {oid}")
    else:
        logger.info(f"{oid}: Returning mail {mail}")


def get_config():
    with open('config.yaml', 'r') as config_file:
        return yaml.safe_load(config_file)


def build_config(api_client, graph_client, config_file):
    mapping = {}
    if config_file['mapping'] is not None:
        mapping = config_file['mapping']
    return Config(
            api_client=api_client,
            graph_client=graph_client,
            config_file=config_file,
            mapping=mapping
            )


def migrate():
    """Migrate a platform oid to RBAC security v2"""
    logging.info("Migration start")
    config_file = get_config()
    with get_apiclient(config_file) as api_client:
        graph_client = get_graphclient(config_file)
        config = build_config(
                api_client,
                graph_client,
                config_file)
        migrate_organizations(config)


@dataclass
class Config(object):
    api_client: str
    graph_client: str
    config_file: str
    mapping: dict


class Context:
    organization: Organization
    workspace: Workspace
    scenario: Scenario


if __name__ == "__main__":
    migrate()
