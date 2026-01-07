# SharePoint interaction functions
# Handles Graph API authentication and file operations

import logging
import os
import requests
from azure.identity import DefaultAzureCredential
from config import SITE_ID, LEADS_DRIVE_ID


##### SHAREPOINT HELPERS #####


def get_graph_headers():
    
    """Get authorization headers for Graph API"""
    
    credential = DefaultAzureCredential()
    token = credential.get_token("https://graph.microsoft.com/.default")
    
    return {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }


def download_file_from_sharepoint(file_name):
   
    """Download a file from SharePoint"""
    
    headers = get_graph_headers()
    headers.pop("Content-Type", None)
    
    download_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{LEADS_DRIVE_ID}/root:/{file_name}:/content"
    
    return requests.get(download_url, headers=headers)


def upload_file_to_sharepoint(file_content, target_path, target_filename=None):
    
    """Upload a file to SharePoint folder"""
    
    try:
        headers = get_graph_headers()
        headers["Content-Type"] = "application/octet-stream"
        
        # If file_content is a path, read the file
        if isinstance(file_content, str):
            with open(file_content, "rb") as f:
                file_data = f.read()
            if target_filename is None:
                target_filename = os.path.basename(file_content)
        else:
            file_data = file_content
        
        # Build full path
        if target_filename:
            full_path = f"{target_path}/{target_filename}"
        else:
            full_path = target_path
        
        url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{LEADS_DRIVE_ID}/root:/{full_path}:/content"
        response = requests.put(url, headers=headers, data=file_data)
        
        if response.status_code in [200, 201]:
            logging.info(f"Uploaded {target_filename or 'file'} to SharePoint: {target_path}")
            return True
        else:
            logging.error(f"Error uploading to SharePoint: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logging.error(f"Error uploading to SharePoint: {e}")
        return False