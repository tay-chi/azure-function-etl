# Azure Function ETL Pipeline

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Azure Functions](https://img.shields.io/badge/Azure-Functions-0078D4.svg)
![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen.svg)

A serverless ETL pipeline built on Azure Functions that retrieves construction project data from an external REST API, transforms it for CRM import, and delivers it to downstream systems via blob storage.

---

## Background

### The Problem

The sales organization needed construction project leads to reach prospects during early planning stages. Manual lead research was consuming significant sales capacity that could be spent on relationship building and closing deals. Competitors with automated lead systems were reaching prospects first.

### The Solution

This system automates the entire lead pipeline:

- Scheduled execution retrieves new construction projects every 2 days
- Business rule filtering surfaces only relevant commercial flooring opportunities
- Field transformation maps API data to CRM-compatible format
- Duplicate prevention ensures leads are never processed twice
- Multi-destination delivery routes data to blob storage for middleware and SharePoint for audit trail

### Project Context

This is the third iteration of the pipeline. The original system processed XML file feeds, but when the vendor deprecated XML delivery entirely and switched to REST API-only, a complete architectural redesign was required. The rebuild was completed in under 4 calendar weeks while working part-time, with requirements reverse-engineered through API testing and analysis of sample data.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dodge API     │────▶│  Azure Function  │────▶│  Blob Storage   │
│  (Data Source)  │     │  (Timer Trigger) │     │  (Middleware)   │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                        ┌────────┴─────────┐
                        │                  │
                        ▼                  ▼
               ┌─────────────┐    ┌─────────────────┐
               │  SharePoint │    │  Excel Config   │
               │  (Tracking) │    │  (Field Mapping)│
               └─────────────┘    └─────────────────┘
```

### Data Flow

1. Timer trigger fires on cron schedule (every 2 days at 11 AM UTC)
2. REST API client sends POST request with search criteria and date range
3. Business rules filter projects by type using Excel-based configuration
4. Field transformer maps 36+ API fields to CRM-compatible format
5. Duplicate checker skips previously processed records using set-based O(1) lookup
6. Excel output generated via pandas in /tmp directory
7. Blob storage receives file for middleware consumption
8. SharePoint logs execution history and processed record IDs

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Runtime | Python 3.9+ |
| Cloud Platform | Microsoft Azure |
| Compute | Azure Functions (Timer Trigger) |
| Storage | Azure Blob Storage |
| File Management | SharePoint Online via Microsoft Graph API |
| Data Processing | pandas |
| Authentication | Azure Managed Identity, SAS tokens |
| Testing | pytest |

---

## Project Structure

```
├── function_app.py          # Main entry point and orchestration
├── config.py                # Environment configuration
├── dodge_api.py             # REST API client and data processing
├── sharepoint_helpers.py    # Microsoft Graph API integration
├── blob_helpers.py          # Azure Blob Storage operations
├── excel_helpers.py         # Configuration file processing
├── tracking.py              # Duplicate detection and run logging
├── data_helpers.py          # Data transformation utilities
├── country_codes.py         # Country code standardization (230+ entries)
├── test_helpers.py          # Unit tests
├── requirements.txt         # Python dependencies
└── host.json                # Azure Functions configuration
```

---

## Key Challenges & Solutions

### 1. Requirements Discovery

**Challenge:** Technical specifications were not available upfront. Data structures, API contracts, and CRM field requirements needed to be determined independently.

**Solution:** Reverse-engineered requirements through analysis of API sample responses, business conversations to understand lead qualification criteria, and iterative testing of endpoints. This approach enabled rapid development despite limited documentation.

### 2. Complex Nested JSON Structures

**Challenge:** API responses use nested ci/value structures and arrays with primary flags rather than flat field access. Documentation examples didn't always match actual response formats.

**Solution:** Built a `get_json_value()` utility for null-safe traversal with empty string defaults. Extraction logic navigates nested arrays and identifies primary values by flag, handling missing data gracefully.

### 3. Data Quality & Standardization

**Challenge:** Raw API data required significant transformation—inconsistent date formats, 9-digit zip codes, embedded newline characters, separate phone number components, and 230+ country name variations.

**Solution:** Created purpose-built helper functions:

- `format_date_to_iso()` — normalizes 6+ date formats to ISO standard
- `get_country_code()` — maps country names/variations to 2-letter codes
- `format_phone()` — assembles area code and number components
- `clean_text()` — sanitizes whitespace and special characters

### 4. Evolving Output Requirements

**Challenge:** Downstream system requirements changed during development—format changes, additional data cleaning, new destination endpoints.

**Solution:** Modular architecture with configurable Excel-based business rules. Format generation uses pandas for flexibility. Independent error handling at each integration point allows partial success when one destination fails.

---

## Features

- **Scheduled Execution** — Cron-based timer trigger (configurable schedule)
- **Duplicate Detection** — Set-based tracking with O(1) lookup, persisted to SharePoint
- **Configurable Filtering** — Excel-driven include/exclude rules editable by business users
- **Field Mapping** — Transforms 36+ API fields to CRM specification
- **Multi-destination Output** — Blob storage for middleware, SharePoint for audit trail
- **Error Resilience** — Independent error handling per integration point with logging

---

## Testing

Unit tests cover core helper functions using pytest.

### Running Tests

```bash
# Install pytest
pip install pytest

# Run all tests with verbose output
pytest test_helpers.py -v

# Run a specific test class
pytest test_helpers.py::TestGetCountryCode -v

# Run a specific test
pytest test_helpers.py::TestCleanText::test_removes_newlines -v
```

### Test Coverage

| Module | Functions Tested | Tests |
|--------|------------------|-------|
| `country_codes.py` | `get_country_code()` | 8 |
| `data_helpers.py` | `get_json_value()` | 5 |
| `data_helpers.py` | `format_phone()` | 5 |
| `data_helpers.py` | `format_date_to_iso()` | 3 |
| `data_helpers.py` | `clean_text()` | 7 |
| **Total** | | **28** |

---

## Setup

### Prerequisites

- Python 3.9+
- Azure subscription
- Azure Functions Core Tools
- API access credentials

### Environment Variables

Configure in Azure Function App settings or `local.settings.json`:

```
DODGE_API_KEY=your_api_key
BLOB_SAS_URL=your_blob_sas_url
SITE_ID=your_sharepoint_site_id
LEADS_DRIVE_ID=your_sharepoint_drive_id
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/tay-chi/azure-function-etl.git
cd azure-function-etl

# Create virtual environment
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables in local.settings.json

# Run locally
func start
```

### Deployment

```bash
func azure functionapp publish <your-function-app-name>
```

---

## Configuration

The pipeline uses an Excel configuration file stored in SharePoint:

| Purpose | Description |
|---------|-------------|
| Project Type Filtering | Include/exclude rules for relevant opportunities |
| Industry Code Mapping | Maps project types to CRM industry codes |
| Segment Code Mapping | Maps project types to market segment codes |

This design allows business users to modify filtering rules without code changes.

---

## Sample Output

The pipeline generates Excel files with CRM-ready data:

| Field | Description | Example |
|-------|-------------|---------|
| DRNumber | Unique project identifier | 202500123456 |
| Name | Project name | Memorial Hospital Expansion |
| Opportunity_Type | Project category | Hospital |
| Opportunity_City | Project location | Memphis |
| Opportunity_State | State code | TN |
| Main_Contact_First_Name | Owner contact | John |
| Main_Contact_Last_Name | Owner contact | Smith |
| Account_Name | Owner organization | Regional Health System |

*36+ fields total mapped to CRM import specification*

---

