
import requests
import sys
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import pandas_gbq
from google.cloud import bigquery
from datetime import datetime
from selenium.webdriver.chrome.options import Options




bq_pow_mapping_table_id = 'tys-bi.referrizer.pow_mapping'
bq_pow_mapping_staging_table_id = 'tys-bi.referrizer.pow_mapping_staging' 


def login_to_referrizer(driver):
    ip_address = requests.get('https://www.curlmyip.org').text.replace('\n','')
    print(f"My IP address is {ip_address}")
    driver.get("https://app.referrizer.com")

    # Wait for and fill login form
    try:
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username.send_keys("roundrock@restore.com")

        password = driver.find_element(By.ID, "password")
        password.send_keys("6629")
        
        # Submit login form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
    except Exception as e:
        print(f"Error: {e}")
        print(f"Page Source: {driver.page_source}")
        sys.exit("There was an issue with logging in")

    # Wait for login to complete
    time.sleep(2)

    # Check if verification code element exists
    try:
        verification_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='verification-code']"))
        )
        print('Waiting for 100 seconds for verification code')
        time.sleep(100)

        # If element exists, query BigQuery for verification code
        bigquery_credentials = 'tys-bi.json'
        bigquery_client = bigquery.Client.from_service_account_json(bigquery_credentials)
        query = """ SELECT code FROM `tys-bi.referrizer.verification_code` """

        # Execute query and get verification code
        results = bigquery_client.query(query).result()
        verification_code = None
        for row in results:
            verification_code = row.code
            break

        if verification_code:
            # Enter verification code
            verification_element.send_keys(verification_code)

            # Find and click submit button for verification code
            verify_button = driver.find_element(By.XPATH, "//button[contains(@class, 'submit') or contains(@type, 'submit')]")
            verify_button.click()
            print(f"Verification code {verification_code} submitted")
        else:
            print("No verification code found in BigQuery")

    except Exception as e:
        # No verification code element found, continue with normal flow
        print("No verification code element found, continuing with login")
        print(e)
        pass


def get_contact_ids():
    bigquery_credentials = 'tys-bi.json'

    bigquery_client = bigquery.Client.from_service_account_json(bigquery_credentials)

    # Looking up by ids from the ret_clients table?

    query = f"""
    SELECT DISTINCT id, lastVisitDate
    FROM `tys-bi.referrizer.ret_clients` r
    left join `{bq_pow_mapping_table_id}` m on m.contact_id = r.id
    WHERE partition_date = date_add(CURRENT_DATE('America/Chicago'), interval -1 day)
    and (m.contact_id is null or m.pow_id is null)
    ORDER BY lastVisitDate desc
    LIMIT 500
    """
    return bigquery_client.query(query).to_dataframe()

def upload_to_gbq(df):
    pandas_gbq.to_gbq(
        df,
        destination_table=bq_pow_mapping_staging_table_id,
        project_id='tys-bi',
        if_exists='replace'
    )
    print("Data successfully uploaded to BigQuery")

def merge_pow_mapping():
    client = bigquery.Client()
    merge_query = f"""
    MERGE `{bq_pow_mapping_table_id}` T
    USING `{bq_pow_mapping_staging_table_id}` S
    ON T.contact_id = S.contact_id
    WHEN MATCHED THEN
      UPDATE SET pow_id = cast(nullif(S.pow_id, '-') as int64),
                 last_time_account_dir_comm = parse_date('%m/%d/%Y', nullif(S.last_time_account_dir_comm, '-')),
                 last_time_contact_dir_comm = parse_date('%m/%d/%Y', nullif(S.last_time_contact_dir_comm, '-'))
                 
    WHEN NOT MATCHED THEN
      INSERT (contact_id, pow_id, last_time_account_dir_comm, last_time_contact_dir_comm)
      VALUES (contact_id, 
              cast(nullif(pow_id, '-') as int64), 
              parse_date('%m/%d/%Y', nullif(S.last_time_account_dir_comm, '-')),
              parse_date('%m/%d/%Y', nullif(S.last_time_contact_dir_comm, '-'))
              )
    """
    query_job = client.query(merge_query)
    query_job.result()  # Wait for the query to complete
    print("Merge completed successfully")


