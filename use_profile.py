#!/usr/bin/env python3
"""
LinkedIn Scraper with Chrome Profile Support
This script allows you to use your existing Chrome profile for LinkedIn automation,
which can help avoid detection since you're already logged in.
"""

import os
import sys
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import logging

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
    """Get the default Chrome profile directory based on OS"""
    home = os.path.expanduser("~")
    
    if sys.platform == "darwin":  # macOS
        return os.path.join(home, "Library/Application Support/Google/Chrome/Default")
    elif sys.platform.startswith("win"):  # Windows
        return os.path.join(home, "AppData/Local/Google/Chrome/User Data/Default")
    else:  # Linux
        return os.path.join(home, ".config/google-chrome/Default")

def setup_driver_with_profile(profile_dir=None, headless=False):
    """Set up Chrome WebDriver with a specific user profile"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Use specified profile or find default
    if not profile_dir:
        profile_dir = get_default_chrome_profile()
        
    # Get parent directory for Chrome's User Data
    if profile_dir.endswith("Default"):
        profile_dir = os.path.dirname(profile_dir)
    
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

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Scraper with Chrome Profile Support")
    parser.add_argument("--profile", help="Path to Chrome profile directory")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    try:
        driver = setup_driver_with_profile(args.profile, args.headless)
        
        # Navigate to LinkedIn
        driver.get("https://www.linkedin.com")
        logger.info("Navigated to LinkedIn")
        
        # Check if already logged in
        time.sleep(3)
        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            logger.info("Already logged in to LinkedIn")
        else:
            logger.info("Not logged in. Please log in manually in the browser window")
            input("Press Enter after logging in...")
        
        # Now you can continue with your scraping logic
        # ...
        
        # Example: navigate to jobs page
        driver.get("https://www.linkedin.com/jobs/")
        logger.info("Navigated to LinkedIn Jobs")
        
        # Keep browser open for inspection
        input("Press Enter to quit...")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main()
