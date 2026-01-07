# API interaction functions

import logging
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from config import DODGE_API_BASE_URL
from country_codes import get_country_code
from data_helpers import get_json_value, get_owner_contact, format_phone, format_date_to_iso, clean_text


#####  API FUNCTIONS #####


def search_dodge_api(correlations, days_back=2):
    
    """
    Search Dodge API for projects

    Args:
        correlations: The property type correlation dict from Excel
        days_back: How many days back to search (default 2)

    Returns:
        List of project dictionaries from API
    """
    
    # Extract project types where Include='Y'
    
    included_types = []
    
    for project_type, corr_data in correlations.items():
        if corr_data.get("include") == "Y":
            included_types.append(project_type)
    
    logging.info(f"Searching for {len(included_types)} project types")
    
    # Calculate date range
   
    today = datetime.now()
    start_date = today - timedelta(days=days_back)
    
    # Date Format
   
    date_min = start_date.strftime("%Y-%m-%d")
    date_max = today.strftime("%Y-%m-%d")
    
    logging.info(f"Searching for projects from {date_min} to {date_max}")
    
    # Build search request
   
    search_request = {
        "criteria": {
            "projectTypes": included_types,
            "publishDateRange": {"min": date_min, "max": date_max},
        },
        "pagination": {"offset": 0, "limit": 100},
    }
    
    # Get API key and make request
   
    api_key = os.environ.get("DODGE_API_KEY")
    
    if not api_key:
        logging.error("DODGE_API_KEY not found in environment variables")
        return []
    
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    
    url = f"{DODGE_API_BASE_URL}/project/search"
    
    try:
        response = requests.post(url, headers=headers, json=search_request)
        response.raise_for_status()
        
        result = response.json()
        projects = result.get("projects", [])
        total = result.get("total", 0)
        
        logging.info(f"Retrieved {len(projects)} projects (total available: {total})")
        
        if total > 100:
            logging.warning(
                f"More than 100 projects available ({total}), but only retrieved first 100 due to API limit"
            )
        
        return projects
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"Error calling Dodge API: {e}")
        logging.error(f"Response content: {e.response.text}")
        return []
    
    except Exception as e:
        logging.error(f"Error calling Dodge API: {e}")
        return []


def process_api_projects(projects, correlations, processed_dr_numbers, output_folder):
    
    """
    Process API projects and create CSV

    Args:
        projects: List of projects from API
        correlations: Property type correlations from Excel
        processed_dr_numbers: Set of already processed DRNumbers
        output_folder: Where to save CSV

    Returns:
        Tuple: (success, output_path, unique_count, duplicates_count, new_dr_numbers, error_msg)
    """
    
    logging.info(f"Processing {len(projects)} projects from API...")
    
    csv_rows = []
    duplicates_skipped = 0
    new_dr_numbers = set()
    
    try:
        for project in projects:
            
            # Extract DRNumber for duplicate detection
            
            dr_number = get_json_value(project, "value", "summary", "dodgeReportNumber")
            
            if dr_number:
                if dr_number in processed_dr_numbers:
                    logging.info(f"Skipping duplicate DRNumber: {dr_number}")
                    duplicates_skipped += 1
                    continue
            
            # Extract primary project type from types array
            
            data = project.get("value", {}).get("data", {})
            types_array = data.get("types", [])
            
            primary_type = ""
            for type_item in types_array:
                if type_item.get("primary") == "Y":
                    primary_type = type_item.get("value", "")
                    break
            
            if not primary_type:
                logging.warning(f"Project has no primary type; Project: {dr_number}")
            
            # Check property type correlation
            
            if primary_type and primary_type in correlations:
                corr_data = correlations[primary_type]
                
                # Check if this project type should be included
               
                if corr_data.get("include", "N") != "Y":
                    logging.info(f"Skipping project (excluded type): {primary_type}")
                    continue
            else:
               
                # Project type not in Excel - skip by default
                
                if primary_type:
                    logging.info(f"Skipping project (unknown type): {primary_type}")
                continue
            
            # Initialize CRM data row
            
            crm_data = {}
            
## --- GROUP: Basic Project Info --- ##
            
            # Current_Opportunity_Phase (from stages array)
            
            stages_array = data.get("stages", [])
            
            primary_stage = ""
            for stage_item in stages_array:
                if stage_item.get("primary") == "Y":
                    primary_stage = stage_item.get("value", "")
                    break
            
            crm_data["Current_Opportunity_Phase"] = primary_stage
            
            # Name (ProjectTitle)
            
            crm_data["Name"] = get_json_value(
                project, "value", "data", "projectName", "value"
            )
            
            # Opportunity_Type (PrimaryProjectType)
            
            crm_data["Opportunity_Type"] = primary_type
            
            # Market_Segment_Code (MarketSegment)
            
            crm_data["Market_Segment_Code"] = ""
            
            # Opportunity_Description (ProjectNote)
            
            crm_data["Opportunity_Description"] = (
                project.get("value", {})
                .get("data", {})
                .get("notes", {})
                .get("notes", "")
            )
            
