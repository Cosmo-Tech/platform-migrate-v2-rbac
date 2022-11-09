# Copyright (c) Cosmo Tech.
# Licensed under the MIT license.
import csv
import getpass
import logging
import sys
from dataclasses import dataclass

import cosmotech_api
import yaml
from azure.common.credentials import UserPassCredentials
from azure.graphrbac import GraphRbacManagementClient
from azure.graphrbac.models import GraphErrorException
from azure.identity import DefaultAzureCredential
from cosmotech_api import ApiClient
from cosmotech_api import Configuration
from cosmotech_api.api import organization_api
from cosmotech_api.api import scenario_api
from cosmotech_api.api import workspace_api
from cosmotech_api.model.organization import Organization
from cosmotech_api.model.scenario import Scenario
from cosmotech_api.model.workspace import Workspace

csv_file = open('rbac_migration_report.csv', 'w', encoding='UTF8')
header_csv = ['RESOURCE', 'ID', 'OWNER_ID', 'OWNER_MAIL', 'STATUS', 'USERS']
csv_writer = csv.writer(csv_file)
csv_writer.writerow(header_csv)

logger = logging.getLogger()
fileHandler = logging.FileHandler("application.log")
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)
logger.setLevel(logging.INFO)
TRACE_DOCUMENTS = False


def get_graphclient(config_file):
    if config_file['options']['fetch_from_azure_ad']:
        logger.info("logging in for graph API")
        print()
        credentials = UserPassCredentials(
            config_file['azure']['user'],
            getpass.getpass(prompt='Please enter Azure account password: '),
            resource="https://graph.windows.net")
        tenant_id = config_file['azure']['tenant']
        graphrbac_client = GraphRbacManagementClient(credentials, tenant_id)
        return graphrbac_client
    else:
        logger.info(
            "Option to fetch users from Azure AD is disabled in config")
        return None


def get_apiclient(config_file):
    host = config_file['platform']['url']
    scope = config_file['platform']['scope']

    logger.debug("logging in")
    credential = DefaultAzureCredential()
    logger.debug("Getting token")
    token = credential.get_token(scope)

    configuration = Configuration(host=host,
                                  discard_unknown_keys=True,
                                  access_token=token.token)

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
        logger.error("Exception when calling " +
                     "organization_api->find_all_organizations: " + f"{e}")


def get_organization_by_id(config, context, organization_id):
    try:
        api_organization = organization_api.OrganizationApi(config.api_client)
        organization = api_organization.find_organization_by_id(
            organization_id
        )
        context.organization = organization
    except cosmotech_api.ApiException as e:
        logger.error("Exception when calling " +
                     "organization_api->find_organization_by_id: " + f"{e}")


def migrate_organization(config, context):
    logger.info("Migrating organization: " + f"{context.organization.id} - " +
                f"{context.organization.name}")
    users = migrate_workspaces(config, context)
    if users:
        users.append(get_mail(config, context.organization.owner_id))
    else:
        users = None
    update_organization(config, context, users)


def migrate_workspaces(config, context):
    logger.info("Migrating workspaces")
    try:
        api_workspace = workspace_api.WorkspaceApi(config.api_client)
        workspaces = api_workspace.find_all_workspaces(context.organization.id)
        if TRACE_DOCUMENTS:
            logger.debug(workspaces)
        users = []
        for workspace in workspaces:
            context.workspace = workspace
            workspace_owners = migrate_workspace(config, context)
            if workspace_owners:
                users.extend(workspace_owners)
        return users
    except cosmotech_api.ApiException as e:
        logger.error("Exception when calling " +
                     "workspace_api->find_all_workspaces: " + f"{e}")


def migrate_workspace(config, context):
    logger.info("Migrating workspace: " + f"{context.workspace.key} - " +
                f"{context.workspace.id} - " + f"{context.workspace.name}")
    users = migrate_scenarios(config, context)
    if users:
        users.append(get_mail(config, context.workspace.owner_id))
    else:
        users = None
    update_workspace(config, context, users)
    return users


def migrate_scenarios(config, context):
    logger.info("Migrating scenarios")
    try:
        api_scenario = scenario_api.ScenarioApi(config.api_client)
        scenarios = api_scenario.find_all_scenarios(context.organization.id,
                                                    context.workspace.id)
        if TRACE_DOCUMENTS:
            logger.debug(scenarios)
        scenarios_owners = []
        for scenario in scenarios:
            context.scenario = scenario
            logger.info("Scenario: " + f"{context.scenario.id} - " +
                        f"{context.scenario.name} - " +
                        f"{context.scenario.owner_id}")
            update_scenario(config, context)
            scenarios_owners.append(get_mail(config, context.scenario.owner_id))
        logger.info(f"Owners: {scenarios_owners}")
        return scenarios_owners
    except cosmotech_api.ApiException as e:
        logger.error("Exception when calling " +
                     "scenario_api->find_all_scenarios: " + f"{e}")


