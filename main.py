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
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string if soup.title else "No title found"
        return {"title": page_title}
    else:
        return {"error": f"Failed to fetch page, status code: {response.status_code}"}