"""Run a bounded, reproducible corpus campaign into an isolated Mongo database."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.sources import SOURCES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "corpus_campaign"
LANGUAGES = ("en", "hi", "bn", "mr")
TARGETS = {"total": 2000, "per_language": 500, "per_adapter": 250}
FLOORS = {"total": 1000, "per_language": 200, "per_family_per_language": 50, "families_per_language": 2}
WINDOW_DAYS = 90
RUN_BATCHES = (("abp_en", "oneindia_en"), ("abp_hi", "amarujala_hi"), ("abp_bn", "news18_bn"), ("abp_mr", "loksatta_mr"))
INTERRUPTED_ATTEMPT = "artifacts/corpus_campaign/interrupted_attempt.json"


def utc_date(value: str) -> date:
    return date.fromisoformat(value)


def article_date(article: dict) -> date | None:
    value = article.get("date") or article.get("published_at")
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date()
    except (TypeError, ValueError):
        return None


def qualified_summary(articles: list[dict], start: date, end: date) -> dict:
    in_window = [a for a in articles if (d := article_date(a)) is not None and start <= d <= end]
    languages = {}
    for lang in LANGUAGES:
        group = [a for a in in_window if a.get("lang") == lang]
        families: dict[str, int] = {}
        for article in group:
            family = article.get("source_family", "unknown")
            families[family] = families.get(family, 0) + 1
        languages[lang] = {"accepted": len(group), "families": families}
    return {"accepted": len(in_window), "languages": languages}


def run_one(adapter: str, anchor: date, max_articles: int, max_listing_pages: int, timeout: int, database: str, family_locks: dict[str, threading.Lock]) -> dict:
    source = SOURCES[adapter]
    start = anchor - timedelta(days=WINDOW_DAYS - 1)
    args = [
        sys.executable, "-m", "scrapy", "crawl", adapter,
        "-a", f"max_articles={max_articles}",
        "-a", f"max_listing_pages={max_listing_pages}",
        "-a", f"date_from={start.isoformat()}",
        "-a", f"date_to={anchor.isoformat()}",
        "-s", f"MONGO_DATABASE={database}",
        "-s", "LOG_LEVEL=INFO",
    ]
    began = datetime.now(timezone.utc)
    started = time.monotonic()
    result = {"adapter_id": adapter, "source_family": source["family"], "lang": source["lang"], "window_days": WINDOW_DAYS,
              "date_from": start.isoformat(), "date_to": anchor.isoformat(), "extractor_version": source["extractor_version"],
              "mapping_version": source["mapping_version"], "command": args, "environment": {"SCRAPY_SETTINGS_MODULE": "scrapers.settings"},
              "started_at": began.isoformat(), "status": "running"}
    try:
        with family_locks[source["family"]]:
            proc = subprocess.Popen(args, cwd=ROOT, env={**os.environ, "SCRAPY_SETTINGS_MODULE": "scrapers.settings"}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                output, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    output, _ = proc.communicate(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    output, _ = proc.communicate()
                result["status"] = "timeout"
                result["timeout_shutdown"] = "SIGTERM, then SIGKILL only if still running after 15 seconds"
            else:
                result["status"] = "finished" if proc.returncode == 0 else "failed"
                result["return_code"] = proc.returncode
            match = re.search(r"scraper/listing_page_limit_reached['\"]?\s*:\s*(\d+)", output or "")
            result["listing_page_limit_reached_sections"] = int(match.group(1)) if match else 0
            if output:
                result["log_tail"] = output[-3000:]
    except OSError as exc:
        result.update(status="launch_failed", error=str(exc))
    result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    result["ended_at"] = datetime.now(timezone.utc).isoformat()
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000)
    try:
        run = client[database].crawl_runs.find_one({"adapter_id": adapter, "started_at": {"$gte": began}}, sort=[("started_at", -1)])
        if run:
            result["run_id"] = run["_id"]
            result["run_counts"] = run.get("counts", {})
            result["run_status"] = run.get("status")
    finally:
        client.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", help="fixed UTC end date YYYY-MM-DD (default: today's UTC date)")
    parser.add_argument("--database", default="news_intel_corpus_v1")
    parser.add_argument("--max-articles", type=int, default=250)
    parser.add_argument("--max-listing-pages", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--metadata", type=Path, default=OUT / "campaign.json")
    args = parser.parse_args()
    if args.database in {"admin", "local", "config", "news_intel", "news_intel_verification"} or args.database.startswith("news_intel_scraper_test_"):
        parser.error("campaign database must be isolated from legacy and verification data")
    if not 1 <= args.max_articles <= 500 or not 1 <= args.max_listing_pages <= 100 or args.timeout_seconds < 30:
        parser.error("limits out of bounds: max-articles 1..500, max-listing-pages 1..100, timeout >=30")
    anchor = utc_date(args.anchor) if args.anchor else datetime.now(timezone.utc).date()
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000)
    database = client[args.database]
    start = anchor - timedelta(days=WINDOW_DAYS - 1)
    record = {"campaign_id": datetime.now(timezone.utc).strftime("corpus-%Y%m%dT%H%M%SZ"), "anchor_utc": anchor.isoformat(),
              "database": args.database, "max_articles_per_run": args.max_articles, "max_listing_pages": args.max_listing_pages,
              "timeout_seconds_per_run": args.timeout_seconds, "max_parallel_runs": 2, "families_permitted_concurrently": "distinct only",
              "targets_aspirational": TARGETS, "former_floors_user_relaxed_to_aspirations": FLOORS,
              "date_window": {"days": WINDOW_DAYS, "date_from_inclusive_utc": start.isoformat(), "date_to_inclusive_utc": anchor.isoformat()},
              "adapters": list(SOURCES), "access_notes_file": "artifacts/corpus_campaign/source_access_notes.json",
              "prior_interrupted_attempt_file": INTERRUPTED_ATTEMPT if (ROOT / INTERRUPTED_ATTEMPT).exists() else None,
              "runs": [], "expansion": "not automatic; page-limit signals require review because they do not prove older eligible articles exist"}
    locks = {source["family"]: threading.Lock() for source in SOURCES.values()}
    try:
        args.metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        for batch in RUN_BATCHES:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run_one, adapter, anchor, args.max_articles, args.max_listing_pages, args.timeout_seconds, args.database, locks) for adapter in batch]
                for future in as_completed(futures):
                    result = future.result()
                    record["runs"].append(result)
                    args.metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        record["final_summary"] = qualified_summary(list(database.articles.find({})), start, anchor)
        record["coverage_gaps"] = [lang for lang, value in record["final_summary"]["languages"].items() if value["accepted"] < FLOORS["per_language"]]
        record["stop_reason"] = "one bounded 90-day pass completed; inspect page-limit signals before any wider-window run"
        record["legacy_database_untouched"] = True
        record["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        args.metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"campaign_id": record["campaign_id"], "database": args.database, "summary": record["final_summary"], "coverage_gaps": record["coverage_gaps"], "page_limit_signals": {run["adapter_id"]: run["listing_page_limit_reached_sections"] for run in record["runs"]}, "metadata": str(args.metadata)}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
