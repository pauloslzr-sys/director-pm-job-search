#!/usr/bin/env python3
"""
Director/VP Level PM Job Search Automation - Version 2
Uses web scraping instead of RSS feeds for better results
"""

import os
import json
import re
import pickle
import base64
import time
from datetime import datetime, timedelta
from typing import List, Dict
import logging

import requests
from bs4 import BeautifulSoup
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

RESUME_KEYWORDS = {
    'titles': [
        'director', 'vice president', 'vp', 'chief of staff', 'head of', 
        'senior director', 'principal'
    ],
    'pmo': [
        'pmo', 'project management office', 'portfolio management', 
        'program management', 'governance'
    ],
    'transformation': [
        'transformation', 'change management', 'digital transformation', 
        'modernization', 'strategic'
    ],
    'leadership': [
        'leadership', 'team leadership', 'executive', 'managing', 'leading'
    ],
    'skills': [
        'pmp', 'prosci', 'agile', 'scrum', 'lean', 'governance'
    ]
}

EXCLUDE_KEYWORDS = [
    'pharmaceutical', 'pharma', 'drug', 'biotech', 'clinical', 'fda'
]

TARGET_KEYWORDS = ['remote', 'fully remote', 'work from home', 'virtual']

SALARY_MINIMUM = 130000

# ============================================================================
# GOOGLE SHEETS SETUP
# ============================================================================

def get_google_sheets_client():
    """Authenticate and return Google Sheets client using OAuth 2.0"""
    try:
        creds = None
        
        # Try to get token from GitHub Secrets (base64 encoded)
        token_b64 = os.getenv('GOOGLE_OAUTH_TOKEN')
        if token_b64:
            try:
                # Decode from base64
                token_data = base64.b64decode(token_b64)
                creds = pickle.loads(token_data)
                logger.info("Loaded OAuth credentials from GitHub Secrets")
            except Exception as e:
                logger.error(f"Failed to decode token from secrets: {e}")
                return None
        else:
            logger.error("GOOGLE_OAUTH_TOKEN not found in environment")
            return None
        
        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed OAuth token")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None
        
        # Authorize gspread
        client = gspread.authorize(creds)
        logger.info("Successfully authenticated with Google Sheets API")
        return client
        
    except Exception as e:
        logger.error(f"Failed to authenticate Google Sheets: {e}")
        return None

def update_google_sheet(jobs: List[Dict], sheet_id: str):
    """Append jobs to Google Sheet"""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Prepare rows for appending
        rows = []
        for job in jobs:
            row = [
                job.get('company', ''),
                job.get('title', ''),
                job.get('url', ''),
                job.get('salary', ''),
                job.get('date_posted', datetime.now().strftime('%Y-%m-%d')),
                job.get('match_score', 0),
                job.get('description_summary', '')[:200],
                job.get('board', ''),
                job.get('keywords_matched', ''),
                '',  # Application Status (manual)
                ''   # Notes (manual)
            ]
            rows.append(row)
        
        if rows:
            sheet.append_rows(rows, value_input_option='USER_ENTERED')
            logger.info(f"✅ Added {len(rows)} jobs to Google Sheet")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update Google Sheet: {e}")
        return False

# ============================================================================
# JOB SCRAPING FUNCTIONS
# ============================================================================

def calculate_match_score(job_text: str) -> tuple:
    """Calculate match score (0-100) and matched keywords"""
    job_text_lower = job_text.lower()
    
    # Check for exclusions
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in job_text_lower:
            return 0, []
    
    # Check for remote requirement
    has_remote = any(keyword in job_text_lower for keyword in TARGET_KEYWORDS)
    if not has_remote:
        return 0, []
    
    # Calculate score based on keyword matches
    matched_keywords = []
    score = 0
    
    for category, keywords in RESUME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in job_text_lower:
                matched_keywords.append(keyword)
                if category == 'titles':
                    score += 20
                elif category == 'pmo':
                    score += 15
                elif category == 'transformation':
                    score += 12
                elif category == 'leadership':
                    score += 10
                elif category == 'skills':
                    score += 5
    
    # Cap score at 100
    score = min(score, 100)
    
    # Lower threshold - accept 15+ (was 30)
    if score < 15:
        return 0, []
    
    return score, list(set(matched_keywords))

