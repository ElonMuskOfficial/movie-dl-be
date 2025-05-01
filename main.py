from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import urllib.parse

from models import APIResponse, SearchResult, DownloadButton, DownloadGroup, ExtractResponse
from utils import fetch_url, extract_image_url, extract_page_title, extract_download_buttons, extract_direct_url_from_scripts
from config import Settings, get_settings

app = FastAPI()

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is running."}

@app.get("/search")
def search_vegamovies_endpoint(
    query: str = Query(..., description="Search query for vegamovies"),
    settings: Settings = Depends(get_settings)
):
    search_url = f"{settings.vegamovies_base_url}/?s={urllib.parse.quote_plus(query)}"
    html = fetch_url(search_url)
    soup = BeautifulSoup(html, "html.parser")
    
    results = []
    for post in soup.select('.post-title a')[:5]:
        title = post.get_text(strip=True)
        link = post.get('href')
        thumb_elem = post.find_previous('div', class_='post-thumbnail')
        thumbnail = None
        if thumb_elem:
            img = thumb_elem.find('img')
            if img and img.get('src'):
                thumbnail = img['src']
        next_step = {
            "endpoint": "/extract",
            "params": {"url": link},
            "full_url": f"{settings.base_url}/extract?url={link}"
        }
        results.append(SearchResult(
            title=title,
            url=link,
            thumbnail=thumbnail,
            next_step=next_step
        ))
    
    return APIResponse(
        data=results,
        next_step="Call 'next_step' for a result to continue."
    )

@app.get("/extract")
def extract_entries(
    url: str = Query(..., description="Direct URL to the movie/series page"),
    settings: Settings = Depends(get_settings)
):
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    
    entry_inner = soup.find(class_="entry-inner") or soup.find(class_="entry-content")
    if not entry_inner:
        raise HTTPException(status_code=404, detail="Neither .entry-inner nor .entry-content found on the page.")
    
    image = extract_image_url(soup)
    page_title = extract_page_title(soup)
    
    results = []
    visited_titles = set()
    
    for p in entry_inner.find_all('p'):
        buttons = []
        for btn_text, btn_link in extract_download_buttons(p):
            next_step = {
                "endpoint": "/next-options",
                "params": {"url": btn_link},
                "full_url": f"{settings.base_url}/next-options?url={btn_link}"
            }
            buttons.append(DownloadButton(
                text=btn_text,
                link=btn_link,
                next_step=next_step
            ))
            
        if buttons:
            heading = p.find_previous(['h3', 'h5', 'h4', 'h2'])
            title = heading.get_text(strip=True) if heading else "Download Links"
            
            if title or not visited_titles:
                if title not in visited_titles:
                    results.append(DownloadGroup(title=title, buttons=buttons))
                    visited_titles.add(title)
                else:
                    results[-1].buttons.extend(buttons)
    
    first_button = results[0].buttons[0] if results and results[0].buttons else None
    return APIResponse(
        data=ExtractResponse(
            title=page_title,
            image=image,
            groups=results
        ),
        next_step="Call 'next_step' for a button to continue."
    )

@app.get("/next-options")
def get_next_options(
    url: str = Query(..., description="URL of the download button or group"),
    settings: Settings = Depends(get_settings)
):
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    entry_inner = soup.find(class_="entry-inner")
    
    if not entry_inner:
        return APIResponse(
            data=None,
            next_step={"endpoint": "/next-options", "params": {"url": url}},
            message="No further download groups/buttons found. Use /next-options for direct download extraction."
        )
    
    results = []
    visited_titles = set()
    
    for p in entry_inner.find_all('p'):
        buttons = []
        for btn_text, btn_link in extract_download_buttons(p):
            next_step = {
                "endpoint": "/resolve-downloads",
                "params": {"url": btn_link},
                "full_url": f"{settings.base_url}/resolve-downloads?url={btn_link}"
            }
            buttons.append(DownloadButton(
                text=btn_text,
                link=btn_link,
                next_step=next_step
            ))
            
        if buttons:
            prev = p.find_previous_sibling()
            title = prev.get_text(strip=True) if prev and prev.name in ['h3', 'h5', 'h4', 'h2'] else "Download Links"
            
            if title or not visited_titles:
                if title not in visited_titles:
                    results.append(DownloadGroup(title=title, buttons=buttons))
                    visited_titles.add(title)
                else:
                    results[-1].buttons.extend(buttons)
    
    first_button = results[0].buttons[0] if results and results[0].buttons else None
    return APIResponse(
        data=results,
        next_step="Call 'next_step' for a button to continue."
    )

@app.get("/resolve-downloads")
def resolve_download_links(url: str = Query(..., description="URL of the download button or group")):
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    
    direct_url = extract_direct_url_from_scripts(soup)
    if not direct_url:
        return APIResponse(
            data=None,
            next_step=None,
            message="No direct download URL found."
        )
    
    html2 = fetch_url(direct_url)
    soup2 = BeautifulSoup(html2, "html.parser")
    
    server_texts = [
        "Download [Server : 10Gbps]",
        "Download [Server : 1]",
        "Download [PixeLServer : 2]"
    ]
    
    links = []
    for a in soup2.find_all("a"):
        link_text = a.get_text(strip=True)
        if link_text in server_texts:
            href = a.get("href")
            if href:
                links.append({"text": link_text, "url": href})
    
    return APIResponse(
        data=links if links else None,
        next_step=None,
        message="No actual download links found." if not links else None
    )