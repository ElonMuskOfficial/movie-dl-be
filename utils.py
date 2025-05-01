import requests
from bs4 import BeautifulSoup
import time
import urllib3
from typing import Optional, List, Tuple
from fastapi import HTTPException

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_request_headers() -> dict:
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://google.com',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def fetch_url(url: str) -> str:
    """Fetch URL content with error handling and rate limiting."""
    try:
        # Using verify=False is required for some sites but should be used cautiously
        response = requests.get(url, headers=get_request_headers(), verify=False, timeout=10)  # Added timeout for safety
        response.raise_for_status()
        time.sleep(2)  # Rate limiting
        return response.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

def extract_image_url(soup: BeautifulSoup) -> Optional[str]:
    """Extract image URL from og:image or twitter:image meta tags."""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return og_image["content"]
    twitter_image = soup.find("meta", property="twitter:image")
    if twitter_image and twitter_image.get("content"):
        return twitter_image["content"]
    return None

def extract_page_title(soup: BeautifulSoup) -> Optional[str]:
    """Extract page title from h1.post-title or title tag."""
    main_title_elem = soup.find("h1", class_="post-title")
    if main_title_elem and main_title_elem.get_text(strip=True):
        return main_title_elem.get_text(strip=True)
    return soup.title.string.strip() if soup.title and soup.title.string else None

def extract_download_buttons(p_tag: BeautifulSoup) -> List[Tuple[str, str]]:
    """Extract download buttons from a paragraph tag."""
    buttons = []
    for a in p_tag.find_all('a'):
        rel = a.get('rel')
        if rel and set(rel) == {"nofollow", "noopener", "noreferrer"}:
            btn_text = a.get_text(strip=True)
            btn_link = a.get('href')
            buttons.append((btn_text, btn_link))
    return buttons

def extract_direct_url_from_scripts(soup: BeautifulSoup) -> Optional[str]:
    """Extract direct URL from JavaScript code."""
    import re
    scripts = [
        s for s in soup.find_all("script")
        if s.get("type") == "text/javascript" or s.get("type") is None
    ]
    for script in scripts:
        if script.string:
            match = re.search(r"var\s+url\s*=\s*['\"](.*?)['\"]", script.string)
            if match:
                return match.group(1)
    return None