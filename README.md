---

# 📘 Apollo Contact Enrichment Script (Compliant, API-Only)

This project provides a **fully compliant**, **scalable**, and **mobile-optimized** Python solution for extracting contact and company data from Apollo.io using **only the official Apollo.io API**.
No scraping of any kind is used — the tool adheres strictly to Apollo.io’s Terms of Service, GDPR, CCPA, and global data protection standards.

---

# ⚠️ Compliance & Data Usage Statement

This tool:

✔ Uses **exclusively the official Apollo.io REST API**
✔ Does **not** scrape Apollo’s UI, HTML, or web interface
✔ Complies with Apollo.io ToS, GDPR, CCPA
✔ Performs no data storage beyond final exported CSV/JSON
✔ Requires users to supply a valid Apollo API key obtained legally through their account

You are responsible for:

* Ensuring you have lawful grounds to process the data obtained through Apollo
* Keeping your API key secure
* Using the output only for legitimate and compliant business purposes

---

# 🚀 Features

### 🔐 1. API-Key Authentication

Authenticate securely using the Apollo API key via an environment variable.

### 🧭 2. LinkedIn-Based Contact Lookup

Takes LinkedIn profile URLs as input and performs:

1. **Primary Lookup (people/match)**
2. **Fallback Enrichment (people/enrich)**

### 📊 3. Extracted Data Fields

For each contact, the script extracts:

* First Name
* Last Name
* Job Title
* Company Name
* Company Website
* Company Industry
* **Verified Corporate Email**
* **Verified Mobile Phone Number (Primary Goal)**
* Apollo Person ID
* Canonical LinkedIn URL
* Error messages (if any)

### 📱 4. Verified Mobile Phone Prioritization

Mobile retrieval uses a **two-step enrichment strategy**:

1. `POST /people/match`
2. If no verified mobile → `POST /people/enrich`

This maximizes mobile retrieval accuracy while minimizing credits used.

### ⚖️ 5. Credit Usage Simulation

Tracks:

* Match lookups
* Enrich lookups
* Email credits
* Mobile credits

This helps you understand credit consumption behavior without misrepresenting Apollo billing.

### 📤 6. CSV or JSON Export

Clean, complete export with consistent fieldnames.

---

# 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/aggarwalkavyanew-dev/apollo-contact-extractor.git
cd apollo-contact-extractor
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Minimal dependencies:

```
requests
```

### 3. Set Your Apollo API Key

```bash
export APOLLO_API_KEY="your_api_key_here"
```

Windows (PowerShell):

```powershell
setx APOLLO_API_KEY "your_api_key_here"
```

---

# 📝 Input Format

Your input CSV must contain **one column** named:

```
linkedin_url
```

### Example:

```csv
linkedin_url
https://www.linkedin.com/in/someperson/
https://www.linkedin.com/in/anotherperson/
```

---

# ▶️ Running the Script

```bash
python apollo_extractor.py
```

The script will:

1. Load `input.csv`
2. Process each LinkedIn profile URL
3. Retrieve contact/company details from Apollo
4. Save the output to:

```
apollo_output.csv
```

---

# 📄 Output Example

Example CSV fields:

```csv
input_linkedin_url,first_name,last_name,job_title,company_name,company_website,industry,verified_email,verified_mobile_phone,linkedin_url,apollo_person_id,lookup_used,apollo_error
https://www.linkedin.com/in/... ,John,Doe,CTO,Acme Corp,https://acme.com,Software,john.doe@acme.com,+15555550123,https://www.linkedin.com/in/... ,12345678,match,
```

---

# 🔧 Code Architecture

```
apollo_extractor.py
│
├── ApolloClient
│   ├── match_by_linkedin()     → Fast lookup (POST /people/match)
│   ├── enrich_person()         → Fallback lookup (POST /people/enrich)
│   ├── extract_verified_email()
│   ├── extract_verified_mobile()
│   ├── lookup_person()         → Two-step mobile-optimized workflow
│   ├── process_csv()           → Bulk processing
│   ├── _write_output()         → CSV/JSON export
│   └── _post()                 → API request handler
│
└── CreditUsage (dataclass)     → Tracks credits used
```

---

# 🧠 Mobile Optimization Logic (Option B Strategy)

This script prioritizes verified mobile numbers using the following algorithm:

1. **Match Lookup**

   * Uses LinkedIn URL
   * Low credit usage
   * Often returns verified mobile
   * If mobile found → STOP

2. **Enrich Lookup (Fallback)**

   * Triggered only if match fails to return mobile
   * Uses person details (name, company, LinkedIn)
   * Often returns mobile when match does not
   * If mobile found → STOP

3. **Return best available data**

   * Email
   * Company
   * Name
   * IDs
   * Error info

This approach delivers **maximum mobile retrieval** with **balanced credit consumption**.

---

# 🔧 Rate Limiting

A delay (`rate_limit_delay`) is enforced between requests to respect Apollo’s rate limits.

Default: **0.4 seconds per request**
(≈ 2.5 requests/second)

Can be increased based on your Apollo plan.

---

# 📜 License

This script is provided for legitimate business use only and must be used in compliance with:

* Apollo.io Terms of Service
* GDPR
* CCPA
* Local privacy and data protection laws

---

