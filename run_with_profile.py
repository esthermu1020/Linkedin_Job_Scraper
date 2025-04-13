#!/usr/bin/env python3
"""
LinkedIn Scraper with Chrome Profile Support
This script runs the LinkedIn scraper using your existing Chrome profile,
which helps avoid login issues since you're already logged in.
"""

import os
import sys
import time
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Import the scraper functions
from linkedin_scraper_one_by_one import collect_job_ids_one_by_one, get_job_details

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_profile_scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_default_chrome_profile():
    """
    Get the default Chrome profile directory based on OS
    
    Returns:
        str: Path to Chrome profile directory
    """
    home = os.path.expanduser("~")
    
    if sys.platform == "darwin":  # macOS
        return os.path.join(home, "Library/Application Support/Google/Chrome/User Data")
    elif sys.platform.startswith("win"):  # Windows
        return os.path.join(home, "AppData/Local/Google/Chrome/User Data")
    else:  # Linux
        return os.path.join(home, ".config/google-chrome")

def setup_driver_with_profile(profile_dir=None, headless=False):
    """
    Set up Chrome WebDriver with a specific user profile
    
    Args:
        profile_dir (str): Path to Chrome profile directory
        headless (bool): Whether to run in headless mode
        
    Returns:
        WebDriver: Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Use specified profile or find default
    if not profile_dir:
        profile_dir = get_default_chrome_profile()
    
    if os.path.exists(profile_dir):
        chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        logger.info(f"Using Chrome profile at: {profile_dir}")
    else:
        logger.warning(f"Chrome profile directory not found: {profile_dir}")
        logger.info("Continuing with a new profile")
    
    # Add anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Add headless mode if requested
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute script to modify navigator properties
    driver.execute_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """)
    
    if not headless:
        driver.maximize_window()
    
    return driver

def check_login_status(driver):
    """
    Check if already logged in to LinkedIn
    
    Args:
        driver: WebDriver instance
        
    Returns:
        bool: True if logged in, False otherwise
    """
    driver.get("https://www.linkedin.com")
    logger.info("Navigating to LinkedIn homepage")
    
    # Wait for page to load
    time.sleep(5)
    
    # Check if logged in
    if any(x in driver.current_url for x in ["feed", "mynetwork", "jobs", "messaging"]):
        logger.info("Already logged in to LinkedIn")
        return True
    else:
        logger.info("Not logged in to LinkedIn")
        return False

def main():
    """Main function to run the scraper with profile support"""
    parser = argparse.ArgumentParser(description="LinkedIn Scraper with Chrome Profile Support")
    parser.add_argument("--profile", help="Path to Chrome profile directory")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--url", help="LinkedIn job search URL")
    parser.add_argument("--max-jobs", type=int, default=10, help="Maximum number of jobs to collect")
    args = parser.parse_args()
    
    # LinkedIn job search URL (default or from args)
    search_url = args.url or "https://www.linkedin.com/jobs/search/?keywords=cloud&location=United%20States&locationId=&geoId=103644278&f_TPR=r604800&position=1&pageNum=0"
    
    try:
        # Set up WebDriver with profile
        driver = setup_driver_with_profile(args.profile, args.headless)
        logger.info("Browser started successfully")
        
        # Check if already logged in
        if check_login_status(driver):
            # Collect job IDs
            logger.info(f"Starting to collect job IDs from: {search_url}")
            job_ids = collect_job_ids_one_by_one(driver, search_url, max_jobs=args.max_jobs)
            logger.info(f"Collected {len(job_ids)} job IDs")
            
            # Get job details
            if job_ids:
                logger.info("Starting to collect job details")
                job_details = get_job_details(driver, job_ids)
                logger.info(f"Collected details for {len(job_details)} jobs")
                logger.info("Results saved to job_details_one_by_one.csv")
            else:
                logger.warning("No job IDs collected")
        else:
            logger.info("Please log in to LinkedIn manually")
            input("Press Enter after logging in...")
            
            # Try again after manual login
            if check_login_status(driver):
                # Collect job IDs
                logger.info(f"Starting to collect job IDs from: {search_url}")
                job_ids = collect_job_ids_one_by_one(driver, search_url, max_jobs=args.max_jobs)
                logger.info(f"Collected {len(job_ids)} job IDs")
                
                # Get job details
                if job_ids:
                    logger.info("Starting to collect job details")
                    job_details = get_job_details(driver, job_ids)
                    logger.info(f"Collected details for {len(job_details)} jobs")
                    logger.info("Results saved to job_details_one_by_one.csv")
                else:
                    logger.warning("No job IDs collected")
            else:
                logger.error("Failed to log in to LinkedIn")
        
        # Keep browser open for inspection if not headless
        if not args.headless:
            input("Press Enter to quit...")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    main()
