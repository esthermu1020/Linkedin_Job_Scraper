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
    start_position = int(start)  # Start from the specified position, ensure it's an integer
    max_attempts = 2000  # Maximum number of attempts, can be adjusted based on expected job count
    consecutive_failures = 0  # Count of consecutive failures
    max_consecutive_failures = 5  # Maximum consecutive failures before assuming we've reached the end
    
    logger.info(f"Starting to collect job IDs one by one, max collection: {max_jobs if max_jobs != float('inf') else 'unlimited'}, starting from position {start_position}")
    
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
                            f.write("{}\n".format(id))
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
            f.write("{}\n".format(job_id))
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
            
            # First, try to click all "See more" buttons to expand the content
            try:
                # Wait for the job description to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-description"))
                )
                
                # Find all "See more" buttons
                see_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'See more')]")
                see_more_spans = driver.find_elements(By.XPATH, "//span[contains(text(), 'See more')]")
                see_more_elements = see_more_buttons + see_more_spans
                
                # Click each "See more" button to expand content
                for i, button in enumerate(see_more_elements):
                    try:
                        logger.info(f"Clicking 'See more' button {i+1}/{len(see_more_elements)}")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.5)  # Small delay to let content expand
                    except Exception as e:
                        logger.debug(f"Error clicking 'See more' button: {e}")
                
                # Wait a moment for all expanded content to load
                time.sleep(1)
                logger.info(f"Clicked {len(see_more_elements)} 'See more' buttons to expand content")
                
            except Exception as e:
                logger.warning(f"Error expanding 'See more' content: {e}")
                
            # Extract job description with special handling for bullet points and sections
            description_parts = []
            responsibilities = []
            requirements = []
            
            # Current section being processed
            current_section = "general"
            
            # Try direct approach first - this is the most reliable for the specific job structure
            try:
                # Import re module locally to avoid "local variable 're' referenced before assignment" error
                import re
                
                # Wait for the job description to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-description"))
                )
                
                # Get the entire job description container
                job_description = driver.find_element(By.CSS_SELECTOR, ".jobs-description")
                
                if job_description:
                    # Try to find and click any remaining "See more" buttons
                    try:
                        # Look for "See more" buttons specifically within this container
                        see_more_buttons = job_description.find_elements(By.XPATH, ".//button[contains(text(), 'See more')]")
                        for button in see_more_buttons:
                            try:
                                logger.info("Found additional 'See more' button, clicking...")
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(0.5)  # Small delay to let content expand
                            except:
                                pass
                    except:
                        pass
                        
                    # Get the raw HTML content after expanding all sections
                    html_content = job_description.get_attribute('innerHTML')
                    
                    # Clean the HTML content
                    # 1. Replace "See more" buttons
                    html_content = re.sub(r'<button[^>]*>See more</button>', '', html_content)
                    html_content = re.sub(r'<span[^>]*>See more</span>', '', html_content)
                    
                    # 2. Replace any hidden content containers that might be duplicating content
                    html_content = re.sub(r'<div[^>]*style="display:\s*none[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
                    
                    # 3. Process bullet points
                    html_content = html_content.replace('<li>', '\n• ')
                    html_content = html_content.replace('</li>', '')
                    
                    # 4. Process line breaks
                    html_content = html_content.replace('<br>', '\n')
                    html_content = html_content.replace('<br/>', '\n')
                    html_content = html_content.replace('<br />', '\n')
                    
                    # 5. Remove all other HTML tags
                    html_content = re.sub(r'<[^>]+>', ' ', html_content)
                    
                    # 6. Fix whitespace
                    html_content = re.sub(r'\s+', ' ', html_content)
                    
                    # 7. Fix bullet points that might have been messed up
                    html_content = re.sub(r'• +', '• ', html_content)
                    
                    # 8. Split into paragraphs and clean each paragraph
                    paragraphs = []
                    html_content_lines = html_content.split('\n')
                    for paragraph in html_content_lines:
                        paragraph = paragraph.strip()
                        if paragraph:
                            paragraphs.append(paragraph)
                    
                    # 9. Remove duplicate paragraphs while preserving order
                    unique_paragraphs = []
                    seen_paragraphs = set()
                    
                    for paragraph in paragraphs:
                        # Skip "See more" paragraphs
                        if paragraph.strip().lower() == "see more":
                            continue
                            
                        # Normalize paragraph for comparison (remove extra spaces, lowercase)
                        normalized = re.sub(r'\s+', ' ', paragraph.lower().strip())
                        if normalized and normalized not in seen_paragraphs:
                            seen_paragraphs.add(normalized)
                            unique_paragraphs.append(paragraph)
                    
                    # 10. Join paragraphs with proper spacing
                    description = '\n\n'.join(unique_paragraphs)
                    
                    logger.info(f"Extracted job description directly with {len(unique_paragraphs)} unique paragraphs")
                    
                    # Skip the rest of the extraction methods
                    all_description_parts = [description]
                    
                else:
                    logger.warning("Could not find job description container")
                    all_description_parts = []
                    
            except Exception as e:
                logger.warning(f"Error with direct extraction approach: {e}")
                all_description_parts = []
            
            # If direct approach failed, try the previous methods
            if not all_description_parts:
                # Try to find the main description container with improved selectors
                desc_containers = []
                
                # First try the specific selector mentioned in the issue
                try:
                    # This is the specific selector mentioned in the issue
                    specific_selector = "body > div.application-outlet > div.authentication-outlet > div.scaffold-layout.scaffold-layout--breakpoint-md.scaffold-layout--main-aside.scaffold-layout--reflow.job-view-layout.jobs-details > div > div > main > div.job-view-layout.jobs-details > div:nth-child(1) > div > div:nth-child(4)"
                    containers = driver.find_elements(By.CSS_SELECTOR, specific_selector)
                    if containers:
                        logger.info(f"Found job description using the specific selector")
                        desc_containers.extend(containers)
                except Exception as e:
                    logger.debug(f"Error with specific selector: {e}")
                
                # If specific selector didn't work, try more general selectors
                if not desc_containers:
                    # Try the most reliable selectors for job description
                    for desc_selector in [
                        ".jobs-description", 
                        ".jobs-description__content", 
                        ".jobs-box__html-content",
                        ".jobs-description-content",
                        "#job-details", 
                        ".description__text",
                        "[data-test-id='job-details']",
                        ".jobs-unified-description__content",
                        ".jobs-details__main-content"
                    ]:
                        try:
                            containers = driver.find_elements(By.CSS_SELECTOR, desc_selector)
                            if containers:
                                logger.info(f"Found job description using selector: {desc_selector}")
                                
                                # Try to click any "See more" buttons in this container
                                for container in containers:
                                    try:
                                        see_more_buttons = container.find_elements(By.XPATH, ".//button[contains(text(), 'See more')]")
                                        for button in see_more_buttons:
                                            try:
                                                logger.info("Found 'See more' button in container, clicking...")
                                                driver.execute_script("arguments[0].click();", button)
                                                time.sleep(0.5)  # Small delay to let content expand
                                            except:
                                                pass
                                    except:
                                        pass
                                
                                desc_containers.extend(containers)
                                break  # Use the first successful selector
                        except Exception as e:
                            logger.debug(f"Error with selector {desc_selector}: {e}")
                            continue
                
                # Process each container
                for container in desc_containers:
                    try:
                        # Get the full HTML content for section detection
                        html_content = container.get_attribute('innerHTML')
                        
                        # First, try to extract structured content using XPath
                        # This helps with properly identifying sections and bullet points
                        
                        # Check if this container has the job description
                        if "About the job" in container.text or "Job details" in container.text:
                            logger.info("Found 'About the job' section")
                        
                        # Process each element in the container
                        elements = container.find_elements(By.XPATH, ".//*")
                        
                        # Track if we're inside a list to properly format bullet points
                        in_list = False
                        
                        for element in elements:
                            try:
                                # Check if this is a heading or paragraph that might indicate a section
                                tag_name = element.tag_name.lower()
                                text = element.text.strip()
                                
                                # Skip "See more" buttons
                                if text.lower() == "see more":
                                    continue
                                
                                if not text:
                                    continue
                                    
                                # Check if this element indicates a new section
                                text_lower = text.lower()
                                
                                # Detect section headers
                                if (tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong', 'b'] or 
                                    'font-weight: bold' in element.get_attribute('style') or 
                                    'font-weight:bold' in element.get_attribute('style')):
                                    
                                    # Check for responsibilities section
                                    if any(keyword in text_lower for keyword in ['responsibilities', 'duties', 'what you\'ll do', 'job description', 'role description']):
                                        current_section = "responsibilities"
                                        logger.info(f"Found responsibilities section: {text}")
                                        responsibilities.append(f"## {text}")
                                        continue
                                    
                                    # Check for requirements section
                                    elif any(keyword in text_lower for keyword in ['requirements', 'qualifications', 'what you need', 'skills', 'experience required', 'job requirements']):
                                        current_section = "requirements"
                                        logger.info(f"Found requirements section: {text}")
                                        requirements.append(f"## {text}")
                                        continue
                                    # Other section headers reset to general
                                    elif any(keyword in text_lower for keyword in ['about the company', 'about us', 'benefits', 'perks', 'why join', 'compensation']):
                                        current_section = "general"
                                
                                # Check if we're entering or exiting a list
                                if tag_name == 'ul' or tag_name == 'ol':
                                    in_list = True
                                elif tag_name == '/ul' or tag_name == '/ol':
                                    in_list = False
                                
                                # Process the text based on current section
                                if tag_name == 'li' or in_list or 'jobs-description__bullet' in element.get_attribute('class') or '•' in text or text.strip().startswith('-'):
                                    # This is a bullet point
                                    bullet_text = text.strip()
                                    if bullet_text:
                                        if current_section == "responsibilities":
                                            responsibilities.append(f"• {bullet_text}")
                                        elif current_section == "requirements":
                                            requirements.append(f"• {bullet_text}")
                                        else:
                                            description_parts.append(f"• {bullet_text}")
                                elif text:
                                    # Regular text
                                    if current_section == "responsibilities":
                                        responsibilities.append(text)
                                    elif current_section == "requirements":
                                        requirements.append(text)
                                    else:
                                        description_parts.append(text)
                                        
                            except Exception as e:
                                logger.debug(f"Error processing element: {e}")
                                continue
                        
                        # If we found content, no need to check other containers
                        if description_parts or responsibilities or requirements:
                            logger.info(f"Found content: {len(description_parts)} general, {len(responsibilities)} responsibilities, {len(requirements)} requirements")
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error processing description container: {e}")
                
                # If we still don't have content, try to get the raw HTML and extract text
                if not description_parts and not responsibilities and not requirements:
                    try:
                        for container in desc_containers:
                            html_content = container.get_attribute('innerHTML')
                            
                            # Remove "See more" buttons from HTML
                            html_content = re.sub(r'<button[^>]*>See more</button>', '', html_content)
                            html_content = re.sub(r'<span[^>]*>See more</span>', '', html_content)
                            
                            # Try to identify sections in the HTML
                            resp_match = re.search(r'(?:<[^>]*>)*(Responsibilities|Duties|What You\'ll Do|Job Description)(?:[^<]*</[^>]*>)', html_content, re.IGNORECASE)
                            req_match = re.search(r'(?:<[^>]*>)*(Requirements|Qualifications|What You Need|Skills Required|Basic Requirements)(?:[^<]*</[^>]*>)', html_content, re.IGNORECASE)
                            
                            if resp_match or req_match:
                                # Split the HTML at these section markers
                                sections = []
                                last_pos = 0
                                
                                for match in sorted([m for m in [resp_match, req_match] if m], key=lambda x: x.start()):
                                    sections.append(html_content[last_pos:match.start()])
                                    last_pos = match.start()
                                
                                sections.append(html_content[last_pos:])
                                
                                # Process each section
                                for i, section in enumerate(sections):
                                    # Clean up the HTML
                                    text = section.replace('<br>', '\n').replace('<li>', '\n• ')
                                    text = re.sub(r'<[^>]+>', ' ', text)  # Remove HTML tags
                                    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
                                    
                                    if i == 0:
                                        description_parts.append(text)
                                    elif resp_match and i == 1:
                                        responsibilities.append(text)
                                    elif req_match:
                                        requirements.append(text)
                            else:
                                # Use a simple approach to extract text from HTML
                                text = html_content.replace('<br>', '\n').replace('<li>', '\n• ')
                                text = re.sub(r'<[^>]+>', ' ', text)  # Remove HTML tags
                                text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
                                if text:
                                    description_parts.append(text)
                                    logger.info("Extracted description from HTML content")
                            break
                    except Exception as e:
                        logger.warning(f"Error extracting from HTML: {e}")
                
                # If still no content, try a direct approach to get the job description
                if not description_parts and not responsibilities and not requirements:
                    try:
                        # Try the specific selector from the issue directly
                        specific_selector = "body > div.application-outlet > div.authentication-outlet > div.scaffold-layout.scaffold-layout--breakpoint-md.scaffold-layout--main-aside.scaffold-layout--reflow.job-view-layout.jobs-details > div > div > main > div.job-view-layout.jobs-details > div:nth-child(1) > div > div:nth-child(4)"
                        job_desc_element = driver.find_element(By.CSS_SELECTOR, specific_selector)
                        
                        if job_desc_element:
                            logger.info("Found job description using the direct specific selector")
                            description_parts.append(job_desc_element.text)
                    except Exception as e:
                        logger.debug(f"Error with direct specific selector: {e}")
                        
                        # Try a more general approach as last resort
                        try:
                            # Look for any div that might contain the job description
                            potential_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'About the job') or contains(text(), 'Job description')]/following-sibling::div")
                            
                            for element in potential_elements:
                                if len(element.text) > 100:  # Likely a description if it has substantial text
                                    description_parts.append(element.text)
                                    logger.info("Found job description using XPath following-sibling approach")
                                    break
                        except Exception as e:
                            logger.debug(f"Error with XPath approach: {e}")
                
                # If still no content, try the previous approach as fallback
                if not description_parts and not responsibilities and not requirements:
                    for desc_selector in [".jobs-description__content", "#job-details", ".description__text"]:
                        try:
                            text = driver.find_element(By.CSS_SELECTOR, desc_selector).text.strip()
                            if text:
                                # Try to identify sections in the text
                                lines = text.split('\n')
                                current_section = "general"
                                
                                for line in lines:
                                    line_lower = line.lower()
                                    
                                    # Skip "See more" buttons
                                    if line_lower == "see more":
                                        continue
                                    
                                    # Check for section headers
                                    if any(keyword in line_lower for keyword in ['responsibilities', 'duties', 'what you\'ll do', 'job description']):
                                        current_section = "responsibilities"
                                        responsibilities.append(f"## {line}")
                                    elif any(keyword in line_lower for keyword in ['requirements', 'qualifications', 'what you need', 'skills']):
                                        current_section = "requirements"
                                        requirements.append(f"## {line}")
                                    elif any(keyword in line_lower for keyword in ['about the company', 'about us', 'benefits']):
                                        current_section = "general"
                                        description_parts.append(line)
                                    else:
                                        # Add content to appropriate section
                                        if current_section == "responsibilities":
                                            responsibilities.append(line)
                                        elif current_section == "requirements":
                                            requirements.append(line)
                                        else:
                                            description_parts.append(line)
                                
                                logger.info("Found description using fallback selector with section parsing")
                                break
                        except:
                            continue
                
                # Combine all parts into a single description, including responsibilities and requirements
                # First add general description parts
                all_description_parts = description_parts.copy() if description_parts else []
                
                # Add responsibilities with proper bullet points preserved
                if responsibilities:
                    # Add a separator before responsibilities section if we have general description
                    if all_description_parts:
                        all_description_parts.append("\n\n--- RESPONSIBILITIES ---\n")
                    all_description_parts.extend(responsibilities)
                    
                # Add requirements with proper bullet points preserved
                if requirements:
                    # Add a separator before requirements section
                    if all_description_parts:
                        all_description_parts.append("\n\n--- REQUIREMENTS ---\n")
                    all_description_parts.extend(requirements)
            
            # Join all parts into a single description, preserving the original order
            if all_description_parts:
                # Join with proper spacing
                description = "\n\n".join(all_description_parts)
                
                # Remove any "See more" buttons that might have been captured
                description = re.sub(r'(?:^|\n)See more(?:\n|$)', '\n', description)
                
                # Remove duplicate paragraphs that might have been captured
                unique_paragraphs = []
                seen_paragraphs = set()
                
                for paragraph in description.split("\n\n"):
                    # Skip empty paragraphs
                    if not paragraph.strip():
                        continue
                        
                    # Skip "See more" paragraphs
                    if paragraph.strip().lower() == "see more":
                        continue
                    
                    # Normalize paragraph for comparison (remove extra spaces, lowercase)
                    normalized = re.sub(r'\s+', ' ', paragraph.lower().strip())
                    if normalized and normalized not in seen_paragraphs:
                        seen_paragraphs.add(normalized)
                        unique_paragraphs.append(paragraph)
                
                # Reconstruct the description with unique paragraphs
                description = "\n\n".join(unique_paragraphs)
            else:
                description = "Unknown Description"
            
            logger.info(f"Extracted complete job description ({len(description)} characters)")
            logger.info("Description contains {} paragraphs".format(description.count('\n\n') + 1))
            
            # Check for mentions of cloud providers
            job_is_amazon = []
            job_is_msft = []
            job_is_google = []
            job_is_alibaba = []
            job_is_oracle = []
            job_is_cloud = []
            
            import re

            # Split by common sentence/phrase delimiters: newline, comma, semicolon, period, colon, dash
            sentences = re.split(r'[\n,.;:\-–—]+', description)
            sentences = [s.strip() for s in sentences if s.strip()]  # Remove empty sentences
            
            for sentence in sentences:
                # For Amazon/AWS, exclude sentences that contain "laws" to avoid false positives
                # Check for AWS/Amazon cloud services - using more specific matching
                sentence_lower = sentence.lower()
                words = re.findall(r'\b\w+\b', sentence_lower)
                
                # Amazon/AWS check with more specific context
                if ('aws' in words or 'amazon' in words or "alexa" in words and 'laws' not in words):
                    job_is_amazon.append(sentence)
                else:
                    # Check for AWS specific services with better context
                    aws_services = ['ec2', 's3', 'lambda', 'dynamodb', 'rds', 'cloudformation', 'cloudwatch', 
                                   'iam', 'eks', 'sagemaker', 'cloudfront', 'route53', 'redshift', 'sqs', 'fargate']
                    if any(f" {service} " in f" {sentence_lower} " for service in aws_services):
                        job_is_amazon.append(sentence)

                # Check for Azure cloud services - more specific matching
                if 'azure' in words or 'microsoft azure' in sentence_lower:
                    job_is_msft.append(sentence)
                else:
                    # Check for Azure specific services with better context
                    azure_services = ['azure vm', 'azure functions', 'azure storage', 'cosmos db', 
                                     'azure sql', 'azure devops', 'azure kubernetes', 'azure active directory',
                                     'azure logic apps', 'azure app service']
                    # Only match if "azure" or "microsoft" is in the same sentence
                    if ('azure' in sentence_lower or 'microsoft' in sentence_lower) and \
                       any(service in sentence_lower for service in azure_services):
                        job_is_msft.append(sentence)
                    elif ' aks ' in f" {sentence_lower} " and ('kubernetes' in sentence_lower or 'azure' in sentence_lower):
                        job_is_msft.append(sentence)
                
                # Check for Google Cloud Platform services - more specific matching
                if 'gcp' in words or 'google cloud' in sentence_lower:
                    job_is_google.append(sentence)
                else:
                    # Check for Google Cloud specific services with better context
                    gcp_services = ['bigquery', 'cloud storage', 'compute engine', 'cloud functions', 
                                   'dataflow', 'cloud spanner', 'cloud run', 'dataproc']
                    # Only match if "google" is in the same sentence
                    if 'google' in sentence_lower and any(service in sentence_lower for service in gcp_services):
                        job_is_google.append(sentence)
                    elif ' gke ' in f" {sentence_lower} " and ('kubernetes' in sentence_lower or 'google' in sentence_lower):
                        job_is_google.append(sentence)
                
                # Check for Alibaba Cloud services - more specific matching
                if 'alicloud' in words or 'alipay' in words or 'alibaba' in words or '阿里' in sentence:
                    job_is_alibaba.append(sentence)
                else:
                    # Check for Alibaba Cloud specific services with better context
                    alibaba_services = ['maxcompute', 'tablestore', 'polardb', 'odps', 'datav']
                    # Only match if "alibaba", "ali", or "aliyun" is in the same sentence
                    if any(term in sentence_lower for term in ['alibaba', 'aliyun', 'alicloud']) and \
                       any(service in sentence_lower for service in alibaba_services):
                        job_is_alibaba.append(sentence)
                    # Handle common terms that might cause false positives
                    elif any(term in f" {sentence_lower} " for term in [' ecs ', ' oss ', ' sls ', ' pai ']):
                        # Only classify if there's clear Alibaba context
                        if any(term in sentence_lower for term in ['alibaba', 'aliyun', 'alicloud', 'china cloud']):
                            job_is_alibaba.append(sentence)

                # Check for Oracle Cloud services - more specific matching
                if 'oracle cloud' in sentence_lower or 'oci' in words:
                    job_is_oracle.append(sentence)
                else:
                    # Check for Oracle Cloud specific services with better context
                    oracle_services = ['oracle cloud infrastructure', 'oci', 'oracle database', 'oracle applications']
                    if any(service in sentence_lower for service in oracle_services):
                        job_is_oracle.append(sentence)
                # Check for general cloud mentions
                if 'cloud' in words and not any(term in sentence_lower for term in ['aws', 'azure', 'google', 'alibaba', 'oracle']):
                    job_is_cloud.append(sentence)

            # Update log messages to be more accurate with our improved classification
            if job_is_amazon:
                logger.info(f"Found {len(job_is_amazon)} sentences with confirmed AWS/Amazon cloud references")
            if job_is_msft:
                logger.info(f"Found {len(job_is_msft)} sentences with confirmed Microsoft Azure references")
            if job_is_google:
                logger.info(f"Found {len(job_is_google)} sentences with confirmed Google Cloud Platform references")
            if job_is_alibaba:
                logger.info(f"Found {len(job_is_alibaba)} sentences with confirmed Alibaba Cloud references")
            if job_is_oracle:
                logger.info(f"Found {len(job_is_oracle)} sentences with confirmed Oracle Cloud references")
            if job_is_cloud:
                logger.info(f"Found {len(job_is_cloud)} sentences with general cloud references (not specific to any CSP)")
            
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
                'Job_IS_Alibaba': job_is_alibaba,
                'Job_IS_Oracle': job_is_oracle,
                'Job_IS_Cloud': job_is_cloud,
            })

            # add country infered from location
            country = location.split(',')[-1].strip() if ',' in location else 'Unknown'
            job_details[-1]['country'] = country

            # add a column where job_is_amazon, job_is_msft, job_is_google, job_is_alibaba, job_is_oracle are joined as a string
            job_details[-1]['Job_IS_Any_CSP'] = ', '.join([
                'Amazon' if job_is_amazon else '',
                'Microsoft Azure' if job_is_msft else '',
                'Google Cloud' if job_is_google else '',
                'Alibaba Cloud' if job_is_alibaba else '',
                'Oracle Cloud' if job_is_oracle else ''
            ]).strip(', ')
            
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
