# LinkedIn Profile Scraper

## Overview
This Python script automates the extraction of professional data from LinkedIn profiles. It uses Selenium and undetected_chromedriver to scrape information such as work experience, education, skills, certifications, and more, and saves the data to CSV files for further analysis.

## Features
- Automated Login: Opens Chrome and allows manual login to LinkedIn.
- Data Extraction: Parses the following sections from a LinkedIn profile:
Work Experience
Education
Volunteering
Publications
Languages
Soft Skills
Technical Skills
Certifications
- Data Export: Saves extracted data to CSV files in a structured format.

## Requirements
Python 3.8+
Required libraries: pip install selenium undetected-chromedriver pandas tabulate requests
Chrome Browser installed on your system.

## How to Use
Install Dependencies.
Run the Script: python linkedIN_scraping.py

## Manual Login
The script opens a Chrome window. Log in to LinkedIn manually. Navigate to the profile you want to scrape.

## Data Output
The script creates a folder named linkedin_data in the current directory.
CSV files for each section (e.g., work_experience.csv, education_history.csv) are saved here.

## File Structure
linkedIN_scraping.py: Main script for scraping LinkedIn profiles.
linkedin_data/: Output directory for CSV files.

## Output Example
The script prints formatted tables for each section and saves the data to CSV files. Example:

=== WORK EXPERIENCE ===
+----------------+----------------+----------------+
| Position       | Company        | Duration      |
+================+================+================+
| Data Scientist | Tech Corp       | 2020 - Present |
+----------------+----------------+----------------+

## Notes
Respect LinkedIn’s Terms of Service: Use this script responsibly and avoid excessive scraping.
Manual Login Required: The script does not store or automate login credentials.
Error Handling: The script includes basic error handling for missing sections or elements.