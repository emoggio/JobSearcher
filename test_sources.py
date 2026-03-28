"""
Standalone source tester — run with:
  python test_sources.py [source_name]

Tests each scraper individually and prints results.
No FastAPI/DB required.
"""
import asyncio
import sys
import logging

# Must be set before any playwright import on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_sources")

TEST_PARAMS = {
    "keywords": "Programme Director Delivery",
    "location": "London",
    "salary_min": 90000,
    "date_posted": "30d",
}


async def test_source(name: str):
    import importlib
    try:
        mod = importlib.import_module(f"backend.sources.{name}")
    except ImportError as e:
        logger.error("Cannot import %s: %s", name, e)
        return []

    logger.info("=== Testing %s ===", name)
    try:
        jobs = await mod.scrape(TEST_PARAMS)
        logger.info("%s returned %d jobs", name, len(jobs))
        for j in jobs[:3]:
            logger.info("  • %s @ %s | %s | %s", j.get("title"), j.get("company"), j.get("location"), j.get("url", "")[:80])
        return jobs
    except Exception as e:
        logger.error("%s FAILED: %s", name, e, exc_info=True)
        return []


async def main():
    sources = sys.argv[1:] if len(sys.argv) > 1 else [
        "linkedin", "indeed", "glassdoor", "totaljobs", "cwjobs", "reed", "adzuna"
    ]

    totals = {}
    for name in sources:
        jobs = await test_source(name)
        totals[name] = len(jobs)

    print("\n=== SUMMARY ===")
    for name, count in totals.items():
        status = "OK" if count > 0 else "FAIL"
        print(f"  {status} {name}: {count} jobs")


if __name__ == "__main__":
    asyncio.run(main())