def click_view_more_button(driver):
    try:
        view_more_button = WebDriverWait(driver,10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-qa="contact-basic-info-customer-fields-view-more-button"]'))
        )
        view_more_button.click()
        #time.sleep(0.5)  # Short wait to allow UI to respond
        return True
    except Exception as e:
        print(f"Error clicking view more button: {e}")
        return False


def get_contact_details(driver, contact_id):
    url = f"https://app.referrizer.com/contacts/{contact_id}/details"
    driver.get(url)

    fields_to_scrape = ['pow_id', 'last_time_account_dir_comm', 'last_time_contact_dir_comm']
    # Initialize pow_id with a default value
    scraped_elements = {}
    for field in fields_to_scrape:
        scraped_elements[field] = '-'
    scrape_info = {}

     # Zoom out to 67%
    driver.execute_script("document.body.style.zoom='67%'")

    # Click the view more button to expand additional fields
    click_view_more_button(driver)
    # Function already handles exceptions internally
    
    # populate field data to be scraped
    scrape_info['pow_id'] = '[data-qa="contact-basic-info-integration-pow-id"]'
    scrape_info['last_time_account_dir_comm'] = '[data-qa="contact-basic-info-customer-fields-contact-last-contacted-date"]'
    scrape_info['last_time_contact_dir_comm'] = '[data-qa="contact-basic-info-customer-fields-contact-last-responded-date"]'
    
  
    # Wait for the element to be present
    for field in fields_to_scrape:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, scrape_info[field])))
            #element = driver.find_element(By.CSS_SELECTOR, scrape_info[field])
            scraped_elements[field] = element.text.strip()
        
        except Exception as e:
            print(f"Error finding {field} element: {e}")
        # Keep the default pow_id value
    # Try up to 3 more times to get the POW ID if it's empty


    # for field in fields_to_scrape:

    #     attempts = 0
    #     max_attempts = 3
        
    #     element_value = scraped_elements[field]

    #     while (element_value == '' or element_value == '-') and attempts < max_attempts:
    #         print(f"Retry attempt {attempts+1} for contact {contact_id} and element {field}")

    #         # Try clicking the view more button again
    #         if click_view_more_button(driver):
    #             try:
    #                 # Wait a bit longer on retries
    #                 time.sleep(1.5)

    #                 # Try to find the POW ID element
    #                 element = driver.find_element(By.CSS_SELECTOR, scrape_info[field])
    #                 new_element_value = element.text.strip()

    #                 if new_element_value:  # Only update if we got a non-empty value
    #                     scraped_elements[field] = new_element_value
    #                     print(f"Found {field} on retry: {new_element_value}")
    #                     break  # Exit the loop if we found a valid element id
    #             except Exception as e:
    #                 print(f"Error finding {field} in retry attempt {attempts+1}: {e}")
    #                 # Keep existing element_id value

    #         attempts += 1


    # Create dataframe with both IDs
    df = pd.DataFrame({
        'contact_id': [contact_id],
        'pow_id': [scraped_elements['pow_id']],
        'last_time_account_dir_comm' : [scraped_elements['last_time_account_dir_comm']],
        'last_time_contact_dir_comm' : [scraped_elements['last_time_contact_dir_comm']]
    })
    
    print([contact_id,
           scraped_elements['pow_id'],
           scraped_elements['last_time_account_dir_comm'],
           scraped_elements['last_time_contact_dir_comm']])
    return df

