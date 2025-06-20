import os
import tempfile
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient import errors as googleapiclient_errors
import functions_framework
import re
import google.auth
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('process-homebase-files')

# Constants
PROJECT_ID = "tys-bi"
DATASET_ID = "homebase"
SOURCE_FOLDER_ID = "1PDBU0dqzar49DEZXCAjeMeqEixVoaOnv"

def parse_datetime(date_str, time_str):
    """Parse date and time strings into a datetime object."""
    if not date_str or not time_str or pd.isna(date_str) or pd.isna(time_str):
        return None

    # Clean up the date and time strings
    date_str = date_str.strip()
    time_str = time_str.strip()

    try:
        # Parse the date in the format "Month Day Year" (e.g., "March 10 2025")
        date_obj = datetime.strptime(date_str, "%B %d %Y")

        # Parse the time in the format "h:mmam/pm" (e.g., "9:44am")
        time_obj = datetime.strptime(time_str, "%I:%M%p")

        # Combine date and time
        return datetime.combine(date_obj.date(), time_obj.time())
    except ValueError as e:
        logger.error(f"Error parsing date/time: {date_str} {time_str} - {e}")
        return None

def parse_wage(wage_str):
    """Parse wage string into a float."""
    if not wage_str or pd.isna(wage_str):
        return None

    # Remove $ and commas
    wage_str = wage_str.replace('$', '').replace(',', '')

    try:
        return float(wage_str)
    except ValueError:
        return None

def transform_homebase_csv(input_file_path):
    """Transform Homebase CSV into BigQuery-compatible format."""
    # Read the CSV file
    with open(input_file_path, 'r') as f:
        lines = f.readlines()

    # Find the actual data rows
    data_rows = []
    header_row = None  # Initialize header_row variable

    for i, line in enumerate(lines):
        if "Name,Clock in date,Clock in time" in line:
            header_row = i
            continue

        if header_row is not None and i > header_row:  # Check if header_row is not None
            # Stop if we hit a separator row
            if line.startswith('-,-,-,-'):
                continue

            # Skip empty rows
            if line.strip() == '""' or line.strip() == '':
                continue

            # Check if this is a totals row
            if "Totals for " in line:
                continue

            # Check if this is the final totals row
            if line.startswith('Totals,""'):
                continue

            # This should be a data row
            parts = line.strip().split(',')
            if len(parts) >= 5:  # Ensure we have enough columns
                data_rows.append(line)

    # Check if we found a header row
    if header_row is None:
        raise ValueError("Could not find header row in the CSV file")

    # Create a DataFrame from the data rows
    df = pd.read_csv(StringIO(''.join([lines[header_row]] + data_rows)))

    # Clean up column names
    df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]

    # Rename columns to match BigQuery schema
    if 'actual_vs._scheduled' in df.columns:
        df.rename(columns={'actual_vs._scheduled': 'actual_vs_scheduled'}, inplace=True)

    # Convert date and time columns to datetime
    df['clock_in_datetime'] = df.apply(lambda row: parse_datetime(row['clock_in_date'], row['clock_in_time']), axis=1)
    df['clock_out_datetime'] = df.apply(lambda row: parse_datetime(row['clock_out_date'], row['clock_out_time']), axis=1)
    df['break_start_datetime'] = df.apply(lambda row: parse_datetime(row['clock_in_date'], row['break_start']), axis=1)
    df['break_end_datetime'] = df.apply(lambda row: parse_datetime(row['clock_in_date'], row['break_end']), axis=1)

    # Keep raw strings for clock_in_date and clock_in_time
    df['clock_in_date_raw'] = df['clock_in_date']
    df['clock_in_time_raw'] = df['clock_in_time']
    df['clock_out_date_raw'] = df['clock_out_date']
    df['clock_out_time_raw'] = df['clock_out_time']
    df['break_start_raw'] = df['break_start']
    df['break_end_raw'] = df['break_end']

    # Parse wage rate
    df['wage_rate_numeric'] = df['wage_rate'].apply(parse_wage)

    # Convert numeric columns (only if they exist)
    numeric_cols = ['scheduled_hours', 'actual_vs_scheduled', 'total_paid_hours',
                    'regular_hours', 'unpaid_breaks', 'ot_hours']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Parse estimated wages, cash tips, credit tips (if they exist)
    if 'estimated_wages' in df.columns:
        df['estimated_wages_numeric'] = df['estimated_wages'].apply(parse_wage)
    else:
        df['estimated_wages_numeric'] = None

    if 'cash_tips' in df.columns:
        df['cash_tips_numeric'] = df['cash_tips'].apply(parse_wage)
    else:
        df['cash_tips_numeric'] = None

    if 'credit_tips' in df.columns:
        df['credit_tips_numeric'] = df['credit_tips'].apply(parse_wage)
    else:
        df['credit_tips_numeric'] = None
        logger.warning("'credit_tips' column not found in CSV. Setting credit_tips_numeric to None.")

    # Add a timestamp for when this data was processed
    df['processed_at'] = datetime.now()

    # Extract location and payroll period from the file
    location = os.path.basename(input_file_path).split('_')[0]
    payroll_period_start = lines[1].split(',')[1].split(' To ')[0].strip()
    payroll_period_end = lines[1].split(',')[1].split(' To ')[1].strip()

    df['location'] = location
    df['payroll_period_start'] = payroll_period_start
    df['payroll_period_end'] = payroll_period_end

    # Select and reorder columns for BigQuery
    columns_for_bq = [
        'location', 'payroll_period_start', 'payroll_period_end', 'name',
        'clock_in_datetime', 'clock_out_datetime', 'break_start_datetime', 'break_end_datetime',
        'break_length', 'break_type', 'payroll_id', 'role', 'wage_rate_numeric',
        'scheduled_hours', 'actual_vs_scheduled', 'total_paid_hours', 'regular_hours',
        'unpaid_breaks', 'ot_hours', 'estimated_wages_numeric', 'cash_tips_numeric',
        'credit_tips_numeric', 'no_show_reason', 'employee_note', 'manager_note',
        'processed_at', 'clock_in_date_raw', 'clock_in_time_raw', 'clock_out_date_raw',
        'clock_out_time_raw', 'break_start_raw', 'break_end_raw'
    ]

    # Make sure all required columns exist in the DataFrame
    # If they don't exist, add them with None values
    for col in columns_for_bq:
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in DataFrame. Adding with None values.")
            df[col] = None

    return df[columns_for_bq]