## --- GROUP: Project Address --- ##
            
            # Opportunity_Street (Address)
            
            crm_data["Opportunity_Street"] = get_json_value(
                project,
                "value",
                "data",
                "locations",
                "projectAddress",
                "addressLines",
                "line1",
                "value",
            )
            
            # Opportunity_City (City)
            
            crm_data["Opportunity_City"] = get_json_value(
                project, "value", "data", "locations", "projectAddress", "city", "value"
            )
            
            # Opportunity_State (State)
            
            crm_data["Opportunity_State"] = get_json_value(
                project,
                "value",
                "data",
                "locations",
                "projectAddress",
                "stateID",
                "value",
            )
            
            # Opportunity_Postal_Code (Zip)
            
            zip5 = get_json_value(
                project,
                "value",
                "data",
                "locations",
                "projectAddress",
                "zipCode5",
                "value",
            )
            crm_data["Opportunity_Postal_Code"] = str(zip5).zfill(5) if zip5 else ""
            
            # Opportunity_Country (Country) - with conversion
            
            country = get_json_value(
                project,
                "value",
                "data",
                "locations",
                "projectAddress",
                "countryID",
                "value",
            )
            crm_data["Opportunity_Country"] = get_country_code(country)
            
## --- GROUP: Project Dates --- ##
            
            # Start_Date (TargetStartDate)
           
            start_date_raw = get_json_value(
                project,
                "value",
                "data",
                "additionalDetails",
                "targetStartDate",
                "value",
            )
            crm_data["Start_Date"] = format_date_to_iso(start_date_raw)
            
            # End_Date (TargetCompletionDate)
            
            end_date_raw = get_json_value(
                project,
                "value",
                "data",
                "additionalDetails",
                "targetFinishDate",
                "value",
            )
            crm_data["End_Date"] = format_date_to_iso(end_date_raw)
            
            # --- FIND OWNER CONTACT ---
            
            owner = get_owner_contact(project)
            
            if owner:
                
                ## --- GROUP: Owner Company Info --- ##
                
                # Company (CompanyName)
               
                crm_data["Company"] = owner.get("firmName", "")
                
                # Account_Information_Phone (CompanyTelephone)
                
                crm_data["Account_Information_Phone"] = format_phone(
                    owner.get("phoneAreaCode", ""), owner.get("phoneNumber", "")
                )
                
                # Account_Information_Web_Site (CompanyWebsite)
               
                crm_data["Account_Information_Web_Site"] = owner.get("url", "")
                
                # Account_Information_Fax (CompanyFax)
               
                crm_data["Account_Information_Fax"] = format_phone(
                    owner.get("faxAreaCode", ""), owner.get("faxNumber", "")
                )
                
                # Account_Information_Longitude
                
                project_geo = data.get("geo", {})
                longitude = project_geo.get("longitude", "") if project_geo else ""
                crm_data["Account_Information_Longitude"] = (
                    longitude if longitude else "0.0000"
                )
                
                # Account_Information_Latitude (from project geo, not owner)
                
                latitude = project_geo.get("latitude", "") if project_geo else ""
                crm_data["Account_Information_Latitude"] = (
                    latitude if latitude else "0.0000"
                )
                
# --- GROUP: Owner Company Address ---
                
                # Account_Information_Street (CompanyAddress)
                
                address_lines = owner.get("addressLines", {})
                crm_data["Account_Information_Street"] = address_lines.get("line1", "")
                
                # Customer_Information_City (CompanyCity)
                
                crm_data["Customer_Information_City"] = owner.get("city", "")
                
                # Customer_Information_State (CompanyState)
                
                crm_data["Customer_Information_State"] = owner.get("state", "")
                
                # Account_Information_County (CompanyCounty)
                
                crm_data["Account_Information_County"] = owner.get("county", "")
                
                # Account_Information_Postal_Code (CompanyZip)
                
                zip5 = owner.get("zipCode5", "")
                crm_data["Account_Information_Postal_Code"] = (
                    str(zip5).zfill(5) if zip5 else ""
                )
                
                # Customer_Information_Country (CompanyCountry) - with conversion
                
                owner_country = owner.get("country", "")
                crm_data["Customer_Information_Country"] = get_country_code(
                    owner_country
                )
                