def main(request=None):
    """
    Cloud Run function that scrapes Referrizer data.
    Can be called directly or as a Cloud Run function.

    Args:
        request (flask.Request, optional): The request object when called as Cloud Run function.
            Defaults to None when called directly.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.
    """
    # Configure Chrome options for both local and Cloud Run environments
    chrome_options = webdriver.ChromeOptions()

    # Detect if running in Cloud Run or similar environment
    import os
    is_cloud_environment = os.environ.get('CLOUD_RUN_JOB', False) or os.environ.get('K_SERVICE', False)

    # Always use these options for stability
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--log-level=3')  # Suppress console messages

    # Use headless mode in cloud environments or when specified
    if is_cloud_environment or os.environ.get('USE_HEADLESS', False):
        print("Running in headless mode")
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--window-size=1920,1080')

    # Set temporary user data directory
    # chrome_options.add_argument('--user-data-dir=/tmp/chrome-data')

    # Add debugging port in development environments
    if not is_cloud_environment:
        chrome_options.add_argument('--remote-debugging-port=9222')

    # Initialize Chrome driver
    from selenium.webdriver.chrome.service import Service
    import os
    import platform
    import subprocess

    try:
        # Determine if we're in a GCP environment
        is_gcp = os.environ.get('CLOUD_RUN_JOB', False) or os.environ.get('K_SERVICE', False)

        if is_gcp:
            # In GCP Cloud Run, Chrome is installed in a standard location
            print("Running in GCP environment, using bundled Chrome")

            # For Cloud Run, we need to use the Chrome binary that's installed in the container
            chrome_options.binary_location = "/usr/bin/google-chrome"

            service = Service("/usr/local/bin/chromedriver")
        else:
            # For local development, try multiple approaches
            print("Running in local environment")

            # First try: Use webdriver-manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                print("Using webdriver-manager to get the correct ChromeDriver version")
                service = Service(ChromeDriverManager().install())
            except Exception as wdm_error:
                print(f"Webdriver-manager failed: {wdm_error}")

                # Second try: Use local chromedriver if it exists
                chromedriver_path = "./chromedriver"
                if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
                    print(f"Using local chromedriver at: {chromedriver_path}")
                    service = Service(executable_path=chromedriver_path)
                else:
                    # Third try: Try to find chromedriver in PATH
                    try:
                        if platform.system() == "Windows":
                            chromedriver_path = subprocess.check_output(["where", "chromedriver"]).decode().strip()
                        else:
                            chromedriver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
                        print(f"Using chromedriver from PATH: {chromedriver_path}")
                        service = Service(executable_path=chromedriver_path)
                    except Exception as path_error:
                        print(f"Could not find chromedriver in PATH: {path_error}")
                        # Last resort: Use default Service and hope Chrome is properly installed
                        print("Using default Service configuration")
                        service = Service()

        # Initialize the driver with the service and options
        print("Initializing Chrome driver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Chrome driver initialized successfully")

    except Exception as e:
        print(f"Chrome initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    starttime = datetime.now()
    print(f"Starting job at: {starttime}")

    try:
        # Login to Referrizer
        login_to_referrizer(driver)
        
        # Get contact IDs to process
        contact_ids_df = get_contact_ids()

        print(f"Total contacts to process: {len(contact_ids_df)}")

        results = []
        total_records = 0

        # Process each contact ID
        for index, contact_id in enumerate(contact_ids_df['id'], 1):
            try:
                contact_data = get_contact_details(driver, contact_id)
                results.append(contact_data)

                # Process batch when reaching 200 records
                if index % 200 == 0:
                    print(f"Processing batch {index} of {len(contact_ids_df)}")
                    batch_df = pd.concat(results, ignore_index=True)
                    upload_to_gbq(batch_df)
                    merge_pow_mapping()
                    total_records += len(batch_df)
                    print(f"Uploaded {len(batch_df)} records. Total records processed: {total_records}")
                    results = []  # Reset for next batch

            except Exception as e:
                print(f"Error processing contact {contact_id}: {e}")
                continue

        # Process remaining records
        if results:
            final_batch = pd.DataFrame()
            final_batch = pd.concat(results, ignore_index=True)
            upload_to_gbq(final_batch)
            merge_pow_mapping()
            total_records += len(final_batch)
            print(f"Final batch uploaded: {len(final_batch)} records")
            print(f"Total records processed: {total_records}")

        endtime = datetime.now()
        print(f"Ending job at: {endtime}")
        print(f"Total runtime: {endtime - starttime}")

        return f"Processed {total_records} records successfully"

    except Exception as e:
        print(f"Error in main function: {e}")
        return f"Error: {str(e)}", 500
    finally:
        # Always close the driver
        driver.quit()
    
    return 'success'

if __name__ == "__main__":
    main(1)