def get_drive_service():
    """Get authenticated Google Drive service."""
    # Use the default service account credentials
    try:
        credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/drive.file',
                   'https://www.googleapis.com/auth/drive']  # Added both scopes for better compatibility
        )
        if hasattr(credentials, 'service_account_email'):
            logger.info(f"Drive API using service account: {credentials.service_account_email}")
        else:
            logger.info(f"Drive API using user credentials for project: {project}")
    except Exception as e:
        logger.error(f"Error getting default credentials: {e}")
        # In production, credentials should be provided via environment variables or metadata service
        raise Exception("Unable to authenticate with Google Cloud. Please ensure proper credentials are configured.")

    return build('drive', 'v3', credentials=credentials)

def get_or_create_loaded_folder(drive_service):
    """Get the ID of the 'loaded' folder or create it if it doesn't exist."""
    # First try to find the folder
    query = "name='loaded' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])

    if folders:
        logger.info(f"Found 'loaded' folder with ID: {folders[0]['id']}")
        return folders[0]['id']

    # If folder doesn't exist, create it
    file_metadata = {
        'name': 'loaded',
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [SOURCE_FOLDER_ID]  # Create inside the source folder
    }

    try:
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        logger.info(f"Created 'loaded' folder with ID: {folder['id']}")
        return folder['id']
    except Exception as e:
        logger.error(f"Error creating 'loaded' folder: {e}")
        return None

def validate_date_range(start_date_str, end_date_str):
    """
    Validate that the date range:
    1. Represents exactly 14 days
    2. Starts on a Monday
    3. Ends on a Sunday

    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format

    Returns:
        (bool, str): (is_valid, error_message)
    """
    try:
        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Collect all validation errors
        errors = []

        # Check if start date is a Monday (weekday 0)
        if start_date.weekday() != 0:
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][start_date.weekday()]
            errors.append(f"Start date {start_date_str} is a {day_name}, not a Monday")

        # Check if end date is a Sunday (weekday 6)
        if end_date.weekday() != 6:
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][end_date.weekday()]
            errors.append(f"End date {end_date_str} is a {day_name}, not a Sunday")

        # Calculate the difference in days
        delta = (end_date - start_date).days + 1  # +1 because it's inclusive

        # Check if the range is exactly 14 days
        if delta != 14:
            errors.append(f"Date range is {delta} days, expected exactly 14 days")

        # Check if end date is after start date
        if end_date < start_date:
            errors.append(f"End date {end_date_str} is before start date {start_date_str}")

        # If we have any errors, return them all
        if errors:
            return False, "; ".join(errors)

        return True, ""
    except ValueError as e:
        return False, f"Error parsing dates: {e}"

