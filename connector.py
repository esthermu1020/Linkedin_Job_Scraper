"""
Connector module to integrate the LinkedIn scraper with the web interface
"""

import os
import sys
import time
import logging
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the current directory to the path so we can import the scraper module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the LinkedIn scraper functions
try:
    from linkedin_scraper_one_by_one import collect_job_ids_one_by_one, get_job_details
except ImportError:
    print("Error: Could not import LinkedIn scraper module. Make sure linkedin_scraper_one_by_one.py is in the same directory.")

# Configure logging
log_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           f"linkedin_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
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

def login_to_linkedin(driver, email, password):
    """
    Login to LinkedIn with provided credentials using enhanced detection methods
    to ensure reliable form filling and submission
    """
    driver.get("https://www.linkedin.com/login")
    logger.info("Navigating to LinkedIn login page")
    
    try:
        # Wait for page to fully load - increased wait time
        time.sleep(8)
        
        # Check if already logged in
        if any(x in driver.current_url for x in ["feed", "mynetwork", "jobs"]):
            logger.info("Already logged in to LinkedIn")
            return True
        
        # Check if on verification page
        if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
            logger.info("LinkedIn security verification detected before login attempt")
            logger.info("Waiting for manual verification (60 seconds)...")
            time.sleep(60)  # Give user time to complete verification
            return True
        
        # ---- IMPROVED USERNAME FIELD HANDLING ----
        # Try JavaScript injection first (most reliable method)
        try:
            driver.execute_script("document.getElementById('username').value = arguments[0]", email)
            logger.info(f"Email entered using JavaScript injection: {email.split('@')[0]}...")
            success_username = True
        except Exception as e:
            logger.warning(f"JavaScript username injection failed: {str(e)}")
            success_username = False
        
        # If JavaScript fails, try traditional Selenium methods
        if not success_username:
            # Try multiple selectors for username field
            username_field = None
            username_selectors = [
                (By.ID, "username"),
                (By.NAME, "session_key"),
                (By.CSS_SELECTOR, "input[name='session_key']"),
                (By.CSS_SELECTOR, ".login-email"),
                (By.XPATH, "//input[@id='username']"),
                (By.XPATH, "//input[@autocomplete='username']")
            ]
            
            for selector_type, selector in username_selectors:
                try:
                    username_field = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if username_field:
                        logger.info(f"Found username field using {selector_type}={selector}")
                        break
                except:
                    continue
            
            if not username_field:
                logger.error("Could not find username field")
                return False
            
            # Clear field and enter email with human-like typing
            try:
                username_field.clear()
                for char in email:
                    username_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
                logger.info(f"Email entered with human-like typing: {email.split('@')[0]}...")
            except Exception as e:
                logger.error(f"Failed to enter email: {str(e)}")
                return False
        
        # Wait before entering password
        time.sleep(random.uniform(1.0, 2.0))
        
        # ---- IMPROVED PASSWORD FIELD HANDLING ----
        # Try JavaScript injection first
        try:
            driver.execute_script("document.getElementById('password').value = arguments[0]", password)
            logger.info("Password entered using JavaScript injection")
            success_password = True
        except Exception as e:
            logger.warning(f"JavaScript password injection failed: {str(e)}")
            success_password = False
        
        # If JavaScript fails, try traditional Selenium methods
        if not success_password:
            # Try multiple selectors for password field
            password_field = None
            password_selectors = [
                (By.ID, "password"),
                (By.NAME, "session_password"),
                (By.CSS_SELECTOR, "input[name='session_password']"),
                (By.CSS_SELECTOR, ".login-password"),
                (By.XPATH, "//input[@id='password']"),
                (By.XPATH, "//input[@autocomplete='current-password']")
            ]
            
            for selector_type, selector in password_selectors:
                try:
                    password_field = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if password_field:
                        logger.info(f"Found password field using {selector_type}={selector}")
                        break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                return False
            
            # Clear field and enter password with human-like typing
            try:
                password_field.clear()
                for char in password:
                    password_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
                logger.info("Password entered with human-like typing")
            except Exception as e:
                logger.error(f"Failed to enter password: {str(e)}")
                return False
        
        # Wait before clicking login button
        time.sleep(random.uniform(1.0, 2.0))
        
        # ---- IMPROVED LOGIN BUTTON HANDLING ----
        # Try JavaScript click first
        try:
            driver.execute_script("document.querySelector('button[type=\"submit\"]').click()")
            logger.info("Login button clicked using JavaScript")
            button_clicked = True
        except Exception as e:
            logger.warning(f"JavaScript button click failed: {str(e)}")
            button_clicked = False
        
        # If JavaScript click fails, try traditional methods
        if not button_clicked:
            # Try multiple selectors for login button
            login_button = None
            button_selectors = [
                (By.XPATH, "//button[@type='submit']"),
                (By.CSS_SELECTOR, ".login__form_action_container button"),
                (By.CSS_SELECTOR, "button[data-litms-control-urn='login-submit']"),
                (By.CSS_SELECTOR, ".btn__primary--large"),
                (By.XPATH, "//button[contains(@class, 'btn__primary--large')]"),
                (By.XPATH, "//button[contains(text(), 'Sign in')]")
            ]
            
            for selector_type, selector in button_selectors:
                try:
                    login_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    if login_button:
                        logger.info(f"Found login button using {selector_type}={selector}")
                        break
                except:
                    continue
            
            if not login_button:
                logger.error("Could not find login button")
                return False
            
            # Try JavaScript click first, then regular click if that fails
            logger.info("Clicking login button")
            try:
                driver.execute_script("arguments[0].click();", login_button)
                logger.info("Used JavaScript click on login button")
            except:
                try:
                    login_button.click()
                    logger.info("Used regular click on login button")
                except Exception as e:
                    logger.error(f"Failed to click login button: {str(e)}")
                    return False
        
        # Wait longer for login to complete
        logger.info("Waiting for login to complete...")
        time.sleep(5)  # Increased from 3 to 5 seconds
        
        # Check if login was successful
        if any(x in driver.current_url for x in ["feed", "mynetwork", "jobs", "messaging", "dashboard"]):
            logger.info("Login successful!")
            return True
        
        # Check for security verification
        if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
            logger.info("LinkedIn security verification detected. Waiting for verification to complete...")
            # Wait for verification to complete (up to 3 minutes)
            max_wait = 180  # Increased maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if any(x in driver.current_url for x in ["feed", "mynetwork", "jobs", "messaging", "dashboard"]):
                    logger.info("Verification completed successfully")
                    return True
                time.sleep(2)  # Check every 2 seconds
            
            logger.warning("Verification timeout. Continuing with current state.")
            # Even if we timeout, we'll continue and see if we can proceed
            return True
        
        # Check for error messages
        try:
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert, .error, #error-for-username, #error-for-password")
            for element in error_elements:
                if element.is_displayed() and element.text.strip():
                    logger.error(f"Login error: {element.text.strip()}")
                    raise Exception(f"Login error: {element.text.strip()}")
        except:
            pass
        
        logger.warning(f"Login may have failed. Current URL: {driver.current_url}")
        # We'll try to continue anyway, as sometimes LinkedIn redirects to unexpected URLs
        return True
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise Exception(f"Error during login: {str(e)}")

