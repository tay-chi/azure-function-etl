### Configuration constants for Dodge Leads Azure Function ###

import os

# SharePoint Configuration (set in Azure Function App Settings)

SITE_ID = os.environ.get("SHAREPOINT_SITE_ID", "")
LEADS_DRIVE_ID = os.environ.get("SHAREPOINT_DRIVE_ID", "")

# Dodge API Configuration

DODGE_API_BASE_URL = "https://www.construction.com/api/1.0/int"