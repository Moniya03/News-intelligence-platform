import unittest

from scrapy.http import HtmlResponse, Request

from scrapers.sources import AMARUJA_MAPPING_VERSION, MAPPING_VERSION, SOURCES
from scrapers.spiders.news import NewsSpider, article_matches_section, canonical_url, extract_article, listing_hrefs, valid_article, validate_response_article


class TestScrapers(unittest.TestCase):
    def test_sources_cover_four_languages_with_two_publisher_families(self):
        by_language = {}
        for source in SOURCES.values():
            by_language.setdefault(source["lang"], set()).add(source["family"])
        self.assertEqual(set(by_language), {"en", "hi", "bn", "mr"})
        self.assertTrue(all(len(families) >= 2 for families in by_language.values()))
        self.assertEqual(len(SOURCES), 8)
        supported = set()
        for source in SOURCES.values():
            expected_version = AMARUJA_MAPPING_VERSION if source is SOURCES["amarujala_hi"] else MAPPING_VERSION
            self.assertEqual(source["mapping_version"], expected_version)
            self.assertGreaterEqual(len(source["sections"]), 2)
            for section in source["sections"]:
                self.assertIn(section["category"], {"politics", "finance", "health", "science_technology", "environment", "sports"})
                self.assertTrue(section["label"])
                self.assertTrue(section["url"].startswith("https://"))
                supported.add(section["category"])
        self.assertEqual(supported, {"politics", "finance", "health", "science_technology", "environment", "sports"})

    def test_canonical_url_removes_tracking_but_keeps_meaningful_query(self):
        self.assertEqual(canonical_url("HTTPS://News.Example/a?story=3&utm_source=x&ref=y#top"), "https://news.example/a?story=3")

    def test_jsonld_graph_extraction_and_acceptance(self):
        html = b'''<html><head><link rel="canonical" href="https://example.org/story?utm_source=x">
        <script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","headline":"Headline","datePublished":"2026-11-12T10:00:00+05:30","articleSection":"Politics","articleBody":"A sufficiently long news report with facts, context, and details. A sufficiently long news report with facts, context, and details. A sufficiently long news report with facts, context, and details. A sufficiently long news report with facts, context, and details."}]}</script></head></html>'''
        response = HtmlResponse("https://example.org/story", body=html, encoding="utf-8", request=Request("https://example.org/story"))
        article = extract_article(response, SOURCES["abp_en"])
        self.assertEqual(article["canonical_url"], "https://example.org/story")
        self.assertEqual(article["section"], "Politics")
        self.assertEqual(valid_article(article), (True, None))

    def test_unmapped_or_unavailable_section_never_creates_category(self):
        self.assertNotIn("environment", {s["category"] for s in SOURCES["abp_en"]["sections"]})
        self.assertNotIn("politics", {s["category"] for s in SOURCES["abp_hi"]["sections"]})

    def test_equivalent_provider_sections_share_global_ids(self):
        def categories(adapter):
            return {section["label"]: section["category"] for section in SOURCES[adapter]["sections"]}

        self.assertEqual(categories("abp_en")["business"], categories("oneindia_en")["business"])
        self.assertEqual(categories("abp_hi")["sports"], categories("amarujala_hi")["sports"])
        self.assertEqual(categories("abp_bn")["business"], categories("news18_bn")["business"])
        self.assertEqual(categories("abp_mr")["sports"], categories("loksatta_mr")["क्रीडा"])

    def test_listing_selector_excludes_navigation_and_related_articles(self):
        html = b'''<html><body>
        <nav><a href="/elections/nav-story-123456">Politics nav</a></nav>
        <section class="explore-panel personal"><div class="top-article-panel">
          <a href="/elections/related-story-123456">Related politics story</a>
        </div></section>
        <section class="column-content"><section class="categoty-top-story">
          <a href="/business/primary-business-story-123456">Business story</a>
        </section></section>
        </body></html>'''
        response = HtmlResponse("https://news.abplive.com/business", body=html, encoding="utf-8", request=Request("https://news.abplive.com/business"))
        links = listing_hrefs(response, SOURCES["abp_en"])
        self.assertEqual(links, ["/business/primary-business-story-123456"])

    def test_amarujala_section_path_blocks_promo_and_cross_section_mappings(self):
        source = SOURCES["amarujala_hi"]
        sections = source["sections"]
        promo = "https://www.amarujala.com/photo-gallery/advertorial/oppo-k14-plus-overview-2026-11-12"
        self.assertFalse(any(article_matches_section(promo, source, section) for section in sections))

        business_story = "https://www.amarujala.com/business/business-diary/private-investment-and-jobs-2026-11-12"
        matching = [section["category"] for section in sections if article_matches_section(business_story, source, section)]
        self.assertEqual(matching, ["finance"])

        sports_story = "https://www.amarujala.com/sports/cricket/team-wins-match-2026-11-12"
        matching = [section["category"] for section in sections if article_matches_section(sports_story, source, section)]
        self.assertEqual(matching, ["sports"])

    def test_news18_listing_includes_editorial_feed_and_not_sidebar(self):
        html = b'''<html><body><div class="nwcol-9">
        <div class="compWrap"><div class="ctnw"><ul class="compfrrow"><li>
          <a href="/news/business/featured-story-2961601.html">Featured</a>
        </li></ul></div></div>
        <div class="cn-left"><ul class="cn-videoList"><li>
          <a href="/news/business/feed-story-2961602.html">Editorial feed</a>
        </li></ul></div>
        <ul class="cn-videoList"><li><a href="/news/business/sidebar-story-2961603.html">Sidebar</a></li></ul>
        <a href="/photogallery/business/gallery-2961604.html">Gallery</a>
        </div></body></html>'''
        response = HtmlResponse("https://bengali.news18.com/business/", body=html, encoding="utf-8", request=Request("https://bengali.news18.com/business/"))
        self.assertEqual(
            listing_hrefs(response, SOURCES["news18_bn"]),
            ["/news/business/featured-story-2961601.html", "/news/business/feed-story-2961602.html"],
        )
        self.assertEqual(SOURCES["news18_bn"]["max_listing_pages"], 5)

    def test_validation_rejects_short_body_and_bad_date(self):
        article = {"title": "Headline", "body": "brief", "published_at": "2026-11-12"}
        self.assertEqual(valid_article(article), (False, "body_under_200_chars"))
        article.update(body="A" * 250, published_at="unknown")
        self.assertEqual(valid_article(article), (False, "invalid_published_at"))

    def test_non_200_response_cannot_be_accepted_even_with_stale_jsonld(self):
        article = {"title": "Old article", "body": "A" * 250, "published_at": "2026-11-12T10:00:00+05:30"}
        self.assertEqual(validate_response_article(404, article), (False, "http_status_404"))

    def test_date_window_is_inclusive_utc_across_publisher_offsets(self):
        spider = NewsSpider(name="abp_en", adapter_id="abp_en", date_from="2026-11-12", date_to="2026-11-12")
        self.assertIsNone(spider._date_rejection("2026-11-13T05:29:59+05:30"))
        self.assertEqual(
            spider._date_rejection("2026-11-13T05:30:00+05:30"),
            "outside_date_window_utc:2026-11-12..2026-11-12",
        )


if __name__ == "__main__":
    unittest.main()
