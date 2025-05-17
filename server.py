from config import DESKTOP_USER_AGENTS
import requests
from bs4 import BeautifulSoup
import random
import time
import re
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the InsecureRequestWarning from urllib3
warnings.simplefilter('ignore', InsecureRequestWarning)

# Headers for server links page with fixed string formatting
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-GB,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": "Chromium;v=136, Google Chrome;v=136, Not.A/Brand;v=99",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "referrer-policy": "no-referrer"
}

def fetch_download_server(url):
    """
    Fetch and parse the server page to extract direct download URL.

    Args:
        url (str): The URL of the server button (e.g., https://vcloud.lol/...)

    Returns:
        dict: Details including page title, original URL, and direct download URL
    """
    if not url or not url.startswith('http'):
        return {"error": "Invalid URL provided"}

    # Use a random user agent for each request
    user_agent = random.choice(DESKTOP_USER_AGENTS)

    # Prepare headers with the selected user agent
    headers = HEADERS.copy()
    headers["User-Agent"] = user_agent

    try:
        # Add a small delay to avoid being blocked
        time.sleep(random.uniform(1, 3))

        # Make the request without cookies
        response = requests.get(
            url, 
            headers=headers,
            timeout=15,
            verify=False
        )

        # Check if the request was successful
        if response.status_code != 200:
            return {
                "error": f"Failed to fetch server page (Status code: {response.status_code})",
                "url": url
            }

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the page title
        title = soup.title.string.strip() if soup.title else "No title found"
        
        # Extract direct URL from scripts
        direct_url = extract_direct_url_from_scripts(soup)
        
        # If direct URL found, fetch the final download links
        download_links = []
        if direct_url:
            # Add random delay between requests
            delay = random.uniform(1.5, 4.0)
            time.sleep(delay)
            
            try:
                # Fetch the direct URL page
                direct_response = requests.get(
                    direct_url, 
                    headers=headers,
                    timeout=15,
                    verify=False
                )
                
                if direct_response.status_code == 200:
                    direct_soup = BeautifulSoup(direct_response.text, 'html.parser')
                    download_links = extract_download_links(direct_soup)
            except Exception as e:
                return {
                    "error": f"[server_links] Error fetching direct URL: {str(e)}",
                    "url": url,
                    "direct_url": direct_url
                }

        # Return details
        details = {
            "title": title,
            "url": url,
            "direct_url": direct_url,
            "download_links": download_links
        }

        return details

    except Exception as e:
        return {"error": f"[server_links] Error: {str(e)}", "url": url}


def extract_direct_url_from_scripts(soup):
    """
    Extract direct URL from JavaScript in the page.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        str: The direct URL extracted from script or None if not found
    """
    # Find all script tags
    scripts = [
        s for s in soup.find_all("script")
        if s.get("type") == "text/javascript" or s.get("type") is None
    ]
    
    # Look for var url = '...' pattern in scripts
    for script in scripts:
        if script.string:
            match = re.search(r"var\s+url\s*=\s*['\"](.*?)['\"]", script.string)
            if match:
                return match.group(1)
    
    return None


def extract_download_links(soup):
    """
    Extract final download links from the direct URL page.
    
    Args:
        soup: BeautifulSoup object of the direct URL page
        
    Returns:
        list: List of download links with their text
    """
    server_texts = [
        "Download [Server : 10Gbps]",
        "Download [Server : 1]",
        "Download [PixeLServer : 2]"
    ]
    
    links = []
    for a in soup.find_all("a"):
        link_text = a.get_text(strip=True)
        if link_text in server_texts:
            href = a.get("href")
            if href:
                links.append({
                    "label": link_text, 
                    "value": href
                })
    
    return links
