# Construction Leads Azure Function - Main Entry Point

import logging
import os
import azure.functions as func
from datetime import datetime
from excel_helpers import read_property_type_correlation
from sharepoint_helpers import download_file_from_sharepoint
from blob_helpers import upload_csv_to_blob
from tracking import load_processed_files_log, save_processed_files_log
from dodge_api import search_dodge_api, process_api_projects


app = func.FunctionApp()


##### CONFIG/SETUP HELPER #####


def load_processor_config(excel_file="dodgeMapping.xlsx"):
    
    """Load all configuration needed for API processing"""
    
    output_folder = "/tmp/processed_csv_files"
    os.makedirs(output_folder, exist_ok=True)
    
    # Log file path
    
    log_file = os.path.join(output_folder, "processed_files.json")
    
    # Download tracking file from SharePoint first
   
    download_response = download_file_from_sharepoint(
        
        "processed_files.json/processed_files.json"
    )
    
    if download_response.status_code == 200:
        with open(log_file, "wb") as f:
            f.write(download_response.content)
        logging.info("Downloaded existing tracking file from SharePoint")
    
    # Load tracking file
  
    processed_data = load_processed_files_log(log_file)
    
    logging.info(f"Loaded {len(processed_data.get('api_runs', {}))} previous API runs")
    logging.info(
        f"Loaded {len(processed_data.get('processed_dr_numbers', set()))} processed DRNumbers"
    )
    
    # Load property type correlations only
   
    try:
        correlations = read_property_type_correlation(excel_file)
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return None, None, None
    
    logging.info(f"Loaded {len(correlations)} property type correlations")
    
    return correlations, processed_data, log_file


##### PROCESSING HELPERS #####


