# File tracking and logging utilities

import logging
import os
import json
from sharepoint_helpers import upload_file_to_sharepoint


##### FILE TRACKING HELPERS #####


def load_processed_files_log(log_file):
    
    """Load the processed API runs and DRNumbers"""
    
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                data = json.load(f)
                
                # Convert list back to set for processed_dr_numbers
                if isinstance(data.get("processed_dr_numbers"), list):
                    data["processed_dr_numbers"] = set(data["processed_dr_numbers"])
                
                # Ensure api_runs exists
                if "api_runs" not in data:
                    data["api_runs"] = {}
                
                return data
        except:
            return {"api_runs": {}, "processed_dr_numbers": set()}
    
    return {"api_runs": {}, "processed_dr_numbers": set()}


def save_processed_files_log(log_file, processed_data, sharepoint_folder_path=None):
    
    """Save the API runs and DRNumbers locally and to SharePoint"""
    
    # Convert set to list for JSON serialization
    processed_data_copy = processed_data.copy()
    processed_data_copy["processed_dr_numbers"] = list(
        processed_data["processed_dr_numbers"]
    )
    
    with open(log_file, "w") as f:
        json.dump(processed_data_copy, f, indent=2)
    
    # Upload to SharePoint if folder path provided
    if sharepoint_folder_path is not None:
        if sharepoint_folder_path == "":
            full_path = "processed_files.json"
        else:
            full_path = f"{sharepoint_folder_path}/processed_files.json"
        
        upload_file_to_sharepoint(log_file, full_path)