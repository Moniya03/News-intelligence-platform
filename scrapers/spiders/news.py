from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import scrapy
from w3lib.html import remove_tags

from scrapers.sources import CATEGORY_ORDER, SOURCES

TRACKING_KEYS = {"fbclid", "gclid", "ref", "ref_source", "ref_medium", "ref_campaign", "src", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
GLOBAL_CATEGORIES = set(CATEGORY_ORDER)
CAPTURE_HTTP_STATUSES = [400, 401, 403, 404, 410, 429, 500, 502, 503, 504]
BODY_SELECTORS = (
    '[itemprop="articleBody"] p::text', "article p::text", ".article-content p::text",
    ".article-body p::text", ".entry-content p::text", "#articleBody p::text",
)


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


def _jsonld_objects(response):
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        queue = value if isinstance(value, list) else [value]
        while queue:
            obj = queue.pop()
            if isinstance(obj, dict):
                if isinstance(obj.get("@graph"), list):
                    queue.extend(obj["@graph"])
                yield obj


def extract_article(response, source):
    ld = next((obj for obj in _jsonld_objects(response) if "article" in str(obj.get("@type", "")).lower() and (obj.get("articleBody") or obj.get("headline"))), {})
    title = (ld.get("headline") or ld.get("name") or response.css("h1::text").get() or response.css('meta[property="og:title"]::attr(content)').get() or "").strip()
    body = ld.get("articleBody") or ""
    if isinstance(body, list):
        body = " ".join(map(str, body))
    body = unescape(remove_tags(str(body))).strip()
    if not body:
        for selector in BODY_SELECTORS:
            paragraphs = [x.strip() for x in response.css(selector).getall() if x.strip()]
            if paragraphs:
                body = " ".join(paragraphs)
                break
    date = ld.get("datePublished") or response.css('[itemprop="datePublished"]::attr(datetime)').get() or response.css('meta[property="article:published_time"]::attr(content)').get()
    canonical = response.css('link[rel="canonical"]::attr(href)').get()
    if not canonical and isinstance(ld.get("mainEntityOfPage"), dict):
        canonical = ld["mainEntityOfPage"].get("@id")
    canonical = canonical_url(response.urljoin(canonical) if canonical else response.url)
    author = ld.get("author", {})
    if isinstance(author, list):
        author = author[0] if author else {}
    author = author.get("name") if isinstance(author, dict) else str(author or "")
    section = ld.get("articleSection") or "unknown"
    if isinstance(section, list):
        section = section[0] if section else "unknown"
    return {"title": title, "body": body, "published_at": date, "author": author, "section": str(section), "canonical_url": canonical}


def valid_article(article):
    if not article["title"]:
        return False, "missing_title"
    if len(article["body"]) < 200:
        return False, "body_under_200_chars"
    if re.sub(r"\W", "", article["title"]).casefold() == re.sub(r"\W", "", article["body"]).casefold():
        return False, "body_equals_title"
    if not article["published_at"]:
        return False, "missing_published_at"
    try:
        datetime.fromisoformat(str(article["published_at"]).replace("Z", "+00:00"))
    except ValueError:
        return False, "invalid_published_at"
    return True, None


def validate_response_article(status, article):
    if status != 200:
        return False, f"http_status_{status}"
    return valid_article(article)


def listing_hrefs(response, source):
    """Read candidate URLs only from the publisher's verified editorial cards."""
    return [anchor.attrib.get("href") for anchor in response.css(source["listing_selector"]) if anchor.attrib.get("href")]


def article_matches_section(url, source, section):
    parts = urlsplit(url)
    prefix = section.get("article_path_prefix")
    return (
        parts.hostname == source["domain"]
        and re.search(source["article_path"], parts.path, re.I)
        and (prefix is None or parts.path.startswith(prefix))
    )


class NewsSpider(scrapy.Spider):
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 36}

    def __init__(self, max_articles=20, **kwargs):
        super().__init__(**kwargs)
        self.max_articles = max(1, min(int(max_articles), 50))

    @property
    def source(self):
        return SOURCES[self.adapter_id]

    async def start(self):
        self._seen = set()
        self._seen_listing_pages = set()
        self._article_count = 0
        self._section_article_counts = {}
        for section in self.source["sections"]:
            if section.get("category") not in GLOBAL_CATEGORIES:
                self.logger.error("skip unmapped section url=%s", section.get("url"))
                self.crawler.stats.inc_value("scraper/unmapped_sections")
                continue
            page_key = (section["url"], canonical_url(section["url"]))
            self._seen_listing_pages.add(page_key)
            yield scrapy.Request(section["url"], callback=self.parse_listing, errback=self.request_error, meta={"handle_httpstatus_list": CAPTURE_HTTP_STATUSES, "section_mapping": section, "listing_page": 1})

    def request_error(self, failure):
        self._record_error(failure.request.url, failure.type.__name__)
        self.logger.warning("request failed type=%s url=%s", failure.type.__name__, failure.request.url)

    def _record_error(self, url, error_type):
        self.crawler.stats.inc_value("scraper/errors")
        errors = self.crawler.stats.get_value("scraper/error_urls", [])
        if len(errors) < 50:
            errors.append({"url": url, "error_type": error_type})
            self.crawler.stats.set_value("scraper/error_urls", errors)

    def parse_listing(self, response):
        if response.status != 200:
            self._record_error(response.url, f"http_status_{response.status}")
            self.logger.warning("section status=%s url=%s", response.status, response.url)
            return
        section = response.meta.get("section_mapping", {})
        global_category = section.get("category")
        if global_category not in GLOBAL_CATEGORIES:
            self.crawler.stats.inc_value("scraper/unmapped_sections")
            self.logger.error("skip unmapped section response url=%s", response.url)
            return
        for href in listing_hrefs(response, self.source):
            url = canonical_url(response.urljoin(href))
            seen_key = (url, section["url"])
            if not article_matches_section(url, self.source, section) or seen_key in self._seen:
                continue
            self._seen.add(seen_key)
            self.crawler.stats.inc_value("scraper/discovered")
            per_section_limit = max(1, (self.max_articles + len(self.source["sections"]) - 1) // len(self.source["sections"]))
            section_count = self._section_article_counts.get(section["url"], 0)
            if self._article_count >= self.max_articles:
                break
            if section_count >= per_section_limit:
                continue
            self._article_count += 1
            self._section_article_counts[section["url"]] = section_count + 1
            mapping = {"category": global_category, "original_category": section["label"], "section_url": section["url"], "mapping_version": self.source["mapping_version"]}
            yield scrapy.Request(url, callback=self.parse_article, errback=self.request_error, dont_filter=True, meta={"handle_httpstatus_list": CAPTURE_HTTP_STATUSES, "discovered_from_section": response.url, "section_url": section["url"], "category": global_category, "original_category": section["label"], "mapping_version": self.source["mapping_version"], "category_mappings": [mapping]})
        next_page = self._schedule_next_listing_page(response, section)
        if next_page is not None:
            yield next_page

    def _schedule_next_listing_page(self, response, section):
        selector = self.source.get("pagination_selector")
        pattern = self.source.get("pagination_pattern")
        if not selector or not pattern:
            return
        per_section_limit = max(1, (self.max_articles + len(self.source["sections"]) - 1) // len(self.source["sections"]))
        if self._section_article_counts.get(section["url"], 0) >= per_section_limit:
            return
        current_page = response.meta.get("listing_page", 1)
        maximum = self.source.get("max_listing_pages", 1)
        candidates = []
        for anchor in response.css(selector):
            href = anchor.attrib.get("href")
            if not href:
                continue
            url = canonical_url(response.urljoin(href))
            parts = urlsplit(url)
            match = re.fullmatch(pattern, parts.path, re.I)
            if parts.hostname != self.source["domain"] or not match:
                continue
            page_number = int(match.group("page"))
            page_key = (section["url"], url)
            if current_page < page_number <= maximum and page_key not in self._seen_listing_pages:
                candidates.append((page_number, url, page_key))
        if not candidates:
            return
        page_number, url, page_key = min(candidates)
        self._seen_listing_pages.add(page_key)
        return scrapy.Request(
            url,
            callback=self.parse_listing,
            errback=self.request_error,
            meta={"handle_httpstatus_list": CAPTURE_HTTP_STATUSES, "section_mapping": section, "listing_page": page_number},
        )

    def parse_article(self, response):
        extracted = extract_article(response, self.source)
        accepted, reason = validate_response_article(response.status, extracted)
        article_id = hashlib.sha256(f"{self.source['family']}\0{extracted['canonical_url']}".encode()).hexdigest()
        raw_html = response.body.decode(response.encoding or "utf-8", errors="replace")
        content_hash = hashlib.sha256(extracted["body"].encode()).hexdigest()
        request_meta = response.meta
        category_mappings = request_meta.get("category_mappings", [])
        yield {
            "adapter_id": self.adapter_id, "source_family": self.source["family"], "lang": self.source["lang"],
            "source": self.source["domain"], "discovered_from_section": request_meta.get("discovered_from_section"), "section_url": request_meta.get("section_url"), "original_category": request_meta.get("original_category"), "mapping_version": request_meta.get("mapping_version"), "category_mappings": category_mappings, "original_url": response.request.url, "final_url": response.url,
            "canonical_url": extracted["canonical_url"], "http_status": response.status, "fetched_at": datetime.now().astimezone(),
            "extractor_version": self.source["extractor_version"], "raw_html": raw_html,
            "raw_html_hash": hashlib.sha256(response.body).hexdigest(), "article_id": article_id,
            "content_hash": content_hash, "title": extracted["title"], "body": extracted["body"],
            "date": extracted["published_at"], "published_at": extracted["published_at"], "author": extracted["author"], "provider_article_section": extracted["section"], "category": request_meta.get("category"),
            "accepted": accepted, "rejection_reason": reason,
        }
