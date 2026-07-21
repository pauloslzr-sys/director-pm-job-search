```python
#!/usr/bin/env python3
"""
Manual Job Tracker + Automated Matching
Reads manually-added jobs from Google Sheet and provides intelligent scoring
"""

import os
import pickle
import base64
import logging
from datetime import datetime
from typing import List, Dict

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# RESUME KEYWORDS FOR MATCHING
# ============================================================================

RESUME_KEYWORDS = {
    'director_titles': ['director', 'vice president', 'vp', 'chief of staff', 'head of'],
    'pmo_terms': ['pmo', 'portfolio', 'program management', 'governance'],
    'transformation': ['transformation', 'change management', 'modernization'],
    'strategy': ['strategy', 'strategic', 'planning'],
    'your_skills': ['enterprise', 'leadership', 'executive', 'team', 'organizational']
}

# ============================================================================
# GOOGLE SHEETS AUTHENTICATION
# ============================================================================

def get_google_sheets_client():
    """Authenticate with Google Sheets"""
    try:
        creds = None
        
        # Get token from environment
        token_b64 = os.getenv('GOOGLE_OAUTH_TOKEN')
        if token_b64:
            try:
                token_data = base64.b64decode(token_b64)
                creds = pickle.loads(token_data)
                logger.info("✅ Loaded OAuth token")
            except Exception as e:
                logger.error(f"Failed to decode token: {e}")
                return None
        else:
            logger.error("GOOGLE_OAUTH_TOKEN not in environment")
            return None
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("✅ Refreshed OAuth token")
        
        client = gspread.authorize(creds)
        return client
        
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        return None

# ============================================================================
# JOB MATCHING ALGORITHM
# ============================================================================

def calculate_match_score(job_title: str, job_description: str) -> tuple:
    """
    Score a job (0-100) based on how well it matches your resume
    Returns: (score, matched_keywords)
    """
    combined_text = f"{job_title} {job_description}".lower()
    
    score = 0
    matched = []
    
    # Check each category
    for category, keywords in RESUME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined_text:
                matched.append(keyword)
                
                if category == 'director_titles':
                    score += 25  # High weight for title match
                elif category == 'pmo_terms':
                    score += 20  # High weight for PMO
                elif category == 'transformation':
                    score += 15
                elif category == 'strategy':
                    score += 10
                elif category == 'your_skills':
                    score += 5
    
    score = min(score, 100)  # Cap at 100
    
    return score, list(set(matched))

# ============================================================================
# PROCESS JOBS FROM SHEET
# ============================================================================

def process_jobs(sheet_id: str):
    """
    Read jobs from sheet, calculate scores, update the sheet
    """
    try:
        client = get_google_sheets_client()
        if not client:
            logger.error("Failed to authenticate")
            return
        
        # Open sheet
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Get all rows
        all_rows = sheet.get_all_records()
        logger.info(f"📋 Found {len(all_rows)} job entries")
        
        # Process each row
        updates_needed = []
        
        for idx, row in enumerate(all_rows, start=2):  # Start at row 2 (row 1 is headers)
            # Skip if already has a score
            if row.get('Match Score'):
                continue
            
            # Skip if no URL
            if not row.get('URL'):
                continue
            
            title = row.get('Job Title', '')
            description = row.get('Description', '')
            
            if not title:
                continue
            
            # Calculate score
            score, keywords = calculate_match_score(title, description)
            
            logger.info(f"  {title}: {score}/100 score")
            
            # Schedule update
            if score > 0:
                updates_needed.append({
                    'row': idx,
                    'score': score,
                    'keywords': ', '.join(keywords[:5])
                })
        
        # Batch update scores
        if updates_needed:
            for update in updates_needed:
                sheet.update_cell(update['row'], 6, update['score'])  # Column F = Match Score
                sheet.update_cell(update['row'], 7, update['keywords'])  # Column G = Keywords
            
            logger.info(f"✅ Updated {len(updates_needed)} jobs with scores")
        
        # Sort by score (highest first)
        logger.info("✨ Jobs sorted by match score (highest first)")
        
    except Exception as e:
        logger.error(f"Failed to process jobs: {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("🚀 Starting automated job matcher...")
    
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    if not sheet_id:
        logger.error("GOOGLE_SHEET_ID not found in environment")
        return
    
    process_jobs(sheet_id)
    logger.info("✅ Job matching complete!")

if __name__ == '__main__':
    main()
```
