"""
Setup WebDriver for LinkedIn scraping with anti-detection measures
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import random
import logging

logger = logging.getLogger(__name__)

def setup_driver(headless=False):
    """Set up and return a configured Chrome WebDriver with enhanced anti-detection
    
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
    
    # Enhanced anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Add a realistic user agent
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute CDP commands to prevent detection
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": driver.execute_script("return navigator.userAgent")
    })
    
    # Execute script to modify navigator properties - enhanced version
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Overwrite the 'plugins' property to use a custom getter
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                // Create a fake plugins array with length > 0
                const plugins = [1, 2, 3, 4, 5];
                plugins.refresh = () => {};
                plugins.item = () => { return {}; };
                plugins.namedItem = () => { return {}; };
                return plugins;
            }
        });
        
        // Overwrite the 'languages' property
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'es']
        });
        
        // Modify the permission behavior
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({state: Notification.permission});
            }
            return originalQuery(parameters);
        };
        """
    })
    
    # Only maximize if not in headless mode
    if not headless:
        driver.maximize_window()
    
    logger.info("WebDriver setup complete with enhanced anti-detection measures")
    return driver
