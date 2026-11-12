"""Read-only quality report for the campaign's accepted Mongo article records."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.sources import CATEGORY_ORDER, SOURCES

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {"en": ("LATIN",), "hi": ("DEVANAGARI",), "mr": ("DEVANAGARI",), "bn": ("BENGALI",)}
REPORT = ROOT / "artifacts" / "corpus_campaign" / "quality_report.json"


def as_date(value) -> date | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()


def normalized_text(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold(), flags=re.UNICODE).strip()


def script_ratio(text: str, script_name: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(unicodedata.name(char, "").find(script_name) >= 0 for char in letters) / len(letters)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=ROOT / "artifacts/corpus_campaign/campaign.json")
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--mongo-uri", default=None)
    parser.add_argument("--sample-per-adapter", type=int, default=5)
    args = parser.parse_args()
    campaign = json.loads(args.campaign.read_text())
    db_name = campaign["database"]
    start = date.fromisoformat(campaign["date_window"]["date_from_inclusive_utc"])
    end = date.fromisoformat(campaign["date_window"]["date_to_inclusive_utc"])
    if args.sample_per_adapter < 0:
        parser.error("sample-per-adapter must be nonnegative")

    client = MongoClient(args.mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000)
    try:
        db = client[db_name]
        articles = list(db.articles.find({}))
        raw_ids = [article.get("raw_version_id") for article in articles if article.get("raw_version_id")]
        raw_refs = {doc["_id"] for doc in db.raw_article_versions.find({"_id": {"$in": raw_ids}}, {"_id": 1})}
        issues = []
        bodies: dict[str, list[dict]] = defaultdict(list)
        per_adapter: dict[str, list[dict]] = defaultdict(list)
        counts = Counter()
        adapter_counts = Counter()
        language_counts = Counter()
        category_counts = Counter()
        section_counts = Counter()
        for article in articles:
            adapter = article.get("adapter_id", "unknown")
            lang = article.get("lang", "unknown")
            d = as_date(article.get("date"))
            title = str(article.get("title") or "")
            body = str(article.get("body") or "")
            flags = []
            if d is None or not start <= d <= end:
                flags.append("publication_date_outside_or_invalid_window")
            if not article.get("canonical_url"):
                flags.append("missing_canonical_url")
            if not title.strip():
                flags.append("missing_title")
            if len(body) < 200:
                flags.append("body_under_200_chars")
            if title.strip() and normalized_text(title) == normalized_text(body):
                flags.append("body_equals_title")
            if article.get("raw_version_id") not in raw_refs:
                flags.append("missing_raw_version_reference")
            mappings = article.get("category_mappings") or []
            cats = article.get("categories") or []
            if not mappings or not cats:
                flags.append("missing_category_mapping_context")
            if any(mapping.get("category") not in CATEGORY_ORDER for mapping in mappings):
                flags.append("unknown_global_category_mapping")
            if any(category not in CATEGORY_ORDER for category in cats):
                flags.append("unknown_global_category")
            expected = LANGUAGES.get(lang)
            ratio = max((script_ratio(body, name) for name in expected), default=None) if expected else None
            if ratio is None:
                flags.append("unsupported_language_code")
            elif ratio < 0.25:
                flags.append("language_script_plausibility_low_review")
            record = {"article_id": article.get("_id"), "adapter_id": adapter, "source_family": article.get("source_family"),
                      "lang": lang, "canonical_url": article.get("canonical_url"), "date": article.get("date"),
                      "title": title, "body_chars": len(body), "body_sha256": hashlib.sha256(body.encode()).hexdigest() if body else None,
                      "raw_version_id": article.get("raw_version_id"), "categories": cats,
                      "category_mappings": mappings, "language_script_ratio": round(ratio, 3) if ratio is not None else None,
                      "flags": flags}
            per_adapter[adapter].append(record)
            adapter_counts[adapter] += 1
            language_counts[lang] += 1
            for category in cats:
                category_counts[category] += 1
            for mapping in mappings:
                section_counts[(adapter, mapping.get("category"), mapping.get("section_url"))] += 1
            counts.update(flags)
            if flags:
                issues.append(record)
            if body:
                digest = hashlib.sha256(normalized_text(body).encode()).hexdigest()
                bodies[digest].append({"article_id": article.get("_id"), "adapter_id": adapter, "source_family": article.get("source_family"), "lang": lang, "canonical_url": article.get("canonical_url"), "body_sha256": digest})
        exact_duplicate_groups = [group for group in bodies.values() if len(group) > 1]
        cross_publisher_groups = [group for group in exact_duplicate_groups if len({row["source_family"] for row in group}) > 1]
        rejected_by_adapter = Counter()
        rejected_by_reason = Counter()
        rejected_by_adapter_reason = Counter()
        for raw in db.raw_article_versions.find({"extracted.accepted": False},
                                                {"adapter_id": 1, "extracted.rejection_reason": 1}):
            adapter = raw.get("adapter_id", "unknown")
            reason = (raw.get("extracted") or {}).get("rejection_reason") or "unspecified"
            rejected_by_adapter[adapter] += 1
            rejected_by_reason[reason] += 1
            rejected_by_adapter_reason[(adapter, reason)] += 1
        coverage_matrix = {}
        for adapter, source in sorted(SOURCES.items()):
            sections_by_category = defaultdict(list)
            for section in source.get("sections", []):
                sections_by_category[section["category"]].append({
                    "label": section.get("label"), "url": section["url"]})
            coverage_matrix[adapter] = {
                category: {
                    "accepted_articles_with_mapping": sum(
                        count for (mapped_adapter, mapped_category, _), count in section_counts.items()
                        if mapped_adapter == adapter and mapped_category == category),
                    "configured_routes": sections_by_category.get(category, []),
                    "status": ("accepted_records" if any(
                        mapped_adapter == adapter and mapped_category == category and count
                        for (mapped_adapter, mapped_category, _), count in section_counts.items())
                        else "configured_route_no_accepted_records" if sections_by_category.get(category)
                        else "no_configured_route"),
                }
                for category in CATEGORY_ORDER
            }
        report = {
            "campaign_id": campaign.get("campaign_id"), "database": db_name,
            "date_window_utc_inclusive": {"from": start.isoformat(), "to": end.isoformat()},
            "read_only": True, "accepted_current_article_records": len(articles), "accepted_in_window": sum(not any(flag == "publication_date_outside_or_invalid_window" for flag in row["flags"]) for group in per_adapter.values() for row in group),
            "by_adapter": {adapter: adapter_counts[adapter] for adapter in SOURCES},
            "by_language": {lang: language_counts[lang] for lang in sorted(LANGUAGES)},
            "by_global_category": {category: category_counts[category] for category in CATEGORY_ORDER},
            "adapter_category_coverage": coverage_matrix,
            "rejections": {
                "raw_rejected_versions": sum(rejected_by_adapter.values()),
                "by_adapter": {adapter: rejected_by_adapter[adapter] for adapter in SOURCES},
                "by_reason": dict(sorted(rejected_by_reason.items())),
                "by_adapter_and_reason": {
                    f"{adapter}:{reason}": count
                    for (adapter, reason), count in sorted(rejected_by_adapter_reason.items())
                },
            },
            "flag_counts": dict(counts), "flagged_records": issues,
            "exact_body_duplicate_group_count": len(exact_duplicate_groups),
            "cross_publisher_exact_body_review_groups": cross_publisher_groups,
            "samples_by_adapter": {
                adapter: [
                    {key: row[key] for key in ("article_id", "canonical_url", "date", "title", "body_chars", "raw_version_id", "categories", "category_mappings", "language_script_ratio", "flags")}
                    for row in sorted(rows, key=lambda r: str(r["article_id"]))[:args.sample_per_adapter]
                ]
                for adapter, rows in sorted(per_adapter.items())
            },
            "limitations": ["Unicode script ratios flag implausible language assignments but do not certify language or translation accuracy.",
                            "Exact normalized body matches are review groups; no records are removed and publisher provenance is retained.",
                            "Near-duplicate/syndication detection beyond exact normalized body matches is deferred.",
                            "Category mappings are section-derived weak labels, not verified article-topic judgments."],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
        print(json.dumps({"campaign_id": report["campaign_id"], "accepted_current_article_records": len(articles), "flag_counts": dict(counts), "exact_duplicate_groups": len(exact_duplicate_groups), "report": str(args.report)}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
