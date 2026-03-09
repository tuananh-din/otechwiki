import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import re
import asyncio
from typing import Optional
from app.services.url_utils import normalize_url, is_blacklisted_url

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def parse_sitemap(client: httpx.AsyncClient, sitemap_url: str, domain: str, limit: int, found_urls: set[str], visited_sitemaps: set[str]):
    """Recursively parse sitemaps and sitemap indexes."""
    if sitemap_url in visited_sitemaps or len(found_urls) >= limit:
        return
    visited_sitemaps.add(sitemap_url)

    try:
        resp = await client.get(sitemap_url)
        if resp.status_code != 200:
            return
        
        root = ET.fromstring(resp.content)
        namespace = ""
        if "}" in root.tag:
            namespace = root.tag.split("}")[0] + "}"
        
        tag_name = root.tag.lower()
        
        # 1. Handle Sitemap Index
        if "sitemapindex" in tag_name:
            for sitemap in root.findall(f".//{namespace}sitemap"):
                loc = sitemap.find(f"{namespace}loc")
                if loc is not None and loc.text:
                    await parse_sitemap(client, loc.text.strip(), domain, limit, found_urls, visited_sitemaps)
                    if len(found_urls) >= limit:
                        return
                        
        # 2. Handle Sitemap
        elif "urlset" in tag_name:
            for url_tag in root.findall(f".//{namespace}url"):
                loc = url_tag.find(f"{namespace}loc")
                if loc is not None and loc.text:
                    url = loc.text.strip().rstrip("/")
                    if urlparse(url).netloc == domain:
                        found_urls.add(url)
                        if len(found_urls) >= limit:
                            return
    except Exception:
        pass

async def discover_urls_recursive(
    homepage_url: str, 
    max_depth: int = 5, 
    limit: int = 500,
    current_depth: int = 0,
    visited: Optional[set[str]] = None,
    found_urls: Optional[set[str]] = None
) -> set[str]:
    """
    Recursively discover sub-pages starting from a homepage URL.
    """
    if visited is None:
        visited = set()
    if found_urls is None:
        found_urls = set()

    clean_homepage = homepage_url.rstrip("/")
    if clean_homepage in visited or len(found_urls) >= limit or current_depth > max_depth:
        return found_urls

    visited.add(clean_homepage)
    domain = urlparse(homepage_url).netloc
    
    # Priority keywords for filtering
    product_patterns = [
        re.compile(p, re.IGNORECASE) 
        for p in [r"/product/", r"/p/", r"/item/", r"/san-pham/", r"/detail/"]
    ]

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(homepage_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                new_links = []
                
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(homepage_url, href)
                    parsed_url = urlparse(full_url)
                    
                    # Basic filters: same domain, http(s), no fragment, not a file
                    path = parsed_url.path.lower()
                    is_blacklisted_file = any(path.endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".zip", ".docx", ".css", ".js", ".svg"])
                    
                    if (parsed_url.netloc == domain and 
                        parsed_url.scheme in ["http", "https"] and 
                        not is_blacklisted_url(full_url)):
                        
                        clean_url = normalize_url(full_url)
                        
                        if clean_url != clean_homepage and clean_url not in visited:
                            # Prioritize product-like URLs
                            is_product = any(pattern.search(clean_url) for pattern in product_patterns)
                            if is_product:
                                found_urls.add(clean_url)
                            else:
                                if current_depth < max_depth:
                                    new_links.append(clean_url)
                                elif len(found_urls) < limit:
                                    found_urls.add(clean_url)
                            
                            if len(found_urls) >= limit:
                                return found_urls

                # If we haven't reached depth limit, recurse
                if current_depth < max_depth:
                    for link in new_links[:100]: # Increased branching factor
                        if len(found_urls) >= limit:
                            break
                        await discover_urls_recursive(link, max_depth, limit, current_depth + 1, visited, found_urls)

    except Exception:
        pass

    return found_urls

async def discover_urls(homepage_url: str, limit: int = 500, depth: int = 5) -> list[str]:
    """
    Find sub-pages starting from a homepage URL.
    Tries Sitemap first (Recursive), then falls back to Recursive BFS.
    """
    domain = urlparse(homepage_url).netloc
    found_urls = set()
    visited_sitemaps = set()
    
    # 1. Try to find Sitemaps
    sitemap_candidates = [
        urljoin(homepage_url, "/sitemap.xml"),
        urljoin(homepage_url, "/sitemap_index.xml")
    ]
    
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            # Check robots.txt
            robots_resp = await client.get(urljoin(homepage_url, "/robots.txt"))
            if robots_resp.status_code == 200:
                matches = re.findall(r"Sitemap:\s*(https?://[^\s]+)", robots_resp.text, re.IGNORECASE)
                sitemap_candidates.extend(matches)
            
            # De-duplicate candidates
            sitemap_candidates = list(set(sitemap_candidates))
            
            # Recursive parse all candidates
            for s_url in sitemap_candidates:
                await parse_sitemap(client, s_url, domain, limit, found_urls, visited_sitemaps)
                if len(found_urls) >= limit:
                    break
    except Exception:
        pass

    if len(found_urls) >= limit:
        return sorted(list(found_urls))[:limit]

    # 2. Deep Discovery BFS if sitemap wasn't enough
    found_urls = await discover_urls_recursive(
        homepage_url=homepage_url, 
        max_depth=depth, 
        limit=limit, 
        found_urls=found_urls
    )

    return sorted(list(found_urls))[:limit]
