"""Himalayas REST API client for remote tech job leads extraction."""
import datetime
import html
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class HimalayasClient:
    API_URL = "https://himalayas.app/jobs/api"

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        self.client = httpx.Client(headers=headers, timeout=25)

    def fetch_jobs(self, max_items=30, keyword_filter="", seniority_filter=""):
        fetch_limit = min(max_items * 3, 200)
        target_url = f"{self.API_URL}?limit={fetch_limit}"
        logging.info("Querying Himalayas API: %s", target_url)

        resp = self.client.get(target_url)
        if resp.status_code != 200:
            logging.error("Failed to fetch Himalayas API (HTTP %s)", resp.status_code)
            return []

        raw_data = resp.json()
        raw_jobs = raw_data.get("jobs", []) if isinstance(raw_data, dict) else []
        logging.info("Discovered %d active listings on Himalayas", len(raw_jobs))

        kw_clean = keyword_filter.strip().lower() if keyword_filter else ""
        sen_clean = seniority_filter.strip().lower() if seniority_filter else ""
        jobs = []

        for j in raw_jobs:
            if len(jobs) >= max_items:
                break

            title = j.get("title", "")
            company = j.get("companyName", "")
            seniority = j.get("seniority") or "Any"
            categories = j.get("categories") or []
            cat_str = ", ".join(categories) if isinstance(categories, list) else str(categories)
            desc = html.unescape(j.get("description") or j.get("excerpt") or "")

            if kw_clean:
                search_text = f"{title} {company} {cat_str} {desc}".lower()
                if kw_clean not in search_text:
                    continue

            if sen_clean:
                if sen_clean not in seniority.lower() and sen_clean not in title.lower():
                    continue

            min_sal = j.get("minSalary")
            max_sal = j.get("maxSalary")
            curr = j.get("currency", "USD")
            period = j.get("salaryPeriod") or "year"
            if min_sal and max_sal:
                salary_str = f"{curr} {min_sal:,} - {max_sal:,} / {period}"
            elif min_sal:
                salary_str = f"From {curr} {min_sal:,} / {period}"
            else:
                salary_str = "Not specified"

            loc_list = j.get("locationRestrictions") or []
            loc_str = ", ".join(loc_list) if loc_list else "Worldwide / Remote"

            guid = j.get("guid") or ""
            slug = j.get("companySlug") or "company"
            himalayas_url = f"https://himalayas.app/companies/{slug}/jobs/{guid}" if guid else "https://himalayas.app/jobs"
            apply_url = j.get("applicationLink") or himalayas_url

            job_item = {
                "id": str(guid or j.get("title")),
                "company": company,
                "title": title,
                "salary": salary_str,
                "seniority": seniority,
                "employmentType": j.get("employmentType") or "Full-time",
                "locationRestrictions": loc_str,
                "categories": cat_str,
                "applicationUrl": apply_url,
                "himalayasUrl": himalayas_url,
                "companyLogo": j.get("companyLogo") or "",
                "summary": desc[:300] + "..." if len(desc) > 300 else desc,
                "fullDescription": desc,
                "postedAt": j.get("pubDate") or "",
                "extractedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            jobs.append(job_item)
            logging.info("Extracted Himalayas job: %s @ %s (%s)", title, company, salary_str)

        logging.info("Total Himalayas jobs extracted: %d", len(jobs))
        return jobs