# Define the LinkedInConnector class that was missing
class LinkedInConnector:
    """Class to connect the LinkedIn scraper with the web interface"""
    
    def __init__(self, search_url='', max_jobs=10, start_position=0, manual_job_ids='', log_file=None, headless=False):
        """Initialize the connector with the given parameters"""
        self.search_url = search_url
        self.max_jobs = max_jobs
        self.start_position = int(start_position) if start_position else 0  # Ensure start_position is an integer
        self.manual_job_ids = manual_job_ids
        self.log_file = log_file
        self.headless = headless
        self.email = None
        self.password = None
        self.logger = logger
    
    def run(self):
        """Run the scraper and return the results"""
        return run_scraper(
            search_url=self.search_url,
            max_jobs=self.max_jobs,
            start_position=self.start_position,
            manual_job_ids=self.manual_job_ids,
            headless=self.headless
        )
    
def run_scraper(search_url, max_jobs='all', start_position=0, manual_job_ids='', linkedin_email='', linkedin_password='', headless=False):
    """
    Run the LinkedIn scraper with the given parameters
    
    Args:
        search_url (str): LinkedIn job search URL
        max_jobs (str or int): Maximum number of jobs to collect, 'all' for unlimited
        start_position (int): Position to start collecting from
        manual_job_ids (str): Comma-separated list of job IDs
        linkedin_email (str): LinkedIn login email
        linkedin_password (str): LinkedIn login password
        headless (bool): Whether to run Chrome in headless mode
        
    Returns:
        dict: Results of the scraping operation
    """
    # Create a global variable to store the log filename so it can be accessed from outside
    global log_filename
    
    # Ensure start_position is an integer
    start_position = int(start_position) if start_position else 0
    
    results = {
        "status": "running",
        "message": "Setting up the scraper...",
        "job_count": 0,
        "jobs": [],
        "cloud_mentions": {
            "aws": 0,
            "azure": 0,
            "gcp": 0,
            "alibaba": 0
        },
        "logs": [],
        "log_file": log_filename
    }
    
    def add_log(message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level
        }
        results["logs"].append(log_entry)
        results["message"] = message
        
        # Also log to file via logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    driver = None
    try:
        # Set up the WebDriver
        driver = setup_driver(headless=headless)
        add_log(f"Browser started successfully {'in headless mode' if headless else ''}")
        add_log("Chrome browser launched and configured")
        
        # Login to LinkedIn
        add_log("Navigating to LinkedIn login page...")
        login_success = False
        
        # First try automatic login
        if linkedin_email and linkedin_password:
            try:
                add_log(f"Attempting automatic login for user {linkedin_email.split('@')[0]}...")
                login_success = login_to_linkedin(driver, linkedin_email, linkedin_password)
                if login_success:
                    add_log("✓ LinkedIn login successful!", "success")
                    add_log("User authenticated and ready to scrape")
                else:
                    add_log("⚠️ Automatic login may have encountered issues", "warning")
                    add_log("Will attempt to continue with current session")
                    # We'll continue anyway since we modified the login function to be more permissive
                    login_success = True
            except Exception as e:
                add_log(f"⚠️ Login process encountered an error: {str(e)}", "warning")
                # Fall back to manual login approach
                add_log("Falling back to manual login approach...")
                
        # If automatic login failed or wasn't attempted, try the original script's manual login
        if not login_success:
            from linkedin_scraper_one_by_one import manual_login
            add_log("Attempting manual login process with automatic timeout...")
            login_success = manual_login(driver)
            if login_success:
                add_log("✓ Manual login successful!", "success")
            else:
                add_log("⚠️ Manual login may have encountered issues", "warning")
                # We'll continue anyway and see if we can proceed
                login_success = True
        
        # Proceed with scraping
        if login_success:
            # Convert max_jobs to the appropriate type
            try:
                max_jobs_value = float('inf') if max_jobs == 'all' else int(max_jobs)
            except (ValueError, TypeError):
                add_log(f"Warning: Could not convert max_jobs '{max_jobs}' to integer, using infinity", "warning")
                max_jobs_value = float('inf')
            
            # Collect job IDs
            job_ids = []
            
            if search_url:
                add_log(f"Starting job collection from search URL...")
                add_log(f"Target URL: {search_url}")
                # Import the function directly to avoid any module-level issues
                from linkedin_scraper_one_by_one import collect_job_ids_one_by_one
                
                # Create a wrapper function to update logs during collection
                def collect_with_logging(driver, search_url, max_jobs, start_position=start_position):
                    job_ids = []
                    collected_ids = set()
                    # Ensure start_position is an integer
                    start_position = int(start_position) if start_position else 0
                    add_log(f"Starting collection from position {start_position}")
                    max_attempts = 2000
                    consecutive_failures = 0
                    max_consecutive_failures = 5
                    
                    add_log(f"🔍 Searching for jobs (max: {max_jobs if max_jobs != float('inf') else 'unlimited'})")
                    
                    while len(job_ids) < max_jobs and start_position < max_attempts and consecutive_failures < max_consecutive_failures:
                        try:
                            # Build URL with start parameter
                            base_url = re.sub(r'&start=\d+', '', search_url)
                            current_url = f"{base_url}&start={start_position}"
                            add_log(f"Processing job #{start_position+1} at position {start_position}")
                            
                            # Navigate to current URL
                            driver.get(current_url)
                            time.sleep(3)
                            
                            # Find job card and click (simplified for logging)
                            add_log(f"Looking for job card #{start_position+1}...")
                            
                            # Try different selectors to find job listings (simplified from original)
                            selectors = [
                                ".jobs-search-results__list-item",
                                ".job-card-container",
                                ".jobs-search-results-list__list-item"
                            ]
                            
                            job_card = None
                            for selector in selectors:
                                try:
                                    job_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                                    if job_cards:
                                        job_card = job_cards[0]
                                        add_log(f"Found job card using selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if not job_card:
                                add_log(f"⚠️ No job card found at position {start_position}", "warning")
                                consecutive_failures += 1
                                
                                # Try again at the same position up to 3 times
                                if consecutive_failures < 3:
                                    add_log(f"Retrying the same position (attempt {consecutive_failures}/3)...")
                                    continue
                                
                                start_position += 1
                                continue
                            
                            # Click on job card
                            add_log(f"Clicking on job card...")
                            click_success = False
                            click_attempts = 0
                            max_click_attempts = 3
                            
                            while not click_success and click_attempts < max_click_attempts:
                                try:
                                    driver.execute_script("arguments[0].click();", job_card)
                                    add_log(f"Click successful using JavaScript")
                                    click_success = True
                                except:
                                    try:
                                        job_card.click()
                                        add_log(f"Click successful using Selenium")
                                        click_success = True
                                    except:
                                        click_attempts += 1
                                        add_log(f"Click attempt {click_attempts} failed, retrying...")
                                        time.sleep(1)
                            
                            if not click_success:
                                add_log("⚠️ All click attempts failed on job card", "warning")
                                consecutive_failures += 1
                                
                                # Try again at the same position up to 3 times
                                if consecutive_failures < 3:
                                    add_log(f"Retrying the same position due to click failure (attempt {consecutive_failures}/3)...")
                                    continue
                                
                                start_position += 1
                                continue
                            
                            # Wait for page update
                            time.sleep(3)
                            
                            # Get current URL and extract job ID
                            current_url = driver.current_url
                            add_log(f"Current URL after click: {current_url}")
                            job_id = None
                            
                            # Extract job ID from URL
                            job_id_match = re.search(r'currentJobId=(\d+)', current_url)
                            if job_id_match:
                                job_id = job_id_match.group(1)
                                add_log(f"Extracted job ID: {job_id}")
                            else:
                                job_id_match = re.search(r'jobs/view/(\d+)', current_url)
                                if job_id_match:
                                    job_id = job_id_match.group(1)
                                    add_log(f"Extracted job ID from alternate format: {job_id}")
                                else:
                                    add_log(f"⚠️ Could not extract job ID from URL", "warning")
                            
                            # Check if this is a new job ID
                            if job_id and job_id not in collected_ids:
                                collected_ids.add(job_id)
                                job_ids.append(job_id)
                                consecutive_failures = 0
                                add_log(f"✓ Collected new job ID: {job_id} (total: {len(job_ids)})")
                                
                                # Save progress periodically
                                if len(job_ids) % 5 == 0:
                                    add_log(f"📊 Progress: {len(job_ids)} job IDs collected so far")
                            else:
                                if job_id in collected_ids:
                                    add_log(f"⚠️ Duplicate job ID detected: {job_id}", "warning")
                                consecutive_failures += 1
                            
                            # Add random delay
                            delay = random.uniform(1, 2)
                            add_log(f"Waiting {delay:.1f} seconds before next job...")
                            time.sleep(delay)
                            
                        except Exception as e:
                            add_log(f"❌ Error processing job item: {str(e)}", "error")
                            consecutive_failures += 1
                        
                        # Move to next job item
                        start_position += 1
                        add_log(f"Moving to next job position: {start_position}")
                    
                    add_log(f"✓ Job ID collection complete! Found {len(job_ids)} unique job IDs")
                    return job_ids
                
                # Use our logging wrapper instead of direct function call
                job_ids = collect_with_logging(driver, search_url, max_jobs_value)
                add_log(f"Total job IDs collected: {len(job_ids)}")
            
            # If no job IDs were collected or manual IDs were provided, use those
            if (not job_ids or len(job_ids) == 0) and manual_job_ids:
                job_ids = [id.strip() for id in manual_job_ids.split(',') if id.strip()]
                add_log(f"Using {len(job_ids)} manually provided job IDs")
                
            if not job_ids or len(job_ids) == 0:
                results["status"] = "error"
                results["message"] = "No job IDs found. Please check your search URL or provide manual job IDs."
                add_log("❌ No job IDs found. Please check your search URL or provide manual job IDs.", "error")
                driver.quit()
                return results
                
            # Get job details
            add_log(f"🔍 Starting to collect details for {len(job_ids)} jobs...")
            
            # Import the function directly to avoid any module-level issues
            from linkedin_scraper_one_by_one import get_job_details
            
            # Create a wrapper to add logs during job details collection
            def get_job_details_with_logs(driver, job_ids):
                # This is just a wrapper to add more logs during the process
                # The actual job details collection is done by the original function
                
                add_log(f"Starting to process {len(job_ids)} job IDs...")
                
                # Call the original function to get job details
                try:
                    job_details = get_job_details(driver, job_ids)
                    if job_details is None:
                        add_log("Warning: get_job_details returned None", "warning")
                        job_details = []
                except Exception as e:
                    add_log(f"Error in get_job_details: {str(e)}", "error")
                    job_details = []
                
                add_log(f"✓ Job details collection complete! Processed {len(job_details)} jobs")
                return job_details
            
            # Use our wrapper around the original function
            job_details = get_job_details_with_logs(driver, job_ids)
            
            # Ensure job_details is not None
            if job_details is None:
                add_log("❌ Job details collection returned None. Creating empty list.", "error")
                job_details = []
            
            # Process results
            results["jobs"] = job_details
            results["job_count"] = len(job_details)
            
            # Count cloud mentions
            add_log("📊 Analyzing cloud provider mentions...")
            for job in job_details:
                if job is None:
                    continue
                    
                if isinstance(job, dict):  # Make sure job is a dictionary
                    if job.get('Job_IS_Amazon') and len(job.get('Job_IS_Amazon', [])) > 0:
                        results["cloud_mentions"]["aws"] += 1
                    if job.get('Job_IS_MSFT') and len(job.get('Job_IS_MSFT', [])) > 0:
                        results["cloud_mentions"]["azure"] += 1
                    if job.get('Job_IS_Google') and len(job.get('Job_IS_Google', [])) > 0:
                        results["cloud_mentions"]["gcp"] += 1
                    if job.get('Job_IS_Alibaba') and len(job.get('Job_IS_Alibaba', [])) > 0:
                        results["cloud_mentions"]["alibaba"] += 1
            
            add_log(f"📊 Cloud provider analysis results:")
            add_log(f"- AWS/Amazon: {results['cloud_mentions']['aws']} jobs")
            add_log(f"- Azure: {results['cloud_mentions']['azure']} jobs")
            add_log(f"- GCP/Google: {results['cloud_mentions']['gcp']} jobs")
            add_log(f"- Alibaba Cloud: {results['cloud_mentions']['alibaba']} jobs")
            
            results["status"] = "completed"
            results["message"] = f"✅ Scraping completed successfully! Found {len(job_details)} jobs."
            add_log(f"✅ Scraping completed successfully! Found {len(job_details)} jobs.", "success")
        else:
            results["status"] = "error"
            results["message"] = "❌ Failed to log in to LinkedIn. Please check your credentials."
            add_log("❌ Failed to log in to LinkedIn. Please check your credentials.", "error")
    except Exception as e:
        results["status"] = "error"
        results["message"] = f"❌ Error during scraping: {str(e)}"
        add_log(f"❌ Error during scraping: {str(e)}", "error")
    finally:
        # Close the browser
        try:
            if driver:
                add_log("Closing browser...")
                driver.quit()
                add_log("✓ Browser closed successfully")
        except:
            add_log("⚠️ Error while closing browser", "warning")
    
    return results
