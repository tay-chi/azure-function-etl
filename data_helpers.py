# Data extraction and formatting helper functions

import logging
from datetime import datetime


def get_json_value(data, *path):
    
    """
    Navigate nested JSON and extract value
    Handles both ci/value pattern AND plain values
    
    Args:
        data: The JSON object to navigate
        *path: Keys to navigate through (e.g., 'value', 'data', 'city')
    
    Returns:
        The extracted value as a string, or empty string if not found
    """
    
    try:
        current = data
        # Navigate through each key in the path
        for key in path:
            if isinstance(current, dict):
                current = current.get(key, {})
            else:
                return ""
        
        # Check if it has ci/value structure
        if isinstance(current, dict) and 'value' in current:
            # Extract just the value part
            return current['value'] if current['value'] is not None else ""
        
        # Otherwise return the value as-is
        return current if current is not None else ""
        
    except Exception as e:
        logging.warning(f"Error extracting value at path {path}: {e}")
        return ""


def get_owner_contact(project):
    
    """
    Find the Owner contact from the contacts array
    
    Args:
        project: The project JSON object
    
    Returns:
        The Owner contact dict, or None if not found
    """
    
    try:
        contacts = project.get('value', {}).get('data', {}).get('contacts', [])
        
        for contact in contacts:
            role = contact.get('contactRole', {}).get('value', '')
            if role == 'Owner':
                return contact
        
        logging.warning("No Owner contact found in project")
        return None
        
    except Exception as e:
        logging.error(f"Error finding owner contact: {e}")
        return None


def format_phone(area_code, number):
    
    """
    Format phone number from area code and number
    
    Args:
        area_code: Area code string (e.g., "901")
        number: Phone number string (e.g., "4953300")
    
    Returns:
        Formatted phone string (e.g., "901-4953300"), or empty if both missing
    """
   
    if area_code and number:
        return f"{area_code}-{number}"
    elif number:
        return number
    elif area_code:
        return area_code
    return ""


def format_date_to_iso(date_value):
    
    """
    Convert date to ISO format: 2025-10-31T00:00:00
    Handles CiText structure, null values, and various date formats
    
    Args:
        date_value: Could be null, a string, or a dict with ci/value
    
    Returns:
        Formatted date string in ISO format, or empty string if invalid/null
    """
    
    # Handle null or empty
    if not date_value or date_value == "null":
        return ""
    
    # If it's already a string, use it
    if isinstance(date_value, str):
        date_string = date_value
    # If dict with ci/value, extract value
    elif isinstance(date_value, dict) and 'value' in date_value:
        date_string = date_value['value']
        if not date_string:
            return ""
    else:
        return ""
    
    try:
        # Remove timezone info if present (Z or +00:00)
        date_clean = date_string.replace('Z', '').split('+')[0].split('T')[0].strip()
        
        # Try multiple date formats
        date_formats = [
            "%Y-%m-%d",      # 2025-10-31
            "%d/%m/%Y",      # 31/10/2025 
            "%m/%d/%Y",      # 10/31/2025 
            "%Y/%m/%d",      # 2025/10/31
            "%d-%m-%Y",      # 31-10-2025
            "%m-%d-%Y"       # 10-31-2025
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_clean, fmt)
                return dt.strftime("%Y-%m-%dT00:00:00")
            except ValueError:
                continue
        
        # If no format worked, log and return empty
        logging.warning(f"Could not parse date '{date_string}' with any known format")
        return ""
        
    except Exception as e:
        logging.warning(f"Error formatting date '{date_string}': {e}")
        return ""


def clean_text(value):
    
    """
    Clean text by trimming whitespace and removing newlines/carriage returns
    
    Args:
        value: Any value (string or other)
    
    Returns:
        Cleaned string, or original value if not a string
    """
   
    if not isinstance(value, str):
        return value
    
    # Replace newlines and carriage returns with space
    cleaned = value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    
    # Replace multiple spaces with single space
    while '  ' in cleaned:
        cleaned = cleaned.replace('  ', ' ')
    
    # Trim leading/trailing whitespace
    return cleaned.strip()