# ============================================================================
# SCRAPER IMPLEMENTATIONS
# ============================================================================

def scrape_indeed() -> List[Dict]:
    """Scrape Indeed jobs"""
    jobs = []
    try:
        logger.info("Scraping Indeed...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Indeed job search URL
        url = (
            "https://www.indeed.com/jobs?"
            "q=director+OR+%22vice+president%22+pmo+program+management+"
            "&l=remote&jt=fulltime"
        )
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find job cards
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        for card in job_cards[:15]:
            try:
                # Extract job details
                title_elem = card.find('h2', class_='jobTitle')
                company_elem = card.find('span', class_='companyName')
                location_elem = card.find('div', class_='companyLocation')
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                url_elem = card.find('a', class_='jcs-JobTitle')
                job_url = url_elem['href'] if url_elem else ''
                
                description_elem = card.find('div', class_='job-snippet')
                description = description_elem.get_text(strip=True) if description_elem else ''
                
                job_text = f"{title} {description}".lower()
                match_score, keywords = calculate_match_score(job_text)
                
                if match_score > 0:
                    job = {
                        'company': company,
                        'title': title,
                        'url': f"https://www.indeed.com{job_url}" if job_url.startswith('/') else job_url,
                        'salary': '',
                        'match_score': match_score,
                        'description_summary': description[:200],
                        'board': 'Indeed',
                        'keywords_matched': ', '.join(keywords[:5]),
                        'date_posted': datetime.now().isoformat()
                    }
                    jobs.append(job)
            except Exception as e:
                continue
        
        logger.info(f"Indeed: Found {len(jobs)} matching jobs")
    except Exception as e:
        logger.error(f"Indeed scrape failed: {e}")
    
    return jobs

def scrape_ziprecruiter() -> List[Dict]:
    """Scrape ZipRecruiter jobs"""
    jobs = []
    try:
        logger.info("Scraping ZipRecruiter...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = (
            "https://www.ziprecruiter.com/Jobs/director+pmo/remote"
        )
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find job listings
        job_listings = soup.find_all('div', class_='job_result')
        
        for listing in job_listings[:15]:
            try:
                title_elem = listing.find('a', class_='job_link')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                company_elem = listing.find('a', class_='company_link')
                company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                
                desc_elem = listing.find('div', class_='job_summary')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                job_text = f"{title} {description}".lower()
                match_score, keywords = calculate_match_score(job_text)
                
                if match_score > 0:
                    job = {
                        'company': company,
                        'title': title,
                        'url': url,
                        'salary': '',
                        'match_score': match_score,
                        'description_summary': description[:200],
                        'board': 'ZipRecruiter',
                        'keywords_matched': ', '.join(keywords[:5]),
                        'date_posted': datetime.now().isoformat()
                    }
                    jobs.append(job)
            except Exception as e:
                continue
        
        logger.info(f"ZipRecruiter: Found {len(jobs)} matching jobs")
    except Exception as e:
        logger.error(f"ZipRecruiter scrape failed: {e}")
    
    return jobs

def scrape_linkedin() -> List[Dict]:
    """Scrape LinkedIn jobs"""
    jobs = []
    try:
        logger.info("Scraping LinkedIn...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = (
            "https://www.linkedin.com/jobs/search/?"
            "keywords=director%20pmo&location=remote&"
            "geoId=103644278&trk=public_jobs_feed-header-home"
        )
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find job cards
        job_cards = soup.find_all('div', class_='base-card')
        
        for card in job_cards[:15]:
            try:
                title_elem = card.find('h3', class_='base-search-card__title')
                company_elem = card.find('h4', class_='base-search-card__subtitle')
                link_elem = card.find('a', class_='base-card__full-link')
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                url = link_elem.get('href', '')
                
                job_text = title.lower()
                match_score, keywords = calculate_match_score(job_text)
                
                if match_score > 0:
                    job = {
                        'company': company,
                        'title': title,
                        'url': url,
                        'salary': '',
                        'match_score': match_score,
                        'description_summary': 'See LinkedIn for details',
                        'board': 'LinkedIn',
                        'keywords_matched': ', '.join(keywords[:5]),
                        'date_posted': datetime.now().isoformat()
                    }
                    jobs.append(job)
            except Exception as e:
                continue
        
        logger.info(f"LinkedIn: Found {len(jobs)} matching jobs")
    except Exception as e:
        logger.error(f"LinkedIn scrape failed: {e}")
    
    return jobs

def scrape_usajobs() -> List[Dict]:
    """Scrape USAJobs federal jobs"""
    jobs = []
    try:
        logger.info("Scraping USAJobs...")
        
        url = "https://data.usajobs.gov/api/search"
        headers = {
            'Host': 'data.usajobs.gov',
            'User-Agent': 'Mozilla/5.0'
        }
        
        params = {
            'Keyword': 'director program management pmo',
            'LocationName': 'remote',
            'ResultsPerPage': 50
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for job_item in data.get('SearchResult', {}).get('SearchResultItems', [])[:15]:
                try:
                    matched = job_item.get('MatchedObjectDescriptor', {})
                    title = matched.get('JobTitle', '')
                    company = matched.get('DepartmentName', '')
                    description = matched.get('JobSummary', '')
                    
                    job_text = f"{title} {description}".lower()
                    match_score, keywords = calculate_match_score(job_text)
                    
                    if match_score > 0:
                        apply_url = matched.get('ApplyURI', [{}])[0].get('ApplicationURI', '')
                        
                        job = {
                            'company': company,
                            'title': title,
                            'url': apply_url,
                            'salary': '',
                            'match_score': match_score,
                            'description_summary': description[:200],
                            'board': 'USAJobs',
                            'keywords_matched': ', '.join(keywords[:5]),
                            'date_posted': matched.get('PublicationStartDate', '')
                        }
                        jobs.append(job)
                except Exception as e:
                    continue
        
        logger.info(f"USAJobs: Found {len(jobs)} matching jobs")
    except Exception as e:
        logger.error(f"USAJobs scrape failed: {e}")
    
    return jobs

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def deduplicate_jobs(all_jobs: List[Dict]) -> List[Dict]:
    """Remove duplicate jobs"""
    seen = set()
    unique_jobs = []
    
    for job in all_jobs:
        key = (job['company'].lower(), job['title'].lower())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs

def sort_jobs_by_score(jobs: List[Dict]) -> List[Dict]:
    """Sort jobs by match score"""
    return sorted(jobs, key=lambda x: x['match_score'], reverse=True)

def main():
    """Main execution"""
    logger.info("🔍 Starting job search automation...")
    
    all_jobs = []
    
    # Scrape each board
    all_jobs.extend(scrape_indeed())
    time.sleep(2)  # Be respectful to servers
    
    all_jobs.extend(scrape_ziprecruiter())
    time.sleep(2)
    
    all_jobs.extend(scrape_linkedin())
    time.sleep(2)
    
    all_jobs.extend(scrape_usajobs())
    
    # Process results
    logger.info(f"📊 Total jobs found: {len(all_jobs)}")
    
    all_jobs = deduplicate_jobs(all_jobs)
    all_jobs = sort_jobs_by_score(all_jobs)
    
    logger.info(f"✨ After deduplication: {len(all_jobs)} unique jobs")
    
    # Update sheet
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    if sheet_id and all_jobs:
        success = update_google_sheet(all_jobs, sheet_id)
        if success:
            logger.info(f"🎉 Successfully updated Google Sheet with {len(all_jobs)} jobs")
        else:
            logger.warning("Failed to update Google Sheet")
    else:
        logger.warning(f"No sheet ID or no jobs to add")
    
    logger.info("✅ Job search automation completed")
    return len(all_jobs)

if __name__ == '__main__':
    main()
