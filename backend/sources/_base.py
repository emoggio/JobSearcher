"""Shared utilities for all job source scrapers."""
from datetime import datetime
from typing import Optional
import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)


def clean_salary(text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse '£90,000 - £120,000' style strings into (min, max) ints."""
    import re
    nums = re.findall(r"[\d,]+", text.replace("£", "").replace("$", ""))
    nums = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 1000]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def parse_date(text: str) -> Optional[datetime]:
    """Best-effort date parsing for 'Posted 3 days ago' style strings."""
    import re
    from datetime import timedelta
    text = text.lower()
    today = datetime.utcnow()
    if "today" in text or "just" in text or "hour" in text:
        return today
    m = re.search(r"(\d+)\s*day", text)
    if m:
        return today - timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s*week", text)
    if m:
        return today - timedelta(weeks=int(m.group(1)))
    m = re.search(r"(\d+)\s*month", text)
    if m:
        return today - timedelta(days=int(m.group(1)) * 30)
    return None
