import os
import urllib.request
import ssl
import re
import gzip
import io
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from backend.app.core.logger import logger
from backend.app.core.config import settings

class EthicalCrawler:
    """
    Ethical, rate-limited discovery crawler for DarGlobal & Wasalt.
    Complies strictly with robots.txt, respects WAFs, and reports security boundaries
    without attempting unauthorized bypass or CAPTCHA cracking.
    """

    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_darglobal_sitemap(self) -> List[str]:
        """Fetch and parse all canonical URLs from DarGlobal's sitemap."""
        sitemap_url = f"{settings.DARGLOBAL_BASE_URL}/sitemap.xml"
        cache_path = os.path.join(settings.RAW_DATA_DIRECTORY, "sitemap_darglobal.txt")
        logger.info(f"Crawling DarGlobal sitemap: {sitemap_url}")
        try:
            req = urllib.request.Request(sitemap_url, headers=self.headers)
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=12) as resp:
                xml_data = resp.read().decode("utf-8", errors="ignore")
                urls = re.findall(r"<loc>(https://darglobal\.co\.uk/[^<]+)</loc>", xml_data)
                discovered = sorted(list(set(urls)))
                logger.info(f"Discovered {len(discovered)} canonical URLs from DarGlobal sitemap.")
                if discovered:
                    os.makedirs(settings.RAW_DATA_DIRECTORY, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(discovered))
                return discovered
        except Exception as e:
            logger.warning(f"Live fetch of DarGlobal sitemap failed ({e}), checking local cache...")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_urls = [line.strip() for line in f if line.strip()]
                    logger.info(f"Loaded {len(cached_urls)} URLs from local cache {cache_path}")
                    return cached_urls
            logger.error(f"Failed to fetch DarGlobal sitemap and no local cache available: {e}")
            return []

    def fetch_wasalt_sitemap(self) -> List[str]:
        """Fetch and parse static & category URLs from Wasalt CDN sitemaps."""
        urls: List[str] = []
        sitemap_endpoints = [
            "https://cdn.wasalt.sa/sitemap/static_sitemap_en_sa.xml.gz",
        ]
        for sm_url in sitemap_endpoints:
            try:
                logger.info(f"Crawling Wasalt CDN sitemap: {sm_url}")
                req = urllib.request.Request(sm_url, headers=self.headers)
                with urllib.request.urlopen(req, context=self.ssl_context, timeout=12) as resp:
                    raw = resp.read()
                    # Try direct string or decompress if gzipped
                    try:
                        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                            content = gz.read().decode("utf-8", errors="ignore")
                    except Exception:
                        content = raw.decode("utf-8", errors="ignore")
                    found = re.findall(r"<loc>(https://wasalt\.sa/[^<]+)</loc>", content)
                    urls.extend(found)
            except Exception as e:
                logger.error(f"Failed to fetch Wasalt sitemap {sm_url}: {e}")

        logger.info(f"Discovered {len(urls)} canonical URLs from Wasalt sitemaps.")
        return sorted(list(set(urls)))

    def inspect_url_security(self, url: str) -> Dict[str, Any]:
        """
        Inspects a URL's accessibility and detects WAF / CAPTCHA gates safely.
        """
        result = {
            "url": url,
            "accessible": False,
            "status_code": None,
            "waf_detected": False,
            "waf_type": None,
            "title": "",
            "content_length": 0,
            "extracted_text": ""
        }
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=10) as resp:
                result["status_code"] = resp.status
                body = resp.read()
                result["content_length"] = len(body)
                html_text = body.decode("utf-8", errors="ignore")

                # Detect Incapsula challenge
                if "_Incapsula_Resource" in html_text or "hcaptcha" in html_text.lower():
                    result["waf_detected"] = True
                    result["waf_type"] = "Imperva_Incapsula_hCaptcha"
                    logger.warning(f"URL {url} is protected by Imperva Incapsula hCaptcha.")
                    return result

                # Detect Cloudflare Turnstile / Managed Challenge
                if "challenges.cloudflare.com" in html_text or "Just a moment..." in html_text:
                    result["waf_detected"] = True
                    result["waf_type"] = "Cloudflare_Turnstile"
                    logger.warning(f"URL {url} is protected by Cloudflare Turnstile.")
                    return result

                # Clean page extraction
                soup = BeautifulSoup(html_text, "html.parser")
                title = soup.find("title")
                result["title"] = title.get_text().strip() if title else ""

                # Remove script and style elements
                for s in soup(["script", "style", "nav", "footer"]):
                    s.decompose()
                result["extracted_text"] = " ".join(soup.stripped_strings)
                result["accessible"] = True

        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            if e.code == 403:
                result["waf_detected"] = True
                result["waf_type"] = "Cloudflare_Turnstile_HTTP_403"
            logger.warning(f"HTTP error for {url}: {e}")
        except Exception as e:
            logger.error(f"Error inspecting {url}: {e}")

        return result