def update_organization(config, context, users):
    api_organization = organization_api.OrganizationApi(config.api_client)
    mail = get_mail(config, context.organization.owner_id)
    context.organization.security = get_security_object(mail, users)
    organization = api_organization.update_organization(
        context.organization.id,
        context.organization)
    updated = organization.security == context.organization.security
    csv_writer.writerow(['organization', organization.id, organization.owner_id,
                         mail, ('EXIST', 'UPDATED')[updated], ','.join(users if users else [])])
    if not updated:
        logger.warning('Organization %s not updated because security already exists'
                       % organization.id)


def update_workspace(config, context, users):
    api_workspace = workspace_api.WorkspaceApi(config.api_client)
    mail = get_mail(config, context.workspace.owner_id)
    context.workspace.security = get_security_object(mail, users)
    workspace = api_workspace.update_workspace(
        context.organization.id,
        context.workspace.id,
        context.workspace)
    updated = workspace.security == context.workspace.security
    csv_writer.writerow(['workspace', workspace.id, workspace.owner_id,
                         mail, ('EXIST', 'UPDATED')[updated], ','.join(users if users else [])])
    if not updated:
        logger.warning('Workspace %s not updated because security already exists'
                       % workspace.id)


def update_scenario(config, context):
    api_scenario = scenario_api.ScenarioApi(config.api_client)
    mail = get_mail(config, context.scenario.owner_id)
    context.scenario.security = get_security_object(mail)
    scenario = api_scenario.update_scenario(
        context.organization.id,
        context.workspace.id,
        context.scenario.id,
        context.scenario)
    updated = scenario.security == context.scenario.security
    csv_writer.writerow(['scenario', scenario.id, scenario.owner_id,
                         mail, ('EXIST', 'UPDATED')[updated], mail])
    if not updated:
        logger.warning('Scenario %s not updated because security already exists'
                       % scenario.id)


def get_security_object(mail, users=None):
    security = {
        "default": "none",
        "accessControlList": [{"id": mail, "role": "admin"}]
    }
    if users is not None:
        users_set = set(users)
        for user in users_set:
            if user != mail:
                security['accessControlList'].append(
                    {
                        "id": user,
                        "role": "user"
                    }
                )
    else:
        logger.warning("No users to add to security object")

    return security


def get_mail(config, oid):
    logger.info(f"Getting user {oid} from mapping")
    if oid not in config.mapping:
        if config.config_file['options']['fetch_from_azure_ad']:
            logger.info("User {oid} not found, searching in MS Graph")
            try:
                user = config.graph_client.users.get(oid)
                logger.debug("New user info fetch:")
                logger.debug(user)
                logger.info("Adding user to mapping: " +
                            f"{user.object_id} - " +
                            f"{user.user_principal_name} - " +
                            f"{user.display_name}")
                config.mapping[user.object_id] = user.user_principal_name
            except GraphErrorException as e:
                logger.debug(f"Exception calling msgraph: {e}")
                logger.info(f"{oid} does not exist in MS Graph")
        else:
            logger.info(f"User {oid} not found and Azure AD disabled")
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
        return mail


def get_config():
    with open('config.yaml', 'r') as config_file:
        return yaml.safe_load(config_file)


def build_config(api_client, graph_client, config_file):
    mapping = {}
    if 'mapping' not in config_file:
        config_file['mapping'] = {}
    if config_file['mapping'] is not None:
        mapping = config_file['mapping']
    return Config(api_client=api_client,
                  graph_client=graph_client,
                  config_file=config_file,
                  mapping=mapping)


def migrate():
    """Migrate a platform oid to RBAC security v2"""
    logging.info("Migration start")
    config_file = get_config()
    with get_apiclient(config_file) as api_client:
        graph_client = get_graphclient(config_file)
        config = build_config(api_client, graph_client, config_file)
        if 'organizationId' in config_file['options']:
            context = Context()
            get_organization_by_id(
                config,
                context,
                config_file['options']['organizationId'])
            migrate_organization(config, context)
        else:
            migrate_organizations(config)
    csv_file.close()


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