def process_api_run(correlations, processed_data, log_file):
   
    """
    Execute one API run: search, process, create CSV, upload

    Args:
        correlations: Property type correlations from Excel
        processed_data: Tracking data with api_runs and processed_dr_numbers
        log_file: Path to tracking JSON file

    Returns:
        None (updates processed_data in place)
    """
    
    output_folder = "/tmp/processed_csv_files"
    run_timestamp = datetime.now().isoformat()
    
    logging.info("=" * 60)
    logging.info(f"Starting API run at {run_timestamp}")
    logging.info("=" * 60)
    
    try:
        # Search Dodge API for projects
        
        projects = search_dodge_api(correlations, days_back=2)
        
        if not projects:
            logging.warning("No projects returned from API")
            
            # Log this run
           
            processed_data["api_runs"][run_timestamp] = {
                "status": "success",
                "projects_found": 0,
                "unique_projects": 0,
                "duplicates_skipped": 0,
                "output_file": None,
                "blob_uploaded": False,
                "sharepoint_uploaded": False,
            }
            
            save_processed_files_log(log_file, processed_data, "")
            return
        
        logging.info(f"API returned {len(projects)} projects")
        
        # Process projects into CSV
       
        (
            success,
            output_path,
            unique_count,
            duplicates_count,
            new_dr_numbers,
            error_msg,
        ) = process_api_projects(
            projects,
            correlations,
            processed_data["processed_dr_numbers"],
            output_folder,
        )
        
        if not success:
            logging.error(f"Processing failed: {error_msg}")
            
            # Log failed run
            
            processed_data["api_runs"][run_timestamp] = {
                "status": "failed",
                "error": error_msg,
                "projects_found": len(projects),
                "unique_projects": 0,
                "duplicates_skipped": 0,
                "output_file": None,
                "blob_uploaded": False,
                "sharepoint_uploaded": False,
            }
            
            save_processed_files_log(log_file, processed_data, "")
            return
        
        if not output_path:
           
            # No CSV created (no qualifying projects or all duplicates)
            
            logging.info("No CSV output - no qualifying projects found")
            
            processed_data["api_runs"][run_timestamp] = {
                "status": "success",
                "projects_found": len(projects),
                "unique_projects": 0,
                "duplicates_skipped": duplicates_count,
                "output_file": None,
                "blob_uploaded": False,
                "sharepoint_uploaded": False,
            }
            
            # Update DRNumbers even if no output
            
            processed_data["processed_dr_numbers"].update(new_dr_numbers)
            save_processed_files_log(log_file, processed_data, "")
            return
        
        # Upload CSV to Blob Storage
        
        blob_success = upload_csv_to_blob(output_path)
        
        if not blob_success:
            logging.error(f"CRITICAL: Blob storage upload failed for {output_path}")
            
            processed_data["api_runs"][run_timestamp] = {
                "status": "failed",
                "error": "Blob storage upload failed",
                "projects_found": len(projects),
                "unique_projects": unique_count,
                "duplicates_skipped": duplicates_count,
                "output_file": os.path.basename(output_path),
                "blob_uploaded": False,
                "sharepoint_uploaded": False,
            }
            
            save_processed_files_log(log_file, processed_data, "")
            return
        
        logging.info(f"SUCCESS: Blob storage upload completed for {output_path}")
        
        # Upload CSV to SharePoint (optional/for records)
       
        from sharepoint_helpers import upload_file_to_sharepoint
        sp_success = upload_file_to_sharepoint(output_path, "Processed")
        
        if sp_success:
            logging.info(f"SharePoint upload completed for {output_path}")
        else:
            logging.warning(
                f"SharePoint upload failed for {output_path} - continuing anyway"
            )
        
        # Log successful run
        
        processed_data["api_runs"][run_timestamp] = {
            "status": "success",
            "projects_found": len(projects),
            "unique_projects": unique_count,
            "duplicates_skipped": duplicates_count,
            "output_file": os.path.basename(output_path),
            "blob_uploaded": True,
            "sharepoint_uploaded": sp_success,
        }
        
        # Update DRNumbers
        
        processed_data["processed_dr_numbers"].update(new_dr_numbers)
        save_processed_files_log(log_file, processed_data, "")
        
        logging.info("=" * 60)
        logging.info(f"API run completed successfully")
        logging.info(f"  - Projects found: {len(projects)}")
        logging.info(f"  - Unique processed: {unique_count}")
        logging.info(f"  - Duplicates skipped: {duplicates_count}")
        logging.info(f"  - CSV uploaded to Blob: {blob_success}")
        logging.info("=" * 60)
    
    except Exception as e:
        logging.error(f"Unexpected error in API run: {e}")
        
        processed_data["api_runs"][run_timestamp] = {
            "status": "failed",
            "error": f"Unexpected error: {str(e)}",
            "projects_found": 0,
            "unique_projects": 0,
            "duplicates_skipped": 0,
            "output_file": None,
            "blob_uploaded": False,
            "sharepoint_uploaded": False,
        }
        
        save_processed_files_log(log_file, processed_data, "")


##### MAIN TIMER FUNCTION #####


@app.timer_trigger(
    schedule="0 0 11 */2 * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def dodge_timer_trigger(myTimer: func.TimerRequest) -> None:
    """Timer trigger to process Dodge API leads - runs every 2 days at 11 AM EST"""
    
    if myTimer.past_due:
        logging.info("The timer is past due!")
    
    logging.info("=" * 60)
    logging.info("Dodge API Timer Trigger - Starting")
    logging.info("=" * 60)
    
    try:
        # Load configuration
       
        correlations, processed_data, log_file = load_processor_config(
            "dodgeMapping.xlsx"
        )
        
        if correlations is None:
            logging.error("Failed to load configuration - aborting")
            return
        
        # Execute API run
        
        process_api_run(correlations, processed_data, log_file)
        
        logging.info("Dodge API Timer Trigger - Completed")
    
    except Exception as e:
        logging.error(f"Fatal error in timer trigger: {e}")
        raise