## Summary

* This Python script add security object to all of these components: **Scenario**, **Workspace**, **Organization**
* By default, all organizations are updated. If you need to update only one, define **organizationId** in **config.yaml**
* Logs can be found in **application.log**


### Script workflow:
1. Scenario owner, admins added to Scenario security as admins
2. Scenario, Workspace owners, admins added to Workspace security as admins
3. Organization, Workspace, Scenario owners, admins added to Organization security as admins
4. Report file **rbac_migration_report.csv** is created in ths end

### Constraints:
* This script works since API v2.
* If security already exists on component, it won't be updated.

### Installation
## Log in with az cli
[Install Powershell](https://learn.microsoft.com/en-us/powershell/scripting/install/install-debian?view=powershell-7.2)
[Install Powershell AZ module](https://learn.microsoft.com/en-us/powershell/azure/install-az-ps?view=azps-8.3.0)
``` powershell
Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force
```
Connect in powershell
``` powershell
Connect-AzAccount
```

## Run
Copy and complete [config.yaml.template](config.yaml.template) to config.yaml.
``` bash
pipenv shell
pipenv install
python main.py
```

## Report example format

[RESOURCE];[ID];[OWNER_ID];[OWNER_MAIL];[STATUS];[USERS]
organization;o-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;UPDATED;user1@cosmotech.com
workspace;w-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;EXIST;user1@cosmotech.com,user2@cosmotech.com
scenario;s-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;UPDATED;user1@cosmotech.com,user2@cosmotech.com,user3@cosmotech.com
