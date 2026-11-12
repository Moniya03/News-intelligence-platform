from scrapy import Spider

from scrapers.sources import SOURCES
from scrapers.spiders.news import NewsSpider


def _spider_class(adapter_id):
    return type(adapter_id, (NewsSpider,), {"name": adapter_id, "adapter_id": adapter_id})


for _adapter_id in SOURCES:
    globals()[_adapter_id] = _spider_class(_adapter_id)

__all__ = list(SOURCES)
