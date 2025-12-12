import csv
import json
import time
import requests
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# ==================================================
# Apollo Configuration
# ==================================================

APOLLO_API_BASE_URL = "https://api.apollo.io/v1"

OUTPUT_FIELDNAMES = [
    "input_linkedin_url",
    "first_name",
    "last_name",
    "job_title",
    "company_name",
    "company_website",
    "industry",
    "verified_email",
    "verified_mobile_phone",
    "linkedin_url",
    "apollo_person_id",
    "lookup_used",
    "apollo_error"
]


# ==================================================
# Credit Tracking Dataclass
# ==================================================
@dataclass
class CreditUsage:
    match_credits: int = 0
    enrich_credits: int = 0
    email_credits: int = 0
    mobile_credits: int = 0


# ==================================================
# APOLLO CLIENT
# ==================================================

class ApolloClient:
    """
    Apollo.io API Client — Compliant, POST-based, with enrichment fallback.
    """

    def __init__(self, api_key: str, rate_limit_delay: float = 0.4):
        if not api_key:
            raise ValueError("Apollo API key required.")

        self.api_key = api_key
        self.base_url = APOLLO_API_BASE_URL
        self.headers = {"X-Api-Key": api_key}
        self.rate_limit_delay = rate_limit_delay

        # Logical credit usage tracker (NOT actual Apollo credits)
        self.credits = CreditUsage()

    # ============================================
    # Internal POST Request Handler
    # ============================================
    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send POST request to Apollo.io API."""
        url = f"{self.base_url}/{endpoint}"

        time.sleep(self.rate_limit_delay)

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, "status_code", 500)}

    # ==================================================
    # STEP 1 — MATCH BY LINKEDIN
    # ==================================================
    def match_by_linkedin(self, linkedin_url: str) -> Dict[str, Any]:
        payload = {"person": {"linkedin_url": linkedin_url.strip()}}
        self.credits.match_credits += 1
        return self._post("people/match", payload)

    # ==================================================
    # STEP 2 — ENRICH (Fallback)
    # ==================================================
    def enrich_person(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichment payload based on person info returned by match.
        """
        payload = {
            "linkedin_url": person.get("linkedin_url"),
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "organization_name": person.get("organization", {}).get("name")
        }

        self.credits.enrich_credits += 1
        return self._post("people/enrich", payload)

    # ==================================================
    # Extraction Helpers
    # ==================================================
    def extract_verified_email(self, person: Dict[str, Any]) -> Optional[str]:
        emails = person.get("emails", [])
        for e in emails:
            if e.get("status") == "verified" and e.get("type") in ("work", "email"):
                self.credits.email_credits += 1
                return e.get("email")
        return None

    def extract_verified_mobile(self, person: Dict[str, Any]) -> Optional[str]:
        phones = person.get("phone_numbers", [])
        for p in phones:
            if p.get("label") == "mobile" and p.get("status") == "verified":
                self.credits.mobile_credits += 1
                return p.get("sanitized_number") or p.get("number")
        return None

    # ==================================================
    # MAIN PERSON LOOKUP WORKFLOW (Option B)
    # ==================================================
    def lookup_person(self, linkedin_url: str) -> Dict[str, Any]:

        if not linkedin_url:
            return self._empty_result(None, "Empty LinkedIn URL.")

        # STEP 1 — Match
        match = self.match_by_linkedin(linkedin_url)

        if "error" in match:
            return self._empty_result(linkedin_url, f"MATCH API error: {match['error']}")

        person = match.get("person")
        lookup_used = "match"

        # If match returns nothing → stop early
        if not person:
            return self._empty_result(linkedin_url, "No match found.")

        # Extract from MATCH response
        extracted = self._extract_all(person)
        extracted["lookup_used"] = lookup_used

        # PRIORITY: verified mobile phone
        if extracted["verified_mobile_phone"]:
            return extracted

        # STEP 2 — ENRICH
        enrich = self.enrich_person(person)
        lookup_used = "enrich"

        if "error" in enrich:
            extracted["lookup_used"] = lookup_used
            extracted["apollo_error"] = f"Enrich error: {enrich['error']}"
            return extracted  # fallback to match result

        enriched_person = enrich.get("person")
        if enriched_person:
            enriched = self._extract_all(enriched_person)
            enriched["lookup_used"] = lookup_used
            enriched["input_linkedin_url"] = linkedin_url
            return enriched

        # If enrichment returns nothing
        extracted["lookup_used"] = lookup_used
        extracted["apollo_error"] = "No enrichment data returned."
        return extracted

    # ==================================================
    # Extract all required fields
    # ==================================================
    def _extract_all(self, person: Dict[str, Any]) -> Dict[str, Any]:
        org = person.get("organization", {})

        return {
            "input_linkedin_url": person.get("linkedin_url"),
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "job_title": person.get("title"),
            "company_name": org.get("name"),
            "company_website": org.get("website_url"),
            "industry": org.get("industry"),
            "verified_email": self.extract_verified_email(person),
            "verified_mobile_phone": self.extract_verified_mobile(person),
            "linkedin_url": person.get("linkedin_url"),
            "apollo_person_id": person.get("id"),
            "lookup_used": None,
            "apollo_error": None
        }

    # ==================================================
    # Empty/Failed Result
    # ==================================================
    def _empty_result(self, linkedin_url: Optional[str], error: str) -> Dict[str, Any]:
        out = {field: None for field in OUTPUT_FIELDNAMES}
        out["input_linkedin_url"] = linkedin_url
        out["apollo_error"] = error
        return out

    # ==================================================
    # CSV Processing
    # ==================================================
    def process_csv(self, input_csv: str, output_path: str, output_format="csv", linkedin_column="linkedin_url"):
        if not os.path.exists(input_csv):
            print(f"Input CSV not found: {input_csv}")
            return

        results = []
        with open(input_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if linkedin_column not in reader.fieldnames:
                print(f"CSV missing column: {linkedin_column}")
                return

            for i, row in enumerate(reader):
                url = row.get(linkedin_column)
                result = self.lookup_person(url)
                results.append(result)

                if (i + 1) % 10 == 0:
                    print(f"Processed {i+1} rows...")

        self._write_output(results, output_path, output_format)

        print("\n=== CREDIT USAGE SUMMARY ===")
        print(self.credits)

    # ==================================================
    # Write CSV or JSON
    # ==================================================
    def _write_output(self, results, output_path, fmt):
        if fmt == "csv":
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
                writer.writeheader()
                writer.writerows(results)
            print(f"CSV saved: {output_path}")

        elif fmt == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)
            print(f"JSON saved: {output_path}")

        else:
            print("Unsupported format. Use csv or json.")


# ==================================================
# EXECUTION BLOCK
# ==================================================
if __name__ == "__main__":
    API_KEY = os.getenv("APOLLO_API_KEY")

    if not API_KEY:
        print("Set APOLLO_API_KEY environment variable.")
        exit(1)

    client = ApolloClient(API_KEY)

    INPUT_CSV = "input.csv"
    OUTPUT_CSV = "apollo_output.csv"

    client.process_csv(INPUT_CSV, OUTPUT_CSV, output_format="csv")
