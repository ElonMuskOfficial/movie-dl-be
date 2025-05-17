from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from server import fetch_download_server
from fastapi import Query
from bs4 import BeautifulSoup
import cloudscraper
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/fetch")
def fetch_url():
    url = "https://vcloud.lol/2syw1ybxwaaxlkk"
    # Try advanced browser emulation
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    # Retry logic
    response = None
    for _ in range(3):
        response = scraper.get(url, headers=headers)
        if response.status_code == 200:
            break
    if response and response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string if soup.title else "No title found"
        return {"title": page_title}
    else:
        # Print response body for debugging
        error_body = response.text if response else "No response received"
        print(error_body)  # Print response body for debugging
        return {"error": f"Failed to fetch page, status code: {response.status_code if response else 'N/A'}", "body": error_body}