def get_table_id_from_filename(file_name):
    """Extract table ID from filename and validate date range."""
    match = re.search(r'_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_', file_name)
    if not match:
        return None

    start_date = match.group(1)
    end_date = match.group(2)

    # Validate the date range
    is_valid, error_message = validate_date_range(start_date, end_date)
    if not is_valid:
        logger.error(f"Invalid date range in file {file_name}: {error_message}")
        raise ValueError(f"Please check date ranges: {error_message}")

    # Format for table ID
    start_date_formatted = start_date.replace('-', '')
    end_date_formatted = end_date.replace('-', '')
    return f"{PROJECT_ID}.{DATASET_ID}.timesheet_{start_date_formatted}_{end_date_formatted}_"

def check_if_file_processed(file_name, bq_client):
    """Check if the file has already been processed by looking for the table in BigQuery.
    If the table exists, drop it so we can reprocess the file."""
    table_id = get_table_id_from_filename(file_name)
    if not table_id:
        return False

    try:
        # Check if table exists (will raise exception if not)
        bq_client.get_table(table_id)
        logger.info(f"Table {table_id} exists. Dropping it for reprocessing.")
        bq_client.delete_table(table_id)
        logger.info(f"Table {table_id} dropped successfully.")
        return False  # Return False so the file will be processed
    except Exception as e:
        if "Not found" in str(e):
            logger.info(f"Table {table_id} does not exist. File has not been processed.")
            return False  # Table doesn't exist, file hasn't been processed
        else:
            logger.error(f"Error checking/dropping table {table_id}: {e}")
            return False  # Process the file anyway

def move_file_to_loaded_folder(file_id, drive_service, loaded_folder_id):
    """Move the file to the 'loaded' folder."""
    if not loaded_folder_id:
        logger.warning("Cannot move file: 'loaded' folder ID is missing")
        return

    try:
        # Get the file's current parents
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        current_parents = ",".join(file.get('parents', []))

        # Add the loaded folder as a parent
        drive_service.files().update(
            fileId=file_id,
            addParents=loaded_folder_id,
            removeParents=current_parents,  # Use actual parent IDs instead of hardcoded SOURCE_FOLDER_ID
            fields='id, parents'
        ).execute()
        logger.info(f"Successfully moved file {file_id} to folder {loaded_folder_id}")
    except googleapiclient_errors.HttpError as http_error:
        logger.error(f"HTTP Error moving file {file_id} to 'loaded' folder: {http_error}")
        logger.error(f"Details: {http_error.content}")
        # If we can't move the file, at least try to copy it to the loaded folder
        try:
            logger.info(f"Attempting to copy file {file_id} to loaded folder instead")
            # Use the copy method instead
            drive_service.files().copy(
                fileId=file_id,
                body={'parents': [loaded_folder_id]}
            ).execute()  # We don't need to store the result
            logger.info(f"Successfully copied file {file_id} to folder {loaded_folder_id}")
        except Exception as copy_error:
            logger.error(f"Error copying file {file_id} to 'loaded' folder: {copy_error}")
    except Exception as e:
        logger.error(f"Error moving file {file_id} to 'loaded' folder: {e}")

