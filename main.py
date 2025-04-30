from typing import Union
import requests
from bs4 import BeautifulSoup
import urllib.parse

from fastapi import FastAPI, Query

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/search")
def search_vegamovies_endpoint(query: str = Query(..., description="Search query for vegamovies")):
    search_url = f"https://vegamovies.bot/?s={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(search_url, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"results": [], "error": str(e)}
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for post in soup.select('.post-title a')[:5]:
        title = post.get_text(strip=True)
        link = post.get('href')
        results.append({
            "title": title,
            "url": link,
            "next_step": {
                "endpoint": "/extract",
                "params": {"url": link}
            }
        })
    return {"results": results, "next_step": "Call 'next_step' for a result to continue."}


@app.get("/extract")
def extract_entries(url: str = Query(..., description="Direct URL to the movie/series page")):
    try:
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"entries": [], "error": str(e)}
    soup = BeautifulSoup(resp.text, "html.parser")
    entry_inner = soup.find(class_="entry-inner")
    if not entry_inner:
        return {"entries": [], "message": ".entry-inner not found on the page."}
    results = []
    visited_titles = set()
    for p in entry_inner.find_all('p'):
        buttons = []
        for a in p.find_all('a'):
            rel = a.get('rel')
            if rel and set(rel) == {"nofollow", "noopener", "noreferrer"}:
                btn_text = a.get_text(strip=True)
                btn_link = a.get('href')
                buttons.append({
                    "text": btn_text,
                    "link": btn_link,
                    "next_step": {
                        "endpoint": "/next-options",
                        "params": {"url": btn_link}
                    }
                })
        if buttons:
            heading = p.find_previous(['h3', 'h5', 'h4', 'h2'])
            title = heading.get_text(strip=True) if heading else "Download Links"
            if title or not visited_titles:
                if title not in visited_titles:
                    results.append({"title": title, "buttons": buttons})
                    visited_titles.add(title)
                else:
                    results[-1]["buttons"].extend(buttons)
    return {
        "entries": results,
        "next_step": "Call 'next_step' for a button to continue."
    }


@app.get("/next-options")
def get_next_options(url: str = Query(..., description="URL of the download button or group")):
    try:
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"entries": [], "error": str(e)}
    soup = BeautifulSoup(resp.text, "html.parser")
    entry_inner = soup.find(class_="entry-inner")
    if entry_inner:
        results = []
        visited_titles = set()
        for p in entry_inner.find_all('p'):
            buttons = []
            for a in p.find_all('a'):
                rel = a.get('rel')
                if rel and set(rel) == {"nofollow", "noopener", "noreferrer"}:
                    btn_text = a.get_text(strip=True)
                    btn_link = a.get('href')
                    buttons.append({
                        "text": btn_text,
                        "link": btn_link,
                        "next_step": {
                            "endpoint": "/next-options",
                            "params": {"url": btn_link}
                        }
                    })
            if buttons:
                prev = p.find_previous_sibling()
                if prev and prev.name in ['h3', 'h5', 'h4', 'h2']:
                    title = prev.get_text(strip=True)
                else:
                    title = "Download Links"
                if title or not visited_titles:
                    if title not in visited_titles:
                        results.append({"title": title, "buttons": buttons})
                        visited_titles.add(title)
                    else:
                        results[-1]["buttons"].extend(buttons)
        if results:
            return {
                "type": "groups",
                "entries": results,
                "next_step": "Call 'next_step' for a button to continue."
            }
    # If no entry-inner or no groups/buttons, return a message
    return {
        "type": "no_groups",
        "message": "No further download groups/buttons found. Use /resolve-downloads for direct download extraction.",
        "previous_link": url,
        "next_step": {
            "endpoint": "/resolve-downloads",
            "params": {"url": url}
        }
    }


@app.get("/resolve-downloads")
def resolve_download_links(url: str = Query(..., description="URL of the download button or group")):
    import re
    try:
        # Step 1: Fetch the button/group page
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"entries": [], "error": str(e)}
    soup = BeautifulSoup(resp.text, "html.parser")
    # Step 2: Extract direct download URL from scripts (like extract_var_url_from_scripts)
    scripts = [
        s for s in soup.find_all("script")
        if s.get("type") == "text/javascript" or s.get("type") is None
    ]
    direct_url = None
    for script in scripts:
        if script.string:
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", script.string)
            if match:
                direct_url = match.group(1)
                break
    if direct_url:
        # Step 3: Fetch the direct download page and extract actual download links (like extract_actual_download_links)
        try:
            resp2 = requests.get(direct_url, verify=False)
            resp2.raise_for_status()
        except requests.RequestException as e:
            return {"entries": [], "error": f"Failed to fetch direct URL: {str(e)}"}
        soup2 = BeautifulSoup(resp2.text, "html.parser")
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
        if links:
            return {
                "type": "download_links",
                "entries": links,
                "direct_url": direct_url,
                "next_step": None
            }
        else:
            # No actual download links found, return direct_url as fallback
            return {
                "type": "direct_url_fallback",
                "direct_url": direct_url,
                "next_step": None
            }
    # Step 4: If no direct download URL found, return previous link as fallback (do NOT fetch again)
    return {
        "type": "previous_link_fallback",
        "previous_link": url,
        "next_step": None
    }