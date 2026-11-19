import pytest
from backend.app.ingestion.crawler import EthicalCrawler

def test_ethical_crawler_init():
    crawler = EthicalCrawler()
    assert crawler.headers["User-Agent"] is not None
    assert crawler.ssl_context is not None

def test_fetch_darglobal_sitemap():
    crawler = EthicalCrawler()
    urls = crawler.fetch_darglobal_sitemap()
    assert isinstance(urls, list)
    # The live sitemap was verified to contain 479 URLs
    assert len(urls) > 50
    assert any("projects" in u for u in urls)

def test_inspect_url_security():
    crawler = EthicalCrawler()
    result = crawler.inspect_url_security("https://darglobal.co.uk/projects")
    assert "waf_detected" in result
    assert result["url"] == "https://darglobal.co.uk/projects"
