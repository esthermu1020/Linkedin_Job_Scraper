from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import json
import pandas as pd
import threading
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re
import base64
from io import BytesIO
import numpy as np

app = Flask(__name__, static_url_path='', static_folder='static')

# Store scraping results
scraping_results = {
    "status": "idle",  # idle, running, completed, error
    "message": "",
    "job_count": 0,
    "jobs": [],
    "cloud_mentions": {
        "aws": 0,
        "azure": 0,
        "gcp": 0,
        "alibaba": 0
    },
    "log_file": None,
    "log_entries": []
}

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index_fixed.html')

@app.route('/api/check_status')
def api_check_status():
    """API endpoint to check the status of the scraping process"""
    # Add debug information
    print("API check_status called")
    print(f"Current status: {scraping_results['status']}")
    print(f"Job count: {scraping_results['job_count']}")
    print(f"Jobs type: {type(scraping_results['jobs'])}")
    if isinstance(scraping_results['jobs'], list):
        print(f"Jobs list length: {len(scraping_results['jobs'])}")
    return jsonify(scraping_results)

@app.route('/check_status')
def check_status():
    """Check the status of the scraping process"""
    # Add the log file content if available
    if "log_file" in scraping_results and scraping_results["log_file"]:
        try:
            with open(scraping_results["log_file"], 'r') as f:
                log_content = f.read()
                scraping_results["log_content"] = log_content
        except Exception as e:
            scraping_results["log_error"] = str(e)
    
    return jsonify(scraping_results)

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start the scraping process with the provided parameters"""
    if scraping_results["status"] == "running":
        return jsonify({"status": "error", "message": "A scraping job is already running"})
    
    # Reset results
    scraping_results["status"] = "running"
    scraping_results["message"] = "Starting job scraping..."
    scraping_results["job_count"] = 0
    scraping_results["jobs"] = []
    scraping_results["cloud_mentions"] = {"aws": 0, "azure": 0, "gcp": 0, "alibaba": 0}
    scraping_results["log_entries"] = []
    
    # Get parameters from request
    data = request.json
    search_url = data.get('search_url', '')
    max_jobs = data.get('max_jobs', 10)
    manual_job_ids = data.get('manual_job_ids', '')
    start_position = int(data.get('start_position', 0))  # Ensure start_position is an integer
    
    # Start scraping in a separate thread
    thread = threading.Thread(target=run_scraper, args=(search_url, max_jobs, manual_job_ids, start_position))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "message": "Scraping started"})

def run_scraper(search_url, max_jobs, manual_job_ids='', start_position=0):
    """Run the LinkedIn scraper with the provided parameters"""
    try:
        # Import the connector module
        from connector import LinkedInConnector
        
        # Create a log file
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"linkedin_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        scraping_results["log_file"] = log_file
        
        # Initialize the connector with increased timeout for web UI
        connector = LinkedInConnector(
            search_url=search_url,
            max_jobs=max_jobs,
            start_position=start_position,  # Pass the start_position parameter
            manual_job_ids=manual_job_ids,
            log_file=log_file,
            headless=False  # Use non-headless mode for better reliability
        )
        
        # Run the scraper
        job_results = connector.run()
        
        # Debug information
        print(f"Type of job_results: {type(job_results)}")
        print(f"Length of job_results: {len(job_results) if hasattr(job_results, '__len__') else 'N/A'}")
        
        # Enhanced job results handling
        if isinstance(job_results, dict) and "jobs" in job_results:
            # If job_results is a dictionary with a "jobs" key, use that
            print("Using job_results['jobs'] as the actual job data")
            actual_jobs = job_results["jobs"]
            scraping_results["status"] = "completed"
            scraping_results["message"] = f"Completed scraping {len(actual_jobs)} jobs"
            scraping_results["job_count"] = len(actual_jobs)
            scraping_results["jobs"] = actual_jobs
        elif isinstance(job_results, list) and len(job_results) > 0:
            # If job_results is a non-empty list, use it directly
            print(f"Using job_results list directly as job data (length: {len(job_results)})")
            scraping_results["status"] = "completed"
            scraping_results["message"] = f"Completed scraping {len(job_results)} jobs"
            scraping_results["job_count"] = len(job_results)
            scraping_results["jobs"] = job_results
        else:
            # Handle empty or invalid results
            print("Warning: Job results appear to be empty or invalid")
            # Check if we can extract any useful information
            if hasattr(job_results, '__len__'):
                print(f"Job results has length attribute: {len(job_results)}")
                if len(job_results) > 0:
                    print("Non-zero length detected, attempting to use results anyway")
                    scraping_results["status"] = "completed"
                    scraping_results["message"] = f"Completed scraping {len(job_results)} jobs"
                    scraping_results["job_count"] = len(job_results)
                    scraping_results["jobs"] = job_results
                else:
                    print("Zero length detected, marking as empty results")
                    scraping_results["status"] = "completed"
                    scraping_results["message"] = "No jobs found matching your criteria"
                    scraping_results["job_count"] = 0
                    scraping_results["jobs"] = []
            else:
                print("No length attribute, treating as empty results")
                scraping_results["status"] = "completed"
                scraping_results["message"] = "No jobs found matching your criteria"
                scraping_results["job_count"] = 0
                scraping_results["jobs"] = []
        
        # Count cloud provider mentions
        jobs_to_process = scraping_results["jobs"]
        print(f"Processing {len(jobs_to_process) if hasattr(jobs_to_process, '__len__') else 'unknown'} jobs for cloud mentions")
        
        for job in jobs_to_process:
            # Check if job is a dictionary before using get()
            if isinstance(job, dict):
                description = job.get('description', '').lower() if job.get('description') else ''
                
                # Check for AWS/Amazon cloud services
                if 'aws' in description or 'amazon' in description or \
                   any(keyword in description for keyword in [' ec2 ', ' s3 ', 'lambda', 'dynamodb',  'cloudwatch', 'sagemaker',
                                                            'cloudfront', 'bedrock', 'redshift', 'cloudformation',]):
                    scraping_results["cloud_mentions"]["aws"] += 1
                
                # Check for Azure cloud services
                if 'azure' in description or 'microsoft azure' in description or \
                   any(keyword in description for keyword in ['azure vm', 'azure functions', 'azure storage', 
                                                            'cosmos db', 'azure sql', 'azure devops', 
                                                            'azure kubernetes', 'aks', 'azure active directory',
                                                            'azure logic apps', 'azure app service']):
                    scraping_results["cloud_mentions"]["azure"] += 1
                
                # Check for Google Cloud Platform services
                if 'gcp' in description or 'google cloud' in description or \
                   any(keyword in description for keyword in ['bigquery', 'dataflow', 'cloud spanner', 
                                                            'looker', 'cloud run', 'dataproc', 'pub/sub']):
                    scraping_results["cloud_mentions"]["gcp"] += 1
                
                # Check for Alibaba Cloud services
                if 'alibaba' in description or 'alicloud' in description or 'alipay' in description or '阿里' in description or \
                   any(keyword in description for keyword in ['maxcompute', 'tablestore', 'polardb', 'datav']):
                    scraping_results["cloud_mentions"]["alibaba"] += 1
            elif isinstance(job, str):
                # If job is a string, log the issue and continue
                print(f"Warning: Received string instead of job dictionary: {job[:100]}...")
                continue
            else:
                print(f"Warning: Unexpected job type: {type(job)}")
                continue
    
    except Exception as e:
        scraping_results["status"] = "error"
        scraping_results["message"] = f"Error: {str(e)}"
        print(f"Error in scraper thread: {str(e)}")

@app.route('/download_results')
def download_results():
    """Download the scraping results as a CSV file"""
    print("Download results requested")
    print(f"Current status: {scraping_results['status']}")
    print(f"Job count: {scraping_results['job_count']}")
    print(f"Jobs type: {type(scraping_results['jobs'])}")
    
    if scraping_results["status"] != "completed":
        return jsonify({"status": "error", "message": "No completed scraping results available for download"})
    
    if scraping_results["job_count"] == 0:
        return jsonify({"status": "error", "message": "No job data available for download"})
    
    try:
        # Create a DataFrame from the results
        df = pd.DataFrame(scraping_results["jobs"])
        print(f"Created DataFrame with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # Save to a temporary CSV file
        temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_results.csv')
        df.to_csv(temp_file, index=False)
        print(f"Saved data to {temp_file}")
        
        # Return the file for download
        return send_file(
            temp_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"linkedin_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    
    except Exception as e:
        print(f"Error generating CSV: {str(e)}")
        return jsonify({"status": "error", "message": f"Error generating CSV: {str(e)}"})

@app.route('/api/generate_analysis')
def generate_analysis():
    """Generate analysis visualizations from the scraped job data"""
    print("Generating analysis...")
    if scraping_results["status"] != "completed" or len(scraping_results["jobs"]) == 0:
        print("No results available for analysis")
        return jsonify({"status": "error", "message": "No results available for analysis"})
    
    try:
        # Create a DataFrame from the results
        df = pd.DataFrame(scraping_results["jobs"])
        print(f"Created DataFrame with {len(df)} rows")
        
        # Analysis results container
        analysis_results = {
            "job_count_by_company": {},
            "job_count_by_location": {},
            "common_skills": {},
            "raw_data": {}
        }
        
        # 1. Job count by company
        if 'company' in df.columns:
            company_counts = df['company'].value_counts().head(10).to_dict()
            analysis_results["job_count_by_company"] = company_counts
            print(f"Found {len(company_counts)} companies")
        else:
            print("No 'company' column found in job data")
        
        # 2. Job count by location
        if 'location' in df.columns:
            location_counts = df['location'].value_counts().head(10).to_dict()
            analysis_results["job_count_by_location"] = location_counts
            print(f"Found {len(location_counts)} locations")
        else:
            print("No 'location' column found in job data")
        
        # 3. Extract common skills from job descriptions
        skill_keywords = ['aws', 'azure', 'gcp', 'alibaba', 'python', 'java', 'javascript', 'sql', 'redshift', 'bigquery',
                           'redshift', 'snowflake', 'spark', 'hadoop', 'docker', 'kubernetes', 'terraform','datav', 'databricks',
                           'claude', 'llama', 'bedrock', 'sagemaker', 'gpt', 'chatgpt', 'openai', 'deep learning', 'vertex', 'openai',
                           'elasticsearch', 'kibana', 'prometheus', 'grafana', 'splunk', 'tableau', 'power bi', 'looker', 'power bi',
                           'maxcompute', 'tablestore', 'polardb', 'dataworks', 'data lake', 'glue']
        
        # Check if description column exists
        if 'description' in df.columns:
            # Combine all job descriptions
            all_text = ' '.join(df['description'].fillna('').astype(str).tolist()).lower()
            
            # Count occurrences of each skill
            skill_counts = {}
            for skill in skill_keywords:
                count = len(re.findall(r'\b' + re.escape(skill) + r'\b', all_text))
                if count > 0:
                    skill_counts[skill] = count
            
            # Sort by count
            sorted_skills = dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True))
            analysis_results["common_skills"] = sorted_skills
            
            # 4. Prepare raw data for frontend visualization
            # Instead of generating images on the backend, send the raw data to the frontend
            
            # For word frequency data
            word_freq = {}
            words = re.findall(r'\b[a-zA-Z]{3,15}\b', all_text)
            word_counts = Counter(words)
            # Filter out common stop words
            stop_words = ['the', 'and', 'for', 'with', 'you', 'will', 'your', 'this', 'that', 'our', 'from', 'have', 'are']
            for word, count in word_counts.most_common(100):
                if word not in stop_words and len(word) > 2:
                    word_freq[word] = count
            
            analysis_results["raw_data"]["word_frequencies"] = word_freq
            
            # For company-specific data
            company_data = {}
            if len(company_counts) > 0:
                # Convert dict_keys to list before slicing
                top_companies = list(company_counts.keys())[:5]  # Top 5 companies
                for company in top_companies:
                    company_jobs = df[df['company'] == company]
                    if not company_jobs.empty and 'description' in company_jobs.columns:
                        company_text = ' '.join(company_jobs['description'].fillna('').astype(str).tolist()).lower()
                        company_words = re.findall(r'\b[a-zA-Z]{3,15}\b', company_text)
                        company_word_counts = Counter(company_words)
                        company_word_freq = {}
                        for word, count in company_word_counts.most_common(100):
                            if word not in stop_words:
                                company_word_freq[word] = count
                        company_data[company] = company_word_freq
            
            analysis_results["raw_data"]["company_word_frequencies"] = company_data
            
        else:
            print("No 'description' column found in job data")
        
        return jsonify({"status": "success", "data": analysis_results})
    
    except Exception as e:
        print(f"Error generating analysis: {str(e)}")
        return jsonify({"status": "error", "message": f"Error generating analysis: {str(e)}"})

if __name__ == '__main__':
    # Check if the template directory exists
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # Copy the UI template if it doesn't exist
    template_dest = os.path.join(template_dir, 'index_fixed.html')
    if not os.path.exists(template_dest):
        # Try to find the original template
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'index.html')
        if os.path.exists(html_path):
            print(f"Using original template from {html_path}")
            with open(html_path, 'r') as f:
                html_content = f.read()
            
            with open(template_dest, 'w') as f:
                f.write(html_content)
            print("Template file copied successfully")
        else:
            print(f"Warning: Original UI template file not found at {html_path}")
    
    # Try different ports if the default ones are in use
    for port in range(5001, 5010):
        try:
            print(f"Starting LinkedIn Job Scraper with dark theme on port {port}")
            print(f"Access the application at http://localhost:{port}")
            app.run(debug=True, port=port)
            break
        except OSError as e:
            print(f"Port {port} is in use, trying next port...")
            continue
