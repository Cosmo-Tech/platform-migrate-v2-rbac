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
Copy and complete config.yaml.template to config.yaml.
``` bash
pipenv shell
pipenv install
python main.py
```

## Report example format
[RESOURCE];[ID];[OWNER_ID];[OWNER_MAIL];[USERS];[STATUS]
organization;o-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;user1@cosmotech.com,user2@cosmotech.com;UPDATED
workspace;w-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;user1@cosmotech.com,user2@cosmotech.com;EXIST
scenario;s-asfsdfdfds;13123123-31312-13123;admin@cosmotech.com;user1@cosmotech.com,user2@cosmotech.com;UPDATED
