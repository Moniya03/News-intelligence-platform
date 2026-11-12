"""Verified, robots-allowed section URLs and explicit global taxonomy maps."""

MAPPING_VERSION = "global-category-v2"
AMARUJA_MAPPING_VERSION = "global-category-v3"
CATEGORY_ORDER = ("politics", "finance", "health", "science_technology", "environment", "sports")


def _sections(*entries):
    sections = []
    for entry in entries:
        url, category, label, *path_prefix = entry
        section = {"url": url, "category": category, "label": label}
        if path_prefix:
            section["article_path_prefix"] = path_prefix[0]
        sections.append(section)
    return sections


SOURCES = {
    "abp_en": {
        "family": "abp", "lang": "en", "domain": "news.abplive.com",
        "listing_selector": "section.column-content section.categoty-top-story a[href]",
        "sections": _sections(
            ("https://news.abplive.com/business", "finance", "business"),
            ("https://news.abplive.com/sports", "sports", "sports"),
            ("https://news.abplive.com/elections", "politics", "elections"),
            ("https://news.abplive.com/health", "health", "health"),
            ("https://news.abplive.com/science", "science_technology", "science"),
        ),
        "article_path": r"/(?:news|business|sports|elections|health|science|technology)/.+-\d{6,}$",
        "extractor_version": "abp-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "abp_hi": {
        "family": "abp", "lang": "hi", "domain": "www.abplive.com",
        "listing_selector": "section.column-content section.categoty-top-story a[href]",
        "sections": _sections(
            ("https://www.abplive.com/business", "finance", "business"),
            ("https://www.abplive.com/sports", "sports", "sports"),
            ("https://www.abplive.com/lifestyle/health", "health", "health"),
            ("https://www.abplive.com/technology", "science_technology", "technology"),
        ),
        "article_path": r"/(?:news|business|sports|lifestyle|technology|science)/.+-\d{6,}$",
        "extractor_version": "abp-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "abp_bn": {
        "family": "abp", "lang": "bn", "domain": "bengali.abplive.com",
        "listing_selector": "section.column-content section.categoty-top-story a[href]",
        "sections": _sections(
            ("https://bengali.abplive.com/business", "finance", "business"),
            ("https://bengali.abplive.com/sports", "sports", "sports"),
            ("https://bengali.abplive.com/news/politics", "politics", "politics"),
            ("https://bengali.abplive.com/lifestyle/health", "health", "health"),
            ("https://bengali.abplive.com/science", "science_technology", "science"),
        ),
        "article_path": r"/(?:business|sports|news|lifestyle|science|technology)/.+-\d{6,}$",
        "extractor_version": "abp-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "abp_mr": {
        "family": "abp", "lang": "mr", "domain": "marathi.abplive.com",
        "listing_selector": "section.column-content section.categoty-top-story a[href]",
        "sections": _sections(
            ("https://marathi.abplive.com/business", "finance", "business"),
            ("https://marathi.abplive.com/news/sports", "sports", "sports"),
            ("https://marathi.abplive.com/news/politics", "politics", "politics"),
            ("https://marathi.abplive.com/news/technology", "science_technology", "technology"),
        ),
        "article_path": r"/(?:news|business|sports|technology|politics)/.+-\d{6,}$",
        "extractor_version": "abp-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "oneindia_en": {
        "family": "oneindia", "lang": "en", "domain": "www.oneindia.com",
        "listing_selector": "div.oi-category-news-list.more-article-news > ul.clearfix > li.clearfix a[href]",
        "sections": _sections(
            ("https://www.oneindia.com/business/", "finance", "business"),
            ("https://www.oneindia.com/sports/", "sports", "sports"),
            ("https://www.oneindia.com/elections/", "politics", "elections"),
            ("https://www.oneindia.com/topic/health/", "health", "health"),
        ),
        "article_path": r"/.+-\d{5,}\.html$",
        "extractor_version": "oneindia-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "amarujala_hi": {
        "family": "amarujala", "lang": "hi", "domain": "www.amarujala.com",
        "listing_selector": "div.__common_listing > div#pageContainer > div.page#page0 > section.__main_listing_content a[href]",
        "sections": _sections(
            ("https://www.amarujala.com/business", "finance", "business", "/business/"),
            ("https://www.amarujala.com/sports", "sports", "sports", "/sports/"),
            ("https://www.amarujala.com/election", "politics", "election", "/election/"),
            ("https://www.amarujala.com/lifestyle/yoga-and-health", "health", "health", "/lifestyle/yoga-and-health/"),
            ("https://www.amarujala.com/technology", "science_technology", "technology", "/technology/"),
        ),
        "article_path": r"/.+-\d{4}-\d{2}-\d{2}$",
        "extractor_version": "amarujala-jsonld-v1", "mapping_version": AMARUJA_MAPPING_VERSION,
    },
    "news18_bn": {
        "family": "news18", "lang": "bn", "domain": "bengali.news18.com",
        "listing_selector": "div.nwcol-9 div.compWrap div.ctnw ul.compfrrow > li a[href], div.nwcol-9 div.cn-left > ul.cn-videoList > li a[href]",
        "pagination_selector": "div.nwcol-9 a[href*='/page-']",
        "pagination_pattern": r"/(?:business|sports)/page-(?P<page>\d+)/$",
        "max_listing_pages": 5,
        "sections": _sections(
            ("https://bengali.news18.com/news/business/", "finance", "business"),
            ("https://bengali.news18.com/news/sports/", "sports", "sports"),
        ),
        "article_path": r"/news/(?:business|sports|kolkata|west-bengal|international)/.+-\d{5,}\.html$",
        "extractor_version": "news18-jsonld-v1", "mapping_version": MAPPING_VERSION,
    },
    "loksatta_mr": {
        "family": "loksatta", "lang": "mr", "domain": "www.loksatta.com",
        "sections": _sections(
            ("https://www.loksatta.com/business/finance/", "finance", "finance"),
            ("https://www.loksatta.com/krida/", "sports", "क्रीडा"),
            ("https://www.loksatta.com/politics/", "politics", "politics"),
            ("https://www.loksatta.com/lifestyle/health-tips/", "health", "health tips"),
            ("https://www.loksatta.com/about/explained-environment/", "environment", "पर्यावरण"),
        ),
        "article_path": r"/.+-\d{5,}/?$",
        "extractor_version": "loksatta-html-v1", "mapping_version": MAPPING_VERSION,
        "listing_selector": "#article-main .left-sidebar > article.article a[href]",
    },
}
