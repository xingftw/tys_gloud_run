# Comprehensive Summary of Extracted Cloud Run Functions

## Overview

This document provides a summary of all the Cloud Run functions that have been extracted from Google Cloud. The extraction was performed using a custom script that pulls the code from the container images used by the Cloud Run services.

## Functions Summary

| Function Name | Main Purpose | Dependencies | Key Features |
|---------------|--------------|--------------|--------------|
| backup-appointments | Backs up appointment data from a source to BigQuery | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Uses multiprocessing to process dates in parallel |
| backup-from-streaming | Extracts data from Referrizer API and loads to BigQuery | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Paginates through API results and loads to BigQuery |
| backup-metrics | Backs up metrics data from Restore BI to TYS BI | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Extracts gross sales metrics from one BigQuery project to another |
| backup-ua | Backs up user activity data from Restore BI to TYS BI | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Extracts multiple tables from Restore BI to TYS BI with complex SQL queries |
| process-homebase-files | Processes Homebase timesheet CSV files from Google Drive and loads to BigQuery | functions-framework, pandas, google-cloud-bigquery, google-api-python-client | Downloads files from Google Drive, transforms CSV data, loads to BigQuery, and moves processed files to a 'loaded' folder |
| redirect1 | Redirects HTTP requests to a specific URL | functions-framework | Simple redirect function |
| referizer-extract | Extracts data from Referrizer API | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Extracts client data from Referrizer API |
| restore-redirect | Redirects HTTP requests to a specific URL | functions-framework | Simple redirect function |
| restore-redirect-usps | Redirects HTTP requests to a specific URL | functions-framework | Simple redirect function |
| scrape-appointments | Scrapes appointment data from POW system | functions-framework, pandas, google-cloud-bigquery, pandas-gbq | Uses multiprocessing to scrape appointment data for multiple dates |

## Detailed Analysis

### Data Backup Functions

Several functions are dedicated to backing up data from various sources to BigQuery:

1. **backup-appointments**: Extracts appointment data from a source system and loads it into BigQuery. Uses multiprocessing to process multiple dates in parallel.

2. **backup-from-streaming**: Extracts data from the Referrizer API and loads it into BigQuery. Paginates through API results to get all data.

3. **backup-metrics**: Extracts metrics data from Restore BI and loads it into TYS BI. Focuses on gross sales metrics.

4. **backup-ua**: Extracts user activity data from Restore BI and loads it into TYS BI. Handles multiple tables and complex SQL queries.

### Data Processing Functions

Functions dedicated to processing and transforming data:

1. **process-homebase-files**: Processes Homebase timesheet CSV files from Google Drive. This function:
   - Monitors a specific Google Drive folder for new CSV files
   - Downloads and parses the CSV files containing timesheet data
   - Transforms the data into a BigQuery-compatible format
   - Loads the data into BigQuery tables
   - Updates a materialized view for reporting
   - Moves processed files to a 'loaded' folder to prevent reprocessing

### Redirect Functions

Several simple functions are used to redirect HTTP requests to specific URLs:

1. **redirect1**: Redirects to https://www.restore.com/locations/tx-round-rock-tx002
2. **restore-redirect**: Redirects to https://www.restore.com/locations/tx-round-rock-tx002
3. **restore-redirect-usps**: Redirects to https://www.restore.com/locations/tx-round-rock-tx002

### Data Extraction Functions

Functions dedicated to extracting data from external systems:

1. **referizer-extract**: Extracts client data from the Referrizer API and loads it into BigQuery.
2. **scrape-appointments**: Scrapes appointment data from the POW system and loads it into BigQuery.

## Common Patterns

1. **BigQuery Integration**: Most functions interact with BigQuery for data storage and retrieval.
2. **API Integration**: Several functions interact with external APIs to extract data.
3. **Pandas Usage**: Most data processing functions use pandas for data manipulation.
4. **Service Account Authentication**: Functions use service account credentials to authenticate with Google Cloud services.
5. **Error Handling**: Most functions include basic error handling to ensure robustness.

## Security Considerations

1. **Service Account Credentials**: Several functions include hardcoded service account credentials, which is a security risk. These should be stored in Secret Manager or environment variables.
2. **API Keys**: Some functions may include API keys or tokens, which should also be stored securely.

## Recommendations

1. **Refactor for Security**: Remove hardcoded credentials and use Secret Manager or environment variables.
2. **Code Reuse**: Consider creating a shared library for common functionality like BigQuery interactions.
3. **Error Handling**: Improve error handling to make functions more robust.
4. **Logging**: Add more comprehensive logging for better monitoring and debugging.
5. **Testing**: Add unit tests to ensure functions work as expected.

## Conclusion

The extracted Cloud Run functions provide valuable insights into the data processing and integration patterns used in the organization. By analyzing these functions, we can identify opportunities for improvement and standardization.
