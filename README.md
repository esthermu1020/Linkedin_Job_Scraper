# LinkedIn Job Scraper

A web-based tool for scraping and analyzing job listings from LinkedIn, with a focus on cloud technology skills and geographic distribution.

## Setup and Usage

1. **Installation**
   ```bash
   # Clone the repository
   git clone https://github.com/esthermu1020/Linkedin_Job_Scraper

   # Move to the current directory
   cd Linkedin

   # Run the setup script
   chmod +x run_scraper.sh
   ./run_scraper.sh
   ```

2. **Opening the Web Interface**
   ```bash
   # In the console, run the python file to redirect to the webpage
   "python app.py"
   # Open your browser and navigate to http://localhost:5001
   http://localhost:5001
   ```

3. **Using the Web Interface**
   # read the instruction page and move to the job scraper page
   - Enter a LinkedIn job search URL
   - Provide your LinkedIn credentials
   - Click "Start Scraping"
   - If LinkedIn requires verification, complete it in the browser window
   # view the results & analysis
   - View and Download results when scraping is complete (scroll down to the bottom to download the csv)
   - See the plots in the analysis tab

## Key Features

1. **Web Interface for Scraping**
   - User-friendly interface for entering LinkedIn search URLs and credentials
   - Real-time status updates and logging during the scraping process
   - Dark theme UI for better readability

2. **LinkedIn Integration**
   - Automated login to LinkedIn (with some limitations)
   - Job search URL parsing and processing
   - Detailed job information extraction

3. **Data Collection**
   - Collects job titles, companies, locations, and descriptions
   - Extracts job IDs for efficient processing
   - Handles pagination to collect multiple job listings

4. **Cloud Technology Analysis**
   - Identifies mentions of major cloud providers (AWS, Azure, GCP, Alibaba Cloud, Oracle Cloud)
   - Counts and categorizes jobs by cloud technology requirements
   - Provides summary statistics on cloud technology demand

5. **Data Visualization**
   - Interactive location-based job distribution chart
   - Company distribution analysis
   - Skill frequency analysis
   - Company-specific technical skill word clouds

6. **Export Capabilities**
   - Download results as CSV files
   - Save analysis for further processing

## Project Structure

- **Core Scraping**
  - `linkedin_scraper_one_by_one.py`: Main scraping functionality
  - `connector.py`: Integration between scraper and web interface
  - `setup_driver.py`: Browser automation configuration

- **Web Interface**
  - `app.py`: Flask application for the web interface
  - `templates/`: HTML templates for the web UI
  - `static/`: Static assets (CSS, JS, images)

- **Utilities**
  - `run_scraper.sh`: Shell script to set up environment and run the application
  - `run_with_profile.py`: Run scraper with browser profile
  - `use_profile.py`: Utilities for browser profile management

## System Requirements

- Python 3.6+
- Chrome browser
- Required Python packages (installed automatically by run_scraper.sh):
  - flask
  - pandas
  - selenium
  - webdriver-manager
  - beautifulsoup4
  - requests
  - lxml
  - plotly
  - wordcloud
  - matplotlib
  

## Visualization Features

1. **Jobs by Location**
   - Bar chart showing job distribution across different locations
   - Helps identify geographic hotspots for job opportunities
   - Provides insights into regional demand for skills

2. **Top Companies**
   - Bar chart displaying companies with the most job listings
   - Identifies major employers in the searched job category

3. **Most In-Demand Skills**
   - Bar chart showing the frequency of skills mentioned in job descriptions
   - Helps identify the most valuable skills in the job market

4. **Company-Specific Cloud Provider Skills**
   - Interactive word clouds showing technical skills required by specific companies
   - Focuses on cloud provider technologies (AWS, Azure, GCP, Alibaba, Oracle)
   - Helps compare skill requirements across different employers

## Known Issues

1. **LinkedIn Login Challenges**
   - LinkedIn's security measures may prevent automatic login
   - The current implementation may fail to automatically fill in credentials
   - Manual verification may be required during the login process

2. **Rate Limiting**
   - LinkedIn may rate-limit or block scraping attempts
   - The tool implements delays and anti-detection measures, but may still be detected

## Disclaimer

This tool is for research purposes only. Use of this tool may violate LinkedIn's Terms of Service. Users are responsible for ensuring their use complies with all applicable terms of service, laws, and regulations.
