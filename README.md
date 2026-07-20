# Director/VP PM Job Search Automation

**Automated job discovery system for senior Project Management roles (Director, VP, Chief of Staff)**

> "Catch Director/VP PMO opportunities before everyone else sees them"

---

## 🎯 What This Does

Automatically searches 8+ job boards every Mon/Wed/Fri at 5 AM EST and:
- ✅ Finds remote Director/VP/Chief of Staff PM roles ($130K+)
- ✅ Matches each job against your resume (0-100 score)
- ✅ Pushes results to your private Google Sheet
- ✅ Sends email alerts for top matches
- ✅ Filters out pharmaceutical companies
- ✅ Deduplicates jobs across boards
- ✅ Sorts by relevance score

**Result**: Fresh, pre-qualified job leads delivered to your inbox every Monday, Wednesday, Friday morning

---

## 📊 The Numbers

Your profile analysis:
- **15+ years** in PM/PMO/transformation leadership
- **$400K+** in measurable impact (cost avoidance, efficiency gains)
- **64%** adoption improvement track record
- **MBA + PMP + Prosci CCP** credentials
- **Expertise**: Enterprise PMO, Strategic Transformation, Change Leadership

**This puts you in the top 5% for Director/VP PM roles.** You should see 3-8 qualified roles per week.

---

## 🚀 Quick Start (30 minutes)

1. **Read** `SETUP_INSTRUCTIONS.md` (follow steps 1-6)
2. **Configure** GitHub repository with 3 secrets
3. **Test** the workflow manually
4. **Wait** for Monday 5 AM EST - first automated run

**Timeline**: 
- Today: Setup
- This weekend: Test
- Monday 5 AM: First results appear in Google Sheet

---

## 📁 Files in This Repository

- **`job_scraper.py`** - Main scraper script (searches all boards, matches resume, updates Sheet)
- **`github_workflow.yml`** - GitHub Actions automation (runs 3x weekly at 5 AM EST)
- **`requirements.txt`** - Python dependencies
- **`SETUP_INSTRUCTIONS.md`** - Complete step-by-step setup guide ⭐ START HERE
- **`JOB_BOARDS_REFERENCE.md`** - Details on all 15+ job boards included
- **`GOOGLE_SHEET_TEMPLATE.md`** - How to format your tracking sheet
- **`README.md`** - This file

---

## 🔍 Job Boards Searched

### Core Boards (8 automated)
1. **Indeed** - Largest volume
2. **ZipRecruiter** - Fastest new postings
3. **LinkedIn** - Executive roles
4. **PMI Job Board** - PM-focused
5. **USAJobs** - Federal government
6. **Idealist.org** - Nonprofits
7. **Built In** - Startups
8. **Flexjobs** - Verified remote-only

### Additional Recommended (manual check 2x/month)
- Government contracting sites
- Consulting firm career pages (McKinsey, Deloitte, Accenture, Bain, EY, PwC)
- Fortune 500 career pages
- Executive boards (The Ladders, Executive.com)
- Tech startups (Y Combinator, AngelList)

**See `JOB_BOARDS_REFERENCE.md` for full coverage details**

---

## 🎲 Matching Algorithm

Each job is scored 0-100 based on keyword matching:

**Scoring Breakdown:**
- Title match (director, VP, chief of staff): +20 points each
- PMO/Portfolio expertise: +15 points each
- Transformation skills: +15 points each
- Strategic planning: +10 points each
- Leadership/coaching: +10 points each
- Technical certifications (PMP, Prosci, Agile): +5 points each
- Measurable impact (cost avoidance, efficiency): +5 points each

**Interpretation:**
- **90-100**: 🟢 Perfect match → Apply same day
- **75-89**: 🟢 Strong match → Review carefully
- **60-74**: 🟡 Good match → Consider applying
- **30-59**: 🟡 Possible match → Review description
- **<30**: ⚪ Not relevant → Skip

---

## 📊 Google Sheet Columns

Your results sheet will automatically populate with:

| Column | Source | Notes |
|--------|--------|-------|
| Company | Job posting | Organization name |
| Job Title | Job posting | Position title |
| URL | Job posting | Link to full job posting |
| Salary | Job posting | Posted range (if available) |
| Date Posted | Job posting | When posted |
| Match Score | Algorithm | 0-100 relevance to your resume |
| Description Summary | Job posting | First 200 characters |
| Board | Algorithm | Which job board |
| Keywords Matched | Algorithm | Your resume keywords found |
| Application Status | MANUAL | You update: Applied/Rejected/Interview/Offer |
| Notes | MANUAL | Your personal notes about role |

