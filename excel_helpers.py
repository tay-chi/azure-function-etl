# Excel file processing utilities

import logging
import pandas as pd


##### EXCEL PROCESSING HELPERS #####


def read_property_type_correlation(excel_file):
    
    """Read property type correlation data from Excel file"""
    
    logging.info("Reading property type correlations from Excel...")
    
    # Read the PropertyType-coorelation sheet
    df = pd.read_excel(excel_file, sheet_name="PropertyType-correlation")
    
    correlations = {}
    
    for index, row in df.iterrows():
        
        # The project type is in the "Dodge - Sub section" column
        project_type = row["Dodge - Sub section"]
        industry = row["CRM - Industry"]
        industry_code = row["CRM - Industry Code"]
        segment = row["CRM - Segment "]
        segment_code = row["CRM - Segment Code"]
        include = row.get("Include", "N")  # Read Include column
        
        # Skip empty rows
        if pd.isna(project_type):
            continue
        
        # Clean up the project type name
        project_type = str(project_type).strip()
        
        # Store the correlation data
        correlations[project_type] = {
            "industry": industry if not pd.isna(industry) else "",
            "industry_code": str(industry_code) if not pd.isna(industry_code) else "",
            "segment": segment if not pd.isna(segment) else "",
            "segment_code": segment_code if not pd.isna(segment_code) else "",
            "include": str(include).strip().upper() if not pd.isna(include) else "N",
        }
    
    logging.info(f"Found {len(correlations)} property type correlations")
    
    return correlations