@functions_framework.http
def process_homebase_files(request):
    """Cloud Function to process Homebase timesheet files from Google Drive."""
    # Check if this is a test request
    request_json = request.get_json(silent=True)
    if request_json and request_json.get('test'):
        # This is a test request
        test_filename = request_json.get('filename', 'Restore Round Rock_2023-05-01_2023-05-14_timesheets.csv')
        logger.info(f"Running in test mode with filename: {test_filename}")

        try:
            table_id = get_table_id_from_filename(test_filename)
            return f"Test successful! Validated filename: {test_filename}, Table ID: {table_id}"
        except ValueError as e:
            return f"Test validation failed: {str(e)}"

    # Initialize clients
    drive_service = get_drive_service()
    bq_client = bigquery.Client(project=PROJECT_ID)

    # Get or create the 'loaded' folder
    loaded_folder_id = get_or_create_loaded_folder(drive_service)

    # Create dataset if it doesn't exist
    try:
        bq_client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
    except Exception:
        dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
        dataset.location = "US"
        bq_client.create_dataset(dataset, exists_ok=True)

    # List files in the source folder
    results = drive_service.files().list(
        q=f"'{SOURCE_FOLDER_ID}' in parents and mimeType='text/csv' and name contains 'timesheets'",
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])

    if not files:
        return "No files found to process."

    processed_files = []
    validation_errors = []

    for file in files:
        file_id = file['id']
        file_name = file['name']

        # Check if file has already been processed
        # Note: check_if_file_processed now drops the table if it exists
        check_if_file_processed(file_name, bq_client)

        # Validate the filename first before downloading
        try:
            table_id = get_table_id_from_filename(file_name)
            if not table_id:
                error_msg = f"Could not extract date range from filename: {file_name}"
                logger.error(error_msg)
                validation_errors.append(error_msg)
                continue
        except ValueError as date_error:
            # This will catch the date validation errors from get_table_id_from_filename
            error_msg = f"Invalid file {file_name}: {str(date_error)}"
            logger.error(error_msg)
            validation_errors.append(error_msg)
            # Move the file to the loaded folder anyway to prevent reprocessing attempts
            move_file_to_loaded_folder(file_id, drive_service, loaded_folder_id)
            continue

        # Download the file
        request = drive_service.files().get_media(fileId=file_id)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            downloader = MediaIoBaseDownload(temp_file, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()  # We don't need the status

            temp_file_path = temp_file.name

        try:
            # Transform the CSV
            df = transform_homebase_csv(temp_file_path)

            # Load data into BigQuery
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                schema=[
                    bigquery.SchemaField("location", "STRING"),
                    bigquery.SchemaField("payroll_period_start", "STRING"),
                    bigquery.SchemaField("payroll_period_end", "STRING"),
                    bigquery.SchemaField("name", "STRING"),
                    bigquery.SchemaField("clock_in_datetime", "TIMESTAMP"),
                    bigquery.SchemaField("clock_out_datetime", "TIMESTAMP"),
                    bigquery.SchemaField("break_start_datetime", "TIMESTAMP"),
                    bigquery.SchemaField("break_end_datetime", "TIMESTAMP"),
                    bigquery.SchemaField("break_length", "STRING"),
                    bigquery.SchemaField("break_type", "STRING"),
                    bigquery.SchemaField("payroll_id", "STRING"),
                    bigquery.SchemaField("role", "STRING"),
                    bigquery.SchemaField("wage_rate_numeric", "FLOAT"),
                    bigquery.SchemaField("scheduled_hours", "FLOAT"),
                    bigquery.SchemaField("actual_vs_scheduled", "FLOAT"),
                    bigquery.SchemaField("total_paid_hours", "FLOAT"),
                    bigquery.SchemaField("regular_hours", "FLOAT"),
                    bigquery.SchemaField("unpaid_breaks", "FLOAT"),
                    bigquery.SchemaField("ot_hours", "FLOAT"),
                    bigquery.SchemaField("estimated_wages_numeric", "FLOAT"),
                    bigquery.SchemaField("cash_tips_numeric", "FLOAT"),
                    bigquery.SchemaField("credit_tips_numeric", "FLOAT"),
                    bigquery.SchemaField("no_show_reason", "STRING"),
                    bigquery.SchemaField("employee_note", "STRING"),
                    bigquery.SchemaField("manager_note", "STRING"),
                    bigquery.SchemaField("processed_at", "TIMESTAMP"),
                    bigquery.SchemaField("clock_in_date_raw", "STRING"),
                    bigquery.SchemaField("clock_in_time_raw", "STRING"),
                    bigquery.SchemaField("clock_out_date_raw", "STRING"),
                    bigquery.SchemaField("clock_out_time_raw", "STRING"),
                    bigquery.SchemaField("break_start_raw", "STRING"),
                    bigquery.SchemaField("break_end_raw", "STRING")
                ]
            )

            job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
            job.result()  # Wait for the job to complete

            # Run SQL query to update materialized view after loading the data
            sql_query = """
            CREATE OR REPLACE TABLE `tys-bi.homebase.timesheets_mv` AS
            SELECT * FROM `tys-bi.homebase.timesheets_v`
            """
            try:
                query_job = bq_client.query(sql_query)
                query_job.result()  # Wait for the query to complete
                logger.info("Successfully updated materialized view table.")
            except Exception as e:
                logger.error(f"Error updating materialized view: {e}")

            # Move file to 'loaded' folder
            move_file_to_loaded_folder(file_id, drive_service, loaded_folder_id)

            processed_files.append(file_name)

        except Exception as e:
            error_msg = f"Error processing file {file_name}: {str(e)}"
            logger.error(error_msg)
            validation_errors.append(error_msg)
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # Prepare the response
    response_parts = []

    if processed_files:
        response_parts.append(f"Successfully processed {len(processed_files)} files: {', '.join(processed_files)}")

    if validation_errors:
        response_parts.append(f"Validation errors found in {len(validation_errors)} files:")
        for error in validation_errors:
            response_parts.append(f"  - {error}")

    if not processed_files and not validation_errors:
        return "No new files to process."

    return "\n".join(response_parts)