## --- GROUP: Owner Contact Person --- ##
                
                # Contact_Information_Job_Title (ContactTitle)
               
                crm_data["Contact_Information_Job_Title"] = owner.get(
                    "contactTitle", ""
                )
                
                # Split contact name into first and last
                
                contact_name = owner.get("contactName", "")
                
                if contact_name:
                    name_parts = contact_name.strip().split(
                        None, 1
                    )  # Split on first space
                    crm_data["Main_Contact_Person_First_name"] = (
                        name_parts[0] if len(name_parts) > 0 else ""
                    )
                    crm_data["Main_Contact_Person_Last_name"] = (
                        name_parts[1] if len(name_parts) > 1 else ""
                    )
                else:
                    crm_data["Main_Contact_Person_First_name"] = ""
                    crm_data["Main_Contact_Person_Last_name"] = ""
                
                # Contact_Information_EMail (ContactEmail)
               
                crm_data["Contact_Information_EMail"] = owner.get("email", "")
                
                # Contact_Information_Phone (ContactPhone)
                
                crm_data["Contact_Information_Phone"] = format_phone(
                    owner.get("phoneAreaCode", ""), owner.get("phoneNumber", "")
                )
            
            else:
                # No owner found - set all company/contact fields to empty
                
                crm_data["Company"] = ""
                crm_data["Account_Information_Phone"] = ""
                crm_data["Account_Information_Web_Site"] = ""
                crm_data["Account_Information_Fax"] = ""
                crm_data["Account_Information_Longitude"] = "0.0000"
                crm_data["Account_Information_Latitude"] = "0.0000"
                crm_data["Account_Information_Street"] = ""
                crm_data["Customer_Information_City"] = ""
                crm_data["Customer_Information_State"] = ""
                crm_data["Account_Information_County"] = ""
                crm_data["Account_Information_Postal_Code"] = ""
                crm_data["Customer_Information_Country"] = ""
                crm_data["Contact_Information_Job_Title"] = ""
                crm_data["Main_Contact_Person_First_name"] = ""
                crm_data["Main_Contact_Person_Last_name"] = ""
                crm_data["Contact_Information_EMail"] = ""
                crm_data["Contact_Information_Phone"] = ""
            
            ## --- PROPERTY TYPE CORRELATION FIELDS --- ##
            
            crm_data["Market_Segment_Code"] = corr_data.get("segment_code", "")
            
            ## --- CRM-SPECIFIC FIELDS --- ##
            
            crm_data["CRM_Field_1"] = "YOUR_VALUE_1"
            crm_data["CRM_Field_2"] = "YOUR_VALUE_2"
            crm_data["CRM_Field_3"] = "YOUR_VALUE_3"
            crm_data["CRM_Field_4"] = "YOUR_VALUE_4"
            crm_data["CRM_Field_5"] = "YOUR_VALUE_5"
            crm_data["CRM_Field_6"] = "YOUR_VALUE_6"
            crm_data["CRM_Field_7"] = "YOUR_VALUE_7"
            
            # Add DR number to tracking once project passes validation
            
            if dr_number:
                new_dr_numbers.add(dr_number)
            
            # Clean all text values before adding to output
            
            for key in crm_data:
                crm_data[key] = clean_text(crm_data[key])
            
            # Add to CSV rows
            
            csv_rows.append(crm_data)
        
        # Only create CSV if there are projects
        
        if len(csv_rows) > 0:
            
            # Create output filename with timestamp
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"processed_api_{timestamp}.xlsx"
            output_path = os.path.join(output_folder, output_filename)
            
            # Define CSV headers in order
            
            csv_headers = [
                "Current_Opportunity_Phase",
                "Name",
                "Opportunity_Street",
                "Opportunity_City",
                "Opportunity_State",
                "Opportunity_Postal_Code",
                "Opportunity_Country",
                "Market_Segment_Code",
                "Opportunity_Type",
                "Opportunity_Description",
                "Company",
                "Account_Information_Phone",
                "Account_Information_Web_Site",
                "Account_Information_Fax",
                "Account_Information_Longitude",
                "Account_Information_Latitude",
                "Account_Information_Street",
                "Customer_Information_City",
                "Customer_Information_State",
                "Account_Information_County",
                "Account_Information_Postal_Code",
                "Customer_Information_Country",
                "Contact_Information_Job_Title",
                "Contact_Information_EMail",
                "Contact_Information_Phone",
                "Start_Date",
                "End_Date",
                "Main_Contact_Person_First_name",
                "Main_Contact_Person_Last_name",
                "CRM_Field_1",
                "CRM_Field_2",
                "CRM_Field_3",
                "CRM_Field_4",
                "CRM_Field_5",
                "CRM_Field_6",
                "CRM_Field_7",
            ]
            
            # Write Excel file
            
            df = pd.DataFrame(csv_rows, columns=csv_headers)
            df.to_excel(output_path, index=False)
            
            logging.info(f"Created {output_filename}")
            logging.info(f"   - {len(csv_rows)} unique projects processed")
            
            if duplicates_skipped > 0:
                logging.info(f"   - {duplicates_skipped} duplicates skipped")
            
            return (
                True,
                output_path,
                len(csv_rows),
                duplicates_skipped,
                new_dr_numbers,
                None,
            )
        
        else:
            logging.info("No unique projects found to process")
            return True, None, 0, duplicates_skipped, new_dr_numbers, None
    
    except Exception as e:
        logging.error(f"Error processing projects: {e}")
        return False, None, 0, 0, set(), str(e)