# LinkedIn Job Scraper

A web-based tool for scraping and analyzing job listings from LinkedIn, with a focus on cloud technology skills and geographic distribution.

![LinkedIn Job Scraper Introduction Page](example_result/Example_linkedIn_job%20scraper_introduction_page.png)

*Screenshot: LinkedIn Job Scraper Introduction Page*

## Installation Options

### Pre-requisite: 
* You must have Google Chrome installed in your laptop
* You must have a Linkedin Account

You have two ways to use this project:

### Option 1: Use Pre-compiled Binary (Recommended)

For users who want a quick start without setting up a development environment:

#### For Mac Users:
1. **Download the pre-compiled binary**
   - Download using the Google Drive https://drive.google.com/file/d/1S7s_tjodfZ7ARH9OvkBxlAFbhsmfJGuf/view?usp=drive_link 
   - Locate to the directory where you have the file. Then run the `LinkedIn_Job_Scraper` executable directly. If you downloaded the file to your Downloads directory, then
   ```bash
   cd Downloads/
   ./LinkedIn_Job_Scraper
   ```
   - You may encounter error "Apple cannot verify the app", please follow the 2. **Mac-specific Troubleshooting** to grant it access.
   - You may also encounter a permission error, to make the file executable, run the following code
   ```bash
   chmod +x LinkedIn_Job_Scraper
   ./LinkedIn_Job_Scraper
   ```
   - The application will start and be accessible at http://localhost:5001
   
2. **Mac-specific Troubleshooting**
   - If you see a message that Apple cannot verify the app:
     1. Try to open the application, you'll see a warning message
     2. Click on the Apple menu in the top-left corner and select "System Settings" (or "System Preferences")
     3. Go to "Privacy & Security" or "Security & Privacy"
     4. In the "Security" section, you'll see a message indicating the app was blocked
     5. Click the "Open Anyway" button, then click "Open" in the confirmation dialog
   - If you see "app is damaged and can't be opened" message, try running:
   ```bash
   xattr -d com.apple.quarantine LinkedIn_Job_Scraper
   ```

#### For Windows Users:
1. **Download the pre-compiled binary**
   - Download the Windows executable from Google Drive: https://drive.google.com/drive/folders/1H_J2EyuzeTyYCkmCe90GaOG3VW4R1Y5L?dmr=1&ec=wgc-drive-hero-goto
   - Extract the ZIP file if necessary
   - Double-click the `LinkedIn_Job_Scraper.exe` file to run the application
   - The application will start and be accessible at http://localhost:5001

2. **Windows-specific Troubleshooting**
   - If Windows Defender SmartScreen blocks the application:
     1. Click "More info" in the warning dialog
     2. Click "Run anyway" to proceed
   - If you see any DLL errors, make sure you have the latest Microsoft Visual C++ Redistributable installed
   - For Chrome driver issues, ensure Chrome browser is installed on your system
   - The project currently only includes a Mac binary
   - Windows users should follow Option 2 (Set Up Development Environment) below
   - If you need a Windows executable, you'll need to build it yourself using PyInstaller on a Windows machine:
   ```cmd
   pip install pyinstaller
   pyinstaller pyinstaller_build.spec
   ```
   - The resulting .exe file will be in the `dist` folder

#### General Troubleshooting:
- If Chrome doesn't launch when clicking "Start Scraping", ensure Chrome is installed on your system
- If you encounter any persistent issues with the pre-compiled version, try Option 2 below

### Option 2: Set Up Development Environment

For developers or if you need to customize the application:

1. **Installation**
   ```bash
   # Clone the repository
   git clone https://github.com/esthermu1020/Linkedin_Job_Scraper

   # Move to the current directory
   cd Linkedin

   # Install dependencies
   pip install -r requirements.txt
   
   # Make sure you have Selenium 4.x installed (important!)
   pip install --upgrade selenium
   ```

2. **Running the Application**
   ```bash
   # Run the Flask application
   python app.py
   
   # Open your browser and navigate to http://localhost:5001
   ```

3. **Building Your Own Binary (Optional)**
   ```bash
   # Install PyInstaller if you don't have it
   pip install pyinstaller
   
   # Build the application
   pyinstaller pyinstaller_build.spec
   ```

## Using the Web Interface

1. **Getting Started**
   - Read the instruction page and navigate to the job scraper page
   - Enter a LinkedIn job search URL
   - Click "Start Scraping"
   - If LinkedIn requires verification, complete it in the browser window

2. **Viewing Results & Analysis**
   - View and download results when scraping is complete (scroll down to the bottom to download the CSV)
   - See the plots in the analysis tab

   ![Results Data Table](example_result/Example_linkedIn_job%20scraper_result_page02.png)
   *Screenshot: Example of scraped job data results*

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

- Python 3.6+ (Python 3.8 recommended for binary compilation)
- Chrome browser
- Required Python packages (installed via requirements.txt):
  - flask
  - pandas
  - selenium (version 4.x required)
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

   ![Jobs by Location Chart](example_result/Example_linkedIn_job%20scraper_plot_page01.png)
   *Screenshot: Example of location-based job distribution visualization*

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

   ![Results Page](example_result/Example_linkedIn_job%20scraper_result_page.png)
   *Screenshot: Example of results page with data visualization*

## Known Issues

1. **LinkedIn Login Challenges**
   - LinkedIn's security measures may prevent automatic login
   - The current implementation may fail to automatically fill in credentials
   - Manual verification may be required during the login process

2. **Rate Limiting**
   - LinkedIn may rate-limit or block scraping attempts
   - The tool implements delays and anti-detection measures, but may still be detected

3. **Selenium Version Compatibility**
   - The application requires Selenium 4.x for proper functioning
   - If you encounter an error like `__init__() got an unexpected keyword argument 'options'`, it indicates a Selenium version compatibility issue
   - Solution: Ensure you're using Selenium 4.x by running `pip install --upgrade selenium` before packaging or running the application

## Disclaimer

This tool is for research purposes only. Use of this tool may violate LinkedIn's Terms of Service. Users are responsible for ensuring their use complies with all applicable terms of service, laws, and regulations.

## Example Results

The `example_result` directory contains sample outputs from the LinkedIn Job Scraper:

- `Example_linkedIn_job scraper_introduction_page.png`: The introduction page of the application
- `Example_linkedIn_job scraper_result_page.png`: The results page with visualizations
- `Example_linkedIn_job scraper_result_page02.png`: The data table with scraped job information
- `Example_linkedIn_job scraper_plot_page01.png`: Location-based job distribution chart
- `Example_linkedIn_job scraper_result_dataframe.csv`: Sample CSV output with scraped job data

These examples demonstrate the capabilities of the tool and the type of data and visualizations it can produce.
