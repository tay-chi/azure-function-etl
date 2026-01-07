# Blob storage operations

import logging
import os
from azure.storage.blob import ContainerClient


##### BLOB STORAGE HELPERS #####


def upload_csv_to_blob(csv_file_path):
   
    """Upload CSV to blob storage for middleware"""
    
    try:
        sas_url = os.environ.get("BLOB_SAS_URL")
        
        if not sas_url:
            logging.error("BLOB_SAS_URL not configured")
            return False
        
        container_client = ContainerClient.from_container_url(sas_url)
        
        file_name = os.path.basename(csv_file_path)
        blob_name = f"Leads/Production/{file_name}"
        
        with open(csv_file_path, "rb") as data:
            blob_client = container_client.get_blob_client(blob=blob_name)
            blob_client.upload_blob(data, overwrite=True)
        
        logging.info(f"Uploaded file to blob storage: {blob_name}")
        return True
    
    except Exception as e:
        logging.error(f"Failed to upload to blob storage: {e}")
        return False