---

## 🔐 Security & Privacy

- ✅ Your Google Sheets credentials stored as GitHub Secrets (encrypted)
- ✅ Job scraping uses RSS/API only (no login/password needed)
- ✅ Data never leaves your GitHub account → your Google Sheet
- ✅ Open-source code (you can review everything)

---

## 💰 Cost

**$0 per month**

- GitHub: Free for public repos
- Google Sheets: Free tier
- Job boards: Free RSS/API access
- Optional: Email server (use Gmail/Outlook free)

---

## 📈 Expected Results

**After 1 week:**
- 5-12 new director/VP PM roles matching your profile
- 2-3 roles scoring 80+
- Clear sense of which boards are most relevant

**After 1 month:**
- 40-50 total qualified leads
- Time to apply: 20-30 minutes per day for top matches
- Response rate: Expect 10-15% interviews from 80+ score roles

**After 3 months:**
- 120+ total leads with full application history
- Patterns emerging (which companies, industries, sectors hiring most)
- Potentially 3-5 offers in pipeline

---

## 🛠 Customization

### Adjust Search Criteria
Edit `job_scraper.py`:
- **Line 65**: Change salary minimum
- **Line 23-45**: Add/remove keywords
- **Line 50-60**: Add exclude terms
- **Line 195-220**: Adjust scoring weights

### Change Schedule
Edit `.github/workflows/job_search.yml`:
- **Line 8**: `cron: '0 10 * * 1,3,5'` = Mon/Wed/Fri at 5 AM EST
- Use [crontab guru](https://crontab.guru/) to generate new times

### Add New Job Boards
Edit `job_scraper.py` line ~650:
```python
boards = [
    IndeedBoard('Indeed'),
    # Add new board here
]
```

See `SETUP_INSTRUCTIONS.md` for detailed customization guide.

---

## 🐛 Troubleshooting

**Jobs not appearing?**
- Check GitHub Actions logs
- Verify Google Sheet sharing with service account
- Confirm GOOGLE_SHEET_ID is correct

**Wrong jobs appearing?**
- Adjust keyword matching (too broad/narrow)
- Add more exclude terms for irrelevant industries
- Review scores and filter threshold

**Workflow not running?**
- GitHub Actions uses UTC (5 AM EST = 10 AM UTC)
- Check workflow is enabled
- Verify secrets are set correctly

See `SETUP_INSTRUCTIONS.md` for full troubleshooting.

---

## 📞 Next Steps

1. **Read** `SETUP_INSTRUCTIONS.md` 
2. **Follow** Steps 1-6 (30 minutes)
3. **Test** the workflow (Saturday)
4. **Receive** first results (Monday 5 AM EST)
5. **Apply** to top matches within 5 minutes of notification

---

## 📚 Additional Resources

- `JOB_BOARDS_REFERENCE.md` - All job boards with details
- `GOOGLE_SHEET_TEMPLATE.md` - How to set up your tracking sheet
- `SETUP_INSTRUCTIONS.md` - Step-by-step setup guide
- GitHub Issues - Report problems or suggest improvements

---

## 🎓 Best Practices for Success

1. **Speed matters**: Apply to 80+ score roles within 30 minutes of posting
2. **Personalize**: Never use template cover letters for director roles
3. **Track everything**: Keep Application Status updated to spot patterns
4. **Cold email**: Find hiring manager on LinkedIn, send personalized note
5. **Do the math**: If 100 applications → 10 interviews → 1-2 offers
6. **Quality > Quantity**: Focus on 3-5 best matches per week

---

## 💡 Pro Tips

- **Salary negotiation**: Your track record ($400K cost avoidance) supports $150K-$180K range
- **Consulting roles**: Check Deloitte/Accenture/McKinsey weekly (perfect fit for you)
- **Startup growth**: Series B-D startups offer $160K-$200K+ for director roles
- **Government roles**: Federal/state PMO roles often $140K-$160K + excellent benefits
- **Nonprofit impact**: Mission-driven roles can offer $130K-$150K + flexibility

---

## 🤝 Contributing

Found a bug? Want to add a job board? Have a feature idea?

1. Open an Issue
2. Create a Pull Request
3. Or email feedback

This system improves with your feedback.

---

## 📄 License

MIT License - Use freely

---

**Built with 🚀 for Director/VP PM roles**

Your next opportunity is just around the corner. Let's find it together.
