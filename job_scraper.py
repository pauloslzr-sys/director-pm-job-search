#!/usr/bin/env python3
"""
Director/VP Level PM Job Search Automation
Scrapes multiple job boards, matches against resume, pushes to Google Sheets
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict
import logging

import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import feedparser

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
        'senior director', 'principal', 'chief transformation', 'chief strategy'
    ],
    'pmo': [
        'pmo', 'project management office', 'portfolio management', 
        'program management', 'enterprise governance', 'executive governance'
    ],
    'transformation': [
        'transformation', 'change management', 'organizational change', 
        'digital transformation', 'modernization', 'strategic planning', 'adkar'
    ],
    'strategy': [
        'strategy', 'strategic planning', 'operating model', 'execution', 
        'business alignment', 'enterprise strategy', 'organizational effectiveness'
    ],
    'leadership': [
        'leadership', 'team leadership', 'executive partnership', 'coaching', 
        'vision', 'stakeholder management', 'influence', 'executive presence'
    ],
    'skills': [
        'pmp', 'prosci', 'certified change practitioner', 'agile', 'scrum', 
        'lean six sigma', 'kanban', 'jira', 'msa', 'ms project', 'governance'
    ],
    'value': [
        'cost avoidance', 'efficiency', 'risk management', 'adoption', 
        'execution', 'delivery', 'resource planning', 'portfolio optimization'
    ]
}

EXCLUDE_KEYWORDS = [
    'pharmaceutical', 'pharma', 'drug', 'biotech', 'clinical trial', 'fda approval'
]

TARGET_KEYWORDS = [
    'remote', 'fully remote', 'work from home', 'virtual', 'distributed'
]

SALARY_MINIMUM = 130000

# ============================================================================
# GOOGLE SHEETS SETUP
# ============================================================================

def get_google_sheets_client():
    """Authenticate and return Google Sheets client"""
    try:
        # Get credentials from environment variable (GitHub Secrets)
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        if not creds_json:
            logger.error("GOOGLE_CREDENTIALS not found in environment")
            return None
        
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict)
        client = gspread.authorize(creds)
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
                job.get('date_posted', ''),
                job.get('match_score', ''),
                job.get('description_summary', ''),
                job.get('board', ''),
                job.get('keywords_matched', ''),
                '',  # Application Status (manual)
                ''   # Notes (manual)
            ]
            rows.append(row)
        
        if rows:
            sheet.append_rows(rows, value_input_option='USER_ENTERED')
            logger.info(f"Added {len(rows)} jobs to Google Sheet")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update Google Sheet: {e}")
        return False

# ============================================================================
# JOB SCRAPING FUNCTIONS
# ============================================================================

class JobBoard:
    """Base class for job boards"""
    
    def __init__(self, name: str):
        self.name = name
        self.jobs = []
    
    def scrape(self) -> List[Dict]:
        raise NotImplementedError
    
    def calculate_match_score(self, job_text: str) -> tuple:
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
                        score += 15
                    elif category == 'strategy':
                        score += 10
                    elif category == 'leadership':
                        score += 10
                    elif category == 'skills':
                        score += 5
                    elif category == 'value':
                        score += 5
        
        # Cap score at 100
        score = min(score, 100)
        
        # Only return jobs with 30+ score
        if score < 30:
            return 0, []
        
        return score, list(set(matched_keywords))


class IndeedBoard(JobBoard):
    """Indeed job scraper"""
    
    def scrape(self) -> List[Dict]:
        try:
            # Using Indeed's RSS feed for remote PM jobs
            rss_url = (
                "https://www.indeed.com/rss?q="
                "(director+OR+%22vice+president%22+OR+%22chief+of+staff%22)+"
                "(pmo+OR+%22program+management%22+OR+%22project+management%22)+"
                "%22remote%22&l=&sort=date"
            )
            
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:15]:  # Limit to 15 most recent
                job_text = f"{entry.title} {entry.summary}".lower()
                match_score, keywords = self.calculate_match_score(job_text)
                
                if match_score > 0:
                    job = {
                        'company': entry.get('company', 'Unknown'),
                        'title': entry.title,
                        'url': entry.link,
                        'salary': extract_salary(entry.summary),
                        'date_posted': entry.get('published', datetime.now().isoformat()),
                        'match_score': match_score,
                        'description_summary': entry.summary[:200],
                        'board': 'Indeed',
                        'keywords_matched': ', '.join(keywords[:5])
                    }
                    self.jobs.append(job)
            
            logger.info(f"Indeed: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"Indeed scrape failed: {e}")
        
        return self.jobs


class ZipRecruiterBoard(JobBoard):
    """ZipRecruiter job scraper"""
    
    def scrape(self) -> List[Dict]:
        try:
            params = {
                'search': 'director OR "vice president" pmo OR "program management" remote',
                'location': 'remote',
                'days': '7'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # ZipRecruiter RSS feed
            rss_url = (
                "https://www.ziprecruiter.com/rss?"
                "search=director+pmo+remote&location=remote&days_ago=7"
            )
            
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:15]:
                job_text = f"{entry.title} {entry.summary}".lower()
                match_score, keywords = self.calculate_match_score(job_text)
                
                if match_score > 0:
                    job = {
                        'company': entry.get('author', 'Unknown'),
                        'title': entry.title,
                        'url': entry.link,
                        'salary': extract_salary(entry.summary),
                        'date_posted': entry.get('published', datetime.now().isoformat()),
                        'match_score': match_score,
                        'description_summary': entry.summary[:200],
                        'board': 'ZipRecruiter',
                        'keywords_matched': ', '.join(keywords[:5])
                    }
                    self.jobs.append(job)
            
            logger.info(f"ZipRecruiter: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"ZipRecruiter scrape failed: {e}")
        
        return self.jobs


class LinkedInBoard(JobBoard):
    """LinkedIn job scraper (RSS feed only - more reliable)"""
    
    def scrape(self) -> List[Dict]:
        try:
            # LinkedIn RSS feed for saved search
            rss_url = (
                "https://www.linkedin.com/jobs/feed/?keywords="
                "(director%20OR%20%22vice%20president%22)%20"
                "(pmo%20OR%20%22program%20management%22)%20"
                "&geoId=103644278&trk=public_jobs_feed-header-home"
            )
            
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:10]:
                job_text = f"{entry.title} {entry.summary}".lower()
                match_score, keywords = self.calculate_match_score(job_text)
                
                if match_score > 0:
                    # Extract company from description
                    company = extract_company_from_linkedin(entry.summary)
                    
                    job = {
                        'company': company,
                        'title': entry.title,
                        'url': entry.link,
                        'salary': extract_salary(entry.summary),
                        'date_posted': entry.get('published', datetime.now().isoformat()),
                        'match_score': match_score,
                        'description_summary': entry.summary[:200],
                        'board': 'LinkedIn',
                        'keywords_matched': ', '.join(keywords[:5])
                    }
                    self.jobs.append(job)
            
            logger.info(f"LinkedIn: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"LinkedIn scrape failed: {e}")
        
        return self.jobs


class PMIJobBoard(JobBoard):
    """PMI Career Center"""
    
    def scrape(self) -> List[Dict]:
        try:
            url = "https://www.pmi.org/careers/career-center/job-board"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Note: PMI structure may vary - adjust selectors as needed
            job_listings = soup.find_all('div', class_='job-listing')
            
            for listing in job_listings[:20]:
                title_elem = listing.find('a', class_='job-title')
                company_elem = listing.find('span', class_='company-name')
                
                if title_elem and company_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    description = listing.find('div', class_='description')
                    desc_text = description.get_text(strip=True) if description else ""
                    
                    job_text = f"{title} {desc_text}".lower()
                    match_score, keywords = self.calculate_match_score(job_text)
                    
                    if match_score > 0:
                        job = {
                            'company': company,
                            'title': title,
                            'url': f"https://www.pmi.org{url}" if url.startswith('/') else url,
                            'salary': extract_salary(desc_text),
                            'date_posted': datetime.now().isoformat(),
                            'match_score': match_score,
                            'description_summary': desc_text[:200],
                            'board': 'PMI Job Board',
                            'keywords_matched': ', '.join(keywords[:5])
                        }
                        self.jobs.append(job)
            
            logger.info(f"PMI: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"PMI scrape failed: {e}")
        
        return self.jobs


class USAJobsBoard(JobBoard):
    """USAJobs federal government jobs"""
    
    def scrape(self) -> List[Dict]:
        try:
            # USAJobs API
            url = "https://data.usajobs.gov/api/search"
            headers = {
                'Host': 'data.usajobs.gov',
                'User-Agent': 'Mozilla/5.0',
                'Authorization-Key': os.getenv('USAJOBS_API_KEY', 'test')  # Free API key from USAJobs
            }
            
            params = {
                'Keyword': 'director program management OR pmo',
                'LocationName': 'remote',
                'ResultsPerPage': 100,
                'WhoMayApply': 'all'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for job in data.get('SearchResult', {}).get('SearchResultItems', [])[:20]:
                    matched_job = job.get('MatchedObjectDescriptor', {})
                    title = matched_job.get('JobTitle', '')
                    company = matched_job.get('DepartmentName', '')
                    desc = matched_job.get('JobSummary', '')
                    
                    job_text = f"{title} {desc}".lower()
                    match_score, keywords = self.calculate_match_score(job_text)
                    
                    if match_score > 0:
                        salary_info = matched_job.get('PositionRemuneration', [{}])[0]
                        salary = salary_info.get('RangeTo', '')
                        
                        job_obj = {
                            'company': company,
                            'title': title,
                            'url': matched_job.get('ApplyURI', {}).get('ApplicationURI', ''),
                            'salary': f"${salary}" if salary else '',
                            'date_posted': matched_job.get('PublicationStartDate', ''),
                            'match_score': match_score,
                            'description_summary': desc[:200],
                            'board': 'USAJobs',
                            'keywords_matched': ', '.join(keywords[:5])
                        }
                        self.jobs.append(job_obj)
                
                logger.info(f"USAJobs: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"USAJobs scrape failed: {e}")
        
        return self.jobs


class IdealistBoard(JobBoard):
    """Idealist.org nonprofit job board"""
    
    def scrape(self) -> List[Dict]:
        try:
            url = "https://www.idealist.org/en/jobs"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            params = {
                'q': 'director OR "program management" OR pmo',
                'location': 'remote',
                'type': 'full-time'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            job_cards = soup.find_all('div', class_='posting')
            
            for card in job_cards[:20]:
                title_elem = card.find('a', class_='job-title')
                org_elem = card.find('span', class_='organization-name')
                
                if title_elem and org_elem:
                    title = title_elem.get_text(strip=True)
                    company = org_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    
                    job_text = title.lower()
                    match_score, keywords = self.calculate_match_score(job_text)
                    
                    if match_score > 0:
                        job = {
                            'company': company,
                            'title': title,
                            'url': f"https://www.idealist.org{url}" if url.startswith('/') else url,
                            'salary': '',
                            'date_posted': datetime.now().isoformat(),
                            'match_score': match_score,
                            'description_summary': 'See Idealist.org for details',
                            'board': 'Idealist.org',
                            'keywords_matched': ', '.join(keywords[:5])
                        }
                        self.jobs.append(job)
            
            logger.info(f"Idealist: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"Idealist scrape failed: {e}")
        
        return self.jobs


class BuiltInBoard(JobBoard):
    """Built In startup jobs"""
    
    def scrape(self) -> List[Dict]:
        try:
            url = "https://builtin.com/jobs"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            params = {
                'q': 'director OR "program management" OR pmo',
                'location': 'remote'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            job_cards = soup.find_all('div', class_='job-card')
            
            for card in job_cards[:20]:
                title_elem = card.find('a', class_='job-link')
                company_elem = card.find('span', class_='company')
                
                if title_elem and company_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    
                    job_text = title.lower()
                    match_score, keywords = self.calculate_match_score(job_text)
                    
                    if match_score > 0:
                        job = {
                            'company': company,
                            'title': title,
                            'url': url,
                            'salary': '',
                            'date_posted': datetime.now().isoformat(),
                            'match_score': match_score,
                            'description_summary': 'See Built In for details',
                            'board': 'Built In',
                            'keywords_matched': ', '.join(keywords[:5])
                        }
                        self.jobs.append(job)
            
            logger.info(f"Built In: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"Built In scrape failed: {e}")
        
        return self.jobs


class FlexjobsBoard(JobBoard):
    """Flexjobs (requires subscription, but RSS feed available to members)"""
    
    def scrape(self) -> List[Dict]:
        try:
            # Flexjobs has limited free access - using public job feed
            url = "https://www.flexjobs.com/jobs"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            params = {
                'search': 'director pmo program management',
                'type': 'remote'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            job_listings = soup.find_all('div', class_='job-listing')
            
            for listing in job_listings[:15]:
                title_elem = listing.find('a', class_='title')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    
                    job_text = title.lower()
                    match_score, keywords = self.calculate_match_score(job_text)
                    
                    if match_score > 0:
                        job = {
                            'company': listing.find('span', class_='company').get_text(strip=True) if listing.find('span', class_='company') else 'Unknown',
                            'title': title,
                            'url': f"https://www.flexjobs.com{url}" if url.startswith('/') else url,
                            'salary': '',
                            'date_posted': datetime.now().isoformat(),
                            'match_score': match_score,
                            'description_summary': 'Flexjobs member access required',
                            'board': 'Flexjobs',
                            'keywords_matched': ', '.join(keywords[:5])
                        }
                        self.jobs.append(job)
            
            logger.info(f"Flexjobs: Found {len(self.jobs)} matching jobs")
        except Exception as e:
            logger.error(f"Flexjobs scrape failed: {e}")
        
        return self.jobs


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_salary(text: str) -> str:
    """Extract salary information from text"""
    try:
        # Look for salary patterns like $130,000 or $130K
        salary_patterns = [
            r'\$[\d,]+(?:k|K)?(?:\s*-\s*\$[\d,]+(?:k|K)?)?',
            r'[\d,]+\s*(?:to|-)\s*[\d,]+\s*(?:year|annually|per year)',
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return ''
    except:
        return ''


def extract_company_from_linkedin(text: str) -> str:
    """Extract company name from LinkedIn job description"""
    try:
        # LinkedIn format typically has company near the beginning
        lines = text.split('\n')
        for line in lines[:5]:
            if 'company' not in line.lower():
                return line.strip()
        return 'Unknown'
    except:
        return 'Unknown'


def deduplicate_jobs(all_jobs: List[Dict]) -> List[Dict]:
    """Remove duplicate jobs based on title and company"""
    seen = set()
    unique_jobs = []
    
    for job in all_jobs:
        key = (job['company'].lower(), job['title'].lower())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs


def sort_jobs_by_score(jobs: List[Dict]) -> List[Dict]:
    """Sort jobs by match score (highest first)"""
    return sorted(jobs, key=lambda x: x['match_score'], reverse=True)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    logger.info("Starting job search automation...")
    
    all_jobs = []
    
    # Initialize job boards
    boards = [
        IndeedBoard('Indeed'),
        ZipRecruiterBoard('ZipRecruiter'),
        LinkedInBoard('LinkedIn'),
        PMIJobBoard('PMI Job Board'),
        USAJobsBoard('USAJobs'),
        IdealistBoard('Idealist.org'),
        BuiltInBoard('Built In'),
        FlexjobsBoard('Flexjobs'),
    ]
    
    # Scrape each board
    for board in boards:
        logger.info(f"Scraping {board.name}...")
        try:
            jobs = board.scrape()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Error scraping {board.name}: {e}")
    
    # Process results
    logger.info(f"Total jobs found: {len(all_jobs)}")
    
    all_jobs = deduplicate_jobs(all_jobs)
    all_jobs = sort_jobs_by_score(all_jobs)
    
    logger.info(f"After deduplication: {len(all_jobs)} unique jobs")
    
    # Filter by salary if provided
    filtered_jobs = []
    for job in all_jobs:
        salary_str = job.get('salary', '')
        if salary_str:
            try:
                # Extract numeric salary
                salary_num = int(re.search(r'[\d,]+', salary_str.replace(',', '')).group())
                if salary_num >= SALARY_MINIMUM:
                    filtered_jobs.append(job)
            except:
                filtered_jobs.append(job)  # Include if we can't parse
        else:
            filtered_jobs.append(job)  # Include if no salary listed
    
    logger.info(f"After salary filter (${SALARY_MINIMUM}+): {len(filtered_jobs)} jobs")
    
    # Update Google Sheet
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    if sheet_id and filtered_jobs:
        success = update_google_sheet(filtered_jobs, sheet_id)
        if success:
            logger.info(f"Successfully updated Google Sheet with {len(filtered_jobs)} jobs")
        else:
            logger.warning("Failed to update Google Sheet")
    else:
        logger.warning(f"No sheet ID provided or no jobs to add (jobs: {len(filtered_jobs)})")
    
    logger.info("Job search automation completed")
    return len(filtered_jobs)


if __name__ == '__main__':
    main()
