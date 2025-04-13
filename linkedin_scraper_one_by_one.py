#!/usr/bin/env python3
"""
LinkedIn Job Scraper - One-by-One Version
1. Retrieves job IDs one by one, avoiding issues that may occur with batch processing
2. Uses the start parameter to precisely control each job item retrieval
3. Collects all available job IDs
4. Automatically handles loading issues
"""

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import random
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_scraper_one_by_one.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_driver(headless=False):
    """Set up and return a configured Chrome WebDriver
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Add headless mode if requested
    if headless:
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--window-size=1920,1080")
        logger.info("Running Chrome in headless mode")
    
    # Add anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Add a realistic user agent
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute CDP commands to prevent detection
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": driver.execute_script("return navigator.userAgent")
    })
    
    # Execute script to modify navigator properties
    driver.execute_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """)
    
    # Only maximize if not in headless mode
    if not headless:
        driver.maximize_window()
    
    logger.info("WebDriver setup complete")
    return driver

def manual_login(driver):
    """Manually login to LinkedIn with automatic timeout"""
    driver.get("https://www.linkedin.com/login")
    logger.info("Please login to LinkedIn manually in the browser")
    
    # Check if we're running in interactive mode (terminal)
    import sys
    if sys.stdin.isatty():
        # In terminal mode, prompt for manual login
        print("\n" + "="*50)
        print("Please login to LinkedIn in the browser window")
        print("You have 120 seconds to complete the login")
        print("="*50 + "\n")
        
        # Wait for login with timeout
        max_wait = 120  # 2 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if login was successful
            if "linkedin.com" in driver.current_url and "login" not in driver.current_url:
                logger.info("Login detected")
                break
                
            # Check if we're on a security verification page
            if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
                logger.info("Security verification detected")
                # Give more time for verification
                time.sleep(5)
                continue
                
            # Wait a bit before checking again
            time.sleep(2)
            
        # After timeout or successful login
        if time.time() - start_time >= max_wait:
            logger.warning("Login timeout reached, continuing anyway")
    else:
        # If running in non-interactive mode (web UI), wait a reasonable time
        logger.info("Running in non-interactive mode. Waiting 120 seconds for login...")
        time.sleep(120)  # Increased wait time for manual login
    
    # Check if login was successful - more comprehensive check
    if "linkedin.com" in driver.current_url and "login" not in driver.current_url:
        logger.info("Login successful")
        return True
    else:
        # Check if we're on a security verification page
        if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
            logger.info("LinkedIn security verification detected. Waiting for verification to complete...")
            # Wait longer for security verification
            time.sleep(60)  # Wait up to 60 seconds for verification to be completed
            return True
            
        logger.warning(f"Login may have failed. Current URL: {driver.current_url}")
        # We'll try to continue anyway, as sometimes LinkedIn redirects to unexpected URLs
        return True

