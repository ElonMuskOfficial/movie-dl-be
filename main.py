# Standard library imports
import os
import time
import random
import gzip

# Third-party imports
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
from bs4 import BeautifulSoup
import zstandard as zstd
import brotli

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Optional, Dict, Any

# List of common desktop user agents
desktop_common_ua = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.6",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.2",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.4",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.",
    "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3"
]

def random_timeout() -> None:
    """Add a random delay to avoid bot detection."""
    time.sleep(1 + float(random.randint(1, 5)/random.randint(5, 13)))

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy"}


@app.get("/scrape")
async def scrape_url_get(url: str, output_file: Optional[str] = "index.html") -> Dict[str, Any]:
    """Endpoint to scrape a URL and save the content to a file.
    
    Args:
        url: The URL to scrape
        output_file: The file to save the scraped content to
        
    Returns:
        A dictionary with the status, message, title, and file path
    """
    return await do_scrape(url, output_file)

@app.get("/view-html", response_class=HTMLResponse)
async def view_html(file_path: Optional[str] = "index.html") -> HTMLResponse:
    """Endpoint to view the HTML content of a file.
    
    Args:
        file_path: The path to the HTML file to view
        
    Returns:
        The HTML content as an HTMLResponse
        
    Raises:
        HTTPException: If the file doesn't exist or can't be read
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")
        
        # Read the HTML content
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")



def decompress_content(response: requests.Response) -> str:
    """Decompress content based on the content-encoding header.
    
    Args:
        response: The response object from requests
        
    Returns:
        The decompressed content as a string
    """
    content_encoding = response.headers.get('content-encoding', '').lower()
    
    try:
        if 'zstd' in content_encoding:
            dctx = zstd.ZstdDecompressor()
            decompressed_content = dctx.decompress(response.content)
            return decompressed_content.decode('utf-8', errors='ignore')
        elif 'gzip' in content_encoding:
            decompressed_content = gzip.decompress(response.content)
            return decompressed_content.decode('utf-8', errors='ignore')
        elif 'br' in content_encoding:
            decompressed_content = brotli.decompress(response.content)
            return decompressed_content.decode('utf-8', errors='ignore')
        else:
            # No compression or unknown compression
            return response.text
    except Exception as e:
        print(f"Error decompressing content ({content_encoding}): {e}")
        return response.text


def get_browser_headers() -> Dict[str, str]:
    """Generate headers that mimic a real browser.
    
    Returns:
        A dictionary of HTTP headers
    """
    user_agent = random.choice(desktop_common_ua)
    return {
        "User-Agent": user_agent,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    }


async def do_scrape(url: str, output_file: str = "index.html") -> Dict[str, Any]:
    """Scrape a vcloud.lol URL and save the content to a file.
    
    Args:
        url: The vcloud.lol URL to scrape
        output_file: The file to save the scraped content to
        
    Returns:
        A dictionary with the status, message, title, and file path
        
    Raises:
        HTTPException: If there's an error scraping the URL
    """
    try:
        # Verify it's a vcloud.lol URL
        if 'vcloud.lol' not in url:
            raise ValueError("This scraper only supports vcloud.lol URLs")
            
        # Create a session that doesn't verify SSL certificates
        session = requests.Session()
        session.verify = False
        
        # Add random timeout to avoid detection
        random_timeout()
        
        # Add headers to mimic a browser
        headers = get_browser_headers()
        
        # Make the request
        response = session.get(url, headers=headers)
        response.raise_for_status()
        
        # Handle compressed content
        html_content = decompress_content(response)
        
        # Save the HTML content to a file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract basic information
        title = soup.title.text if soup.title else "No title found"
        
        return {
            "status": "success",
            "message": f"Successfully scraped {url} and saved to {output_file}",
            "title": title,
            "file_path": os.path.abspath(output_file)
        }
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.RequestException as e:
        # Handle request errors
        raise HTTPException(status_code=502, detail=f"Error fetching URL: {str(e)}")
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")