def collect_job_ids_one_by_one(driver, search_url, max_jobs=float('inf'), start=0):
    """Collect job IDs one by one, avoiding issues that may occur with batch processing
    
    Args:
        driver: WebDriver instance
        search_url: Search URL
        max_jobs: Maximum number of jobs to collect, default is unlimited (collect all available jobs)
        start: Position to start collecting from
    """
    job_ids = []
    collected_ids = set()  # For checking duplicate IDs
    start_position = start  # Start from the specified position
    max_attempts = 200  # Maximum number of attempts, can be adjusted based on expected job count
    consecutive_failures = 0  # Count of consecutive failures
    max_consecutive_failures = 5  # Maximum consecutive failures before assuming we've reached the end
    
    logger.info(f"Starting to collect job IDs one by one, max collection: {max_jobs if max_jobs != float('inf') else 'unlimited'}")
    
    while len(job_ids) < max_jobs and start_position < max_attempts and consecutive_failures < max_consecutive_failures:
        try:
            # Build URL with start parameter
            # Remove any existing start parameter from URL
            base_url = re.sub(r'&start=\d+', '', search_url)
            current_url = f"{base_url}&start={start_position}"
            logger.info(f"Processing job item #{start_position+1}, URL: {current_url}")
            
            # Navigate to current URL
            driver.get(current_url)
            time.sleep(3)  # Wait for page to load
            
            # Try different selectors to find job listings
            selectors = [
                ".jobs-search-results__list-item",
                ".job-card-container",
                ".jobs-search-results-list__list-item",
                ".jobs-search-two-pane__job-card-container",
                "li.jobs-search-results__list-item",
                ".artdeco-list__item"
            ]
            
            # Try to find the first job card
            job_card = None
            for selector in selectors:
                try:
                    # Wait for element to appear
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    job_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if job_cards:
                        job_card = job_cards[0]  # Only get the first job card
                        logger.info(f"Found first job card using selector {selector}")
                        break
                except:
                    continue
            
            if not job_card:
                logger.warning(f"No job card found at start={start_position}")
                consecutive_failures += 1
                logger.info(f"Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                start_position += 1
                continue
            
            # Click on job card
            logger.info("Attempting to click job card")
            try:
                driver.execute_script("arguments[0].click();", job_card)
                logger.info("JavaScript click successful")
            except:
                try:
                    job_card.click()
                    logger.info("Regular click successful")
                except:
                    logger.error("Click failed")
                    consecutive_failures += 1
                    start_position += 1
                    continue
            
            # Wait for page update
            time.sleep(3)
            
            # Get current URL, which should contain currentJobId
            current_url = driver.current_url
            logger.info(f"Current URL after click: {current_url}")
            
            # Extract currentJobId from URL
            job_id = None
            job_id_match = re.search(r'currentJobId=(\d+)', current_url)
            if job_id_match:
                job_id = job_id_match.group(1)
                logger.info(f"Extracted job ID: {job_id}")
            else:
                # Try to extract from jobs/view/ format
                job_id_match = re.search(r'jobs/view/(\d+)', current_url)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    logger.info(f"Extracted job ID from jobs/view/ format: {job_id}")
                else:
                    logger.warning(f"Could not extract job ID from URL: {current_url}")
                    consecutive_failures += 1
                    start_position += 1
                    continue
            
            # Check if this is a new job ID
            if job_id and job_id not in collected_ids:
                collected_ids.add(job_id)
                job_ids.append(job_id)
                consecutive_failures = 0  # Reset consecutive failures counter
                logger.info(f"Collected new job ID: {job_id} (total: {len(job_ids)})")
                
                # Save to file every 10 job IDs
                if len(job_ids) % 10 == 0:
                    with open("job_ids_one_by_one.txt", "w") as f:
                        for id in job_ids:
                            f.write(f"{id}\n")
                    logger.info(f"Saved {len(job_ids)} job IDs to job_ids_one_by_one.txt")
            else:
                if job_id in collected_ids:
                    logger.warning(f"Detected duplicate job ID: {job_id}")
                consecutive_failures += 1
            
            # Add random delay to avoid detection
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.error(f"Error processing job item: {e}")
            consecutive_failures += 1
        
        # Increment start value regardless of success or failure, move to next job item
        start_position += 1
        logger.info(f"Moving to next job item, start = {start_position}")
    
    # Save final job IDs to file
    with open("job_ids_one_by_one.txt", "w") as f:
        for job_id in job_ids:
            f.write(f"{job_id}\n")
    logger.info(f"Saved {len(job_ids)} job IDs to job_ids_one_by_one.txt")
    
    return job_ids

def get_job_details(driver, job_ids):
    """Get job details"""
    job_details = []
    
    for i, job_id in enumerate(job_ids):
        try:
            logger.info(f"Processing job {i+1}/{len(job_ids)} (ID: {job_id})")
            
            # Build job URL
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            logger.info(f"Navigating to job URL: {job_url}")
            
            # Navigate to job page
            driver.get(job_url)
            time.sleep(5)  # Wait for page to load
            
            # Extract job title
            job_title = "Unknown Title"
            for title_selector in [".jobs-unified-top-card__job-title", ".job-details-jobs-unified-top-card__job-title", "h1", ".topcard__title"]:
                try:
                    job_title = driver.find_element(By.CSS_SELECTOR, title_selector).text.strip()
                    logger.info(f"Job title: {job_title}")
                    break
                except:
                    continue
            
            # Extract company name
            company = "Unknown Company"
            for company_selector in [".jobs-unified-top-card__company-name", ".job-details-jobs-unified-top-card__company-name", ".topcard__org-name-link"]:
                try:
                    company = driver.find_element(By.CSS_SELECTOR, company_selector).text.strip()
                    logger.info(f"Company name: {company}")
                    break
                except:
                    continue
            
            # Extract job location - improved with multiple selectors and approaches
            location = "Unknown Location"
            
            # Try multiple location selectors with more comprehensive approach
            location_selectors = [
                ".jobs-unified-top-card__bullet", 
                ".job-details-jobs-unified-top-card__bullet", 
                ".topcard__flavor--bullet",
                ".jobs-unified-top-card__workplace-type",
                ".jobs-unified-top-card__subtitle-primary [class*='location']",
                ".jobs-unified-top-card__company-name + span",
                ".job-details-jobs-unified-top-card__primary-description-container .job-details-jobs-unified-top-card__primary-description-without-tagline",
                ".job-details-jobs-unified-top-card__company-name + .job-details-jobs-unified-top-card__primary-description-container span",
                ".jobs-unified-top-card__subtitle-primary",
                ".jobs-unified-top-card__metadata",
                ".job-details-jobs-unified-top-card__subtitle",
                ".job-details-jobs-unified-top-card__primary-description"
            ]
            
            # First try specific location selectors
            for location_selector in location_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, location_selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and text != company and "ago" not in text.lower() and not text.isdigit():
                            # Check if this looks like a location (not a job type like "Full-time")
                            if not any(job_type in text.lower() for job_type in ["full-time", "part-time", "contract", "temporary", "internship", "remote"]):
                                location = text
                                logger.info(f"Job location found: {location}")
                                break
                    if location != "Unknown Location":
                        break
                except Exception as e:
                    logger.debug(f"Error with location selector {location_selector}: {e}")
                    continue
            
            # If still unknown, try to get all metadata text and parse it
            if location == "Unknown Location":
                try:
                    # Get all metadata elements
                    metadata_elements = driver.find_elements(By.CSS_SELECTOR, ".jobs-unified-top-card__subtitle-primary span, .jobs-unified-top-card__metadata span, .job-details-jobs-unified-top-card__subtitle span")
                    
                    # Look for location patterns in the metadata
                    for element in metadata_elements:
                        text = element.text.strip()
                        # Skip empty, company name, or time-related text
                        if not text or text == company or "ago" in text.lower() or text.isdigit():
                            continue
                            
                        # Check if this looks like a location
                        if "," in text or any(city in text.lower() for city in ["new york", "san francisco", "london", "tokyo", "beijing", "shanghai", "remote"]):
                            location = text
                            logger.info(f"Job location found in metadata: {location}")
                            break
                except Exception as e:
                    logger.debug(f"Error extracting location from metadata: {e}")
            
            # If still unknown, try to find location in the URL or page title
            if location == "Unknown Location":
                try:
                    page_title = driver.title
                    url_text = driver.current_url
                    
                    # Common location patterns in titles like "Job Title at Company in Location"
                    title_location_match = re.search(r'(?:in|at) ([A-Za-z\s,]+)(?:\s*[-|]\s*LinkedIn|$)', page_title)
                    if title_location_match:
                        potential_location = title_location_match.group(1).strip()
                        if potential_location and potential_location != company:
                            location = potential_location
                            logger.info(f"Job location extracted from title: {location}")
                except Exception as e:
                    logger.debug(f"Error extracting location from title/URL: {e}")
            
            # Try one more approach - look for location in the full page HTML
            if location == "Unknown Location":
                try:
                    # Get the page source
                    page_source = driver.page_source.lower()
                    
                    # Look for common location patterns
                    location_patterns = [
                        r'location"?:\s*"([^"]+)"',
                        r'location"?>\s*([^<]+)<',
                        r'address"?>\s*([^<]+)<',
                        r'locality"?>\s*([^<]+)<'
                    ]
                    
                    for pattern in location_patterns:
                        match = re.search(pattern, page_source)
                        if match:
                            potential_location = match.group(1).strip()
                            if potential_location and len(potential_location) < 100:  # Sanity check
                                location = potential_location
                                logger.info(f"Job location extracted from HTML: {location}")
                                break
                except Exception as e:
                    logger.debug(f"Error extracting location from HTML: {e}")
                    
            logger.info(f"Final job location: {location}")
            
            # Extract job description with special handling for bullet points
            description_parts = []
            
            # Try to find the main description container
            desc_containers = []
            for desc_selector in [".jobs-description__content", "#job-details", ".description__text", ".jobs-description-content", ".jobs-box__html-content"]:
                try:
                    containers = driver.find_elements(By.CSS_SELECTOR, desc_selector)
                    if containers:
                        desc_containers.extend(containers)
                except:
                    continue
            
            # Process each container
            for container in desc_containers:
                try:
                    # Get all text elements including headers and paragraphs
                    text_elements = container.find_elements(By.CSS_SELECTOR, "p, h1, h2, h3, h4, h5, h6")
                    for element in text_elements:
                        text = element.text.strip()
                        if text:
                            description_parts.append(text)
                    
                    # Get all list items (bullet points)
                    list_items = container.find_elements(By.CSS_SELECTOR, "li, .jobs-description__bullet")
                    for item in list_items:
                        bullet_text = item.text.strip()
                        if bullet_text:
                            description_parts.append(f"• {bullet_text}")
                    
                    # If we found content, no need to check other containers
                    if description_parts:
                        logger.info(f"Found description content in container: {len(description_parts)} elements")
                        break
                except Exception as e:
                    logger.warning(f"Error processing description container: {e}")
            
            # If we still don't have content, try to get the raw HTML and extract text
            if not description_parts:
                try:
                    for container in desc_containers:
                        html_content = container.get_attribute('innerHTML')
                        # Use a simple approach to extract text from HTML
                        # This is not perfect but can help in some cases
                        text = html_content.replace('<br>', '\n').replace('<li>', '\n• ')
                        text = re.sub(r'<[^>]+>', ' ', text)  # Remove HTML tags
                        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
                        if text:
                            description_parts.append(text)
                            logger.info("Extracted description from HTML content")
                            break
                except:
                    pass
            
            # If still no content, try the previous approach as fallback
            if not description_parts:
                for desc_selector in [".jobs-description__content", "#job-details", ".description__text"]:
                    try:
                        text = driver.find_element(By.CSS_SELECTOR, desc_selector).text.strip()
                        if text:
                            description_parts.append(text)
                            logger.info("Found description using fallback selector")
                            break
                    except:
                        continue
            
            # Combine all parts into a single description
            description = "\n\n".join(description_parts) if description_parts else "Unknown Description"
            logger.info(f"Extracted job description ({len(description)} characters)")
            
            # Check for mentions of cloud providers
            job_is_amazon = []
            job_is_msft = []
            job_is_google = []
            job_is_alibaba = []
            
            # Process each sentence in the description
            for sentence in description.split('\n'):
                if 'aws' in sentence.lower() or 'amazon' in sentence.lower():
                    job_is_amazon.append(sentence)
                if 'azure' in sentence.lower() or 'microsoft' in sentence.lower():
                    job_is_msft.append(sentence)
                if 'gcp' in sentence.lower() or 'google' in sentence.lower():
                    job_is_google.append(sentence)
                if 'alicloud' in sentence.lower() or 'alipay' in sentence.lower() or 'alibaba' in sentence.lower() or '阿里' in sentence:
                    job_is_alibaba.append(sentence)
            
            logger.info(f"Found {len(job_is_amazon)} sentences mentioning Amazon/AWS")
            logger.info(f"Found {len(job_is_msft)} sentences mentioning Microsoft/Azure")
            logger.info(f"Found {len(job_is_google)} sentences mentioning Google/GCP")
            logger.info(f"Found {len(job_is_alibaba)} sentences mentioning Alibaba/AliCloud/Alipay/阿里")
            
            # Save job details
            job_details.append({
                'job_id': job_id,
                'title': job_title,
                'company': company,
                'location': location,
                'description': description,
                'url': job_url,
                'Job_IS_Amazon': job_is_amazon,
                'Job_IS_MSFT': job_is_msft,
                'Job_IS_Google': job_is_google,
                'Job_IS_Alibaba': job_is_alibaba
            })
            
            # Add random delay to avoid detection
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            logger.error(f"Error processing job ID {job_id}: {e}")
            continue
    
    # Save job details to CSV
    if job_details:
        df = pd.DataFrame(job_details)
        df.to_csv("job_details_one_by_one.csv", index=False)
        logger.info(f"Saved {len(job_details)} job details to job_details_one_by_one.csv")
    
    return job_details

def main():
    # LinkedIn job search URL
    search_url = "https://www.linkedin.com/jobs/search/?currentJobId=4176105597&f_C=67172076%2C13427342%2C31380518%2C12904942%2C31411332&geoId=92000000&origin=COMPANY_PAGE_JOBS_CLUSTER_EXPANSION&originToLandingJobPostings=4026419284%2C4191492284%2C4191488681%2C4190297579%2C4199399891%2C4191906534%2C4182788851%2C4143107247%2C4172215447"
    
    # Manually specified job ID list (can be used if collection from page fails)
    manual_job_ids = [
        "4026419284", "4191492284", "4191488681", "4190297579", 
        "4199399891", "4191906534", "4182788851", "4143107247", 
        "4172215447", "4176105597"
    ]
    
    logger.info("Starting LinkedIn Job Scraper (One-by-One Version)...")
    
    # Set up WebDriver - default to non-headless mode
    driver = setup_driver(headless=False)
    
    try:
        # Manual login to LinkedIn
        if manual_login(driver):
            # Check if we're running in interactive mode (terminal)
            import sys
            if sys.stdin.isatty():
                # Ask user if they want to start from a specific position
                start_from = input("Enter the job position to start collecting from (default is 0): ")
                start_position = 0
                if start_from.strip() and start_from.isdigit():
                    start_position = int(start_from)
                    logger.info(f"Will start collecting from job #{start_position}")
                
                # Ask user for maximum number of jobs to collect
                max_jobs_input = input("Enter the maximum number of jobs to collect (default is all available jobs): ")
                max_jobs = int(max_jobs_input) if max_jobs_input.strip() and max_jobs_input.isdigit() else float('inf')
            else:
                # Default values for non-interactive mode
                start_position = 0
                max_jobs = float('inf')
                logger.info("Running in non-interactive mode with default values")
            
            # Collect job IDs one by one from search page
            job_ids = collect_job_ids_one_by_one(driver, search_url, max_jobs=max_jobs, start=start_position)
            
            # If collection from page fails, use manually specified job ID list
            if not job_ids:
                logger.info("Using manually specified job ID list")
                job_ids = manual_job_ids
            
            # Get job details
            job_details = get_job_details(driver, job_ids)
            logger.info(f"Total job details collected: {len(job_details)}")
        else:
            logger.error("Login failed, cannot continue scraping")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Close browser
        # Check if we're running in interactive mode (terminal)
        import sys
        if sys.stdin.isatty():
            input("Scraping complete, press Enter to close the browser...")
        else:
            logger.info("Scraping complete, closing browser automatically")
        driver.quit()
        logger.info("Browser closed")

if __name__ == "__main__":
    main()
