import requests
from bs4 import BeautifulSoup
from typing import List
from dataclasses import dataclass
import logging
import questionary
import re

logging.basicConfig(level=logging.INFO)

@dataclass
class DownloadButton:
    text: str
    link: str

@dataclass
class EntryInner:
    title: str
    buttons: List[DownloadButton]

class BaseEntryExtractor:
    def extract(self, soup) -> list:
        raise NotImplementedError

class StandardEntryExtractor(BaseEntryExtractor):
    """Extractor for main/movie/series pages (loose heading association)."""
    def extract(self, soup) -> list:
        entry_inner = soup.find(class_="entry-inner")
        if not entry_inner:
            logging.warning(".entry-inner not found on the page.")
            return []
        results = []
        visited_titles = set()
        for p in entry_inner.find_all('p'):
            buttons = []
            for a in p.find_all('a'):
                rel = a.get('rel')
                if rel and set(rel) == {"nofollow", "noopener", "noreferrer"}:
                    btn_text = a.get_text(strip=True)
                    btn_link = a.get('href')
                    buttons.append(DownloadButton(text=btn_text, link=btn_link))
            if buttons:
                # Loose: find any previous heading
                heading = p.find_previous(['h3', 'h5', 'h4', 'h2'])
                title = heading.get_text(strip=True) if heading else "Download Links"
                if title or not visited_titles:
                    if title not in visited_titles:
                        results.append(EntryInner(title=title, buttons=buttons))
                        visited_titles.add(title)
                    else:
                        results[-1].buttons.extend(buttons)
        return results

class StrictEntryExtractor(BaseEntryExtractor):
    """Extractor for drill-down/next_results pages (only direct sibling heading or default title)."""
    def extract(self, soup) -> list:
        entry_inner = soup.find(class_="entry-inner")
        if not entry_inner:
            logging.warning(".entry-inner not found on the page.")
            return []
        results = []
        visited_titles = set()
        for p in entry_inner.find_all('p'):
            buttons = []
            for a in p.find_all('a'):
                rel = a.get('rel')
                if rel and set(rel) == {"nofollow", "noopener", "noreferrer"}:
                    btn_text = a.get_text(strip=True)
                    btn_link = a.get('href')
                    buttons.append(DownloadButton(text=btn_text, link=btn_link))
            if buttons:
                prev = p.find_previous_sibling()
                if prev and prev.name in ['h3', 'h5', 'h4', 'h2']:
                    title = prev.get_text(strip=True)
                else:
                    title = "Download Links"
                if title or not visited_titles:
                    if title not in visited_titles:
                        results.append(EntryInner(title=title, buttons=buttons))
                        visited_titles.add(title)
                    else:
                        results[-1].buttons.extend(buttons)
        return results

# Helper function to fetch and extract entries
import urllib.parse

def fetch_and_extract(url: str, extractor: BaseEntryExtractor) -> list:
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch URL: {url} | Error: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    return extractor.extract(soup)

def search_vegamovies(query: str, max_results: int = 5):
    """Searches vegamovies.bot for the given query and returns up to max_results (title, link) pairs."""
    import urllib.parse
    search_url = f"https://vegamovies.bot/?s={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(search_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch search results: {search_url} | Error: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    # Results are typically in <div class="post-title"> or similar
    results = []
    for post in soup.select('.post-title a')[:max_results]:
        title = post.get_text(strip=True)
        link = post.get('href')
        results.append((title, link))
    return results

def extract_var_url_from_scripts(page_url: str) -> str:
    """Fetches the page, searches all <script type='text/javascript'> tags for `var url = ...` and returns the value if found."""
    try:
        resp = requests.get(page_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch URL: {page_url} | Error: {e}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    # Only consider <script> tags with type="text/javascript" (or no type, which defaults to text/javascript)
    scripts = [
        s for s in soup.find_all("script")
        if s.get("type") == "text/javascript" or s.get("type") is None
    ]
    for script in scripts:
        if script.string:
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", script.string)
            if match:
                return match.group(1)
    logging.info("No var url assignment found in any <script type='text/javascript'> tag.")
    return None

def extract_actual_download_links(page_url: str) -> list:
    """Fetches the page and returns a list of (text, href) for all download buttons with specific server text."""
    try:
        resp = requests.get(page_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch URL: {page_url} | Error: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    server_texts = ["Download [Server : 10Gbps]", "Download [Server : 1]", "Download [PixeLServer : 2]"]
    links = []
    for a in soup.find_all("a"):
        link_text = a.get_text(strip=True)
        if link_text in server_texts:
            href = a.get("href")
            if href:
                links.append((link_text, href))
    return links

def main():
    # Always start with Vegamovies search
    search_query = questionary.text("Enter search query").ask()
    search_results = search_vegamovies(search_query)
    if not search_results:
        print("No search results found.")
        return
    # Let user pick a URL from search results
    choice = questionary.select(
        "Select a result:",
        choices=[f"{title} | {link}" for title, link in search_results]
    ).ask()
    # Extract the selected URL
    selected_url = next(link for title, link in search_results if f"{title} | {link}" == choice)
    # Continue with the original logic using selected_url
    results = fetch_and_extract(selected_url, StandardEntryExtractor())
    if not results:
        print("No entries found.")
        return
    # Step 1: Select entry
    entry_choice = questionary.select(
        "Select a title:",
        choices=[entry.title for entry in results]
    ).ask()
    selected_entry = next(entry for entry in results if entry.title == entry_choice)
    # Step 2: Select button
    button_choice = questionary.select(
        "Select a button:",
        choices=[f"{btn.text} | {btn.link}" for btn in selected_entry.buttons]
    ).ask()
    selected_button = next(btn for btn in selected_entry.buttons if f"{btn.text} | {btn.link}" == button_choice)
    print(f"\nYou selected: {selected_button.text}")
    print(f"URL: {selected_button.link}")

    # --- New: Drill down if button link is another page with entry-inner ---
    next_results = fetch_and_extract(selected_button.link, StrictEntryExtractor())
    if next_results:
        print("\nFound additional entries at the next URL:")
        # Step 3: Select a group/title from next_results
        next_entry_choice = questionary.select(
            "Select a download group:",
            choices=[entry.title for entry in next_results]
        ).ask()
        next_selected_entry = next(entry for entry in next_results if entry.title == next_entry_choice)
        # Step 4: Select a button from the chosen group
        next_button_choice = questionary.select(
            "Select a button:",
            choices=[f"{btn.text} | {btn.link}" for btn in next_selected_entry.buttons]
        ).ask()
        next_selected_button = next(
            btn for btn in next_selected_entry.buttons if f"{btn.text} | {btn.link}" == next_button_choice
        )
        print(f"\nYou selected: {next_selected_button.text}")
        print(f"URL: {next_selected_button.link}")
        # --- Extract var url from the final page ---
        direct_url = extract_var_url_from_scripts(next_selected_button.link)
        if direct_url:
            print(f"\nDirect download URL found: {direct_url}")
            # Find all actual download links on the direct_url page
            download_links = extract_actual_download_links(direct_url)
            if download_links:
                print("\nActual download links found:")
                for text, href in download_links:
                    print(f"{text}: {href}")
            else:
                print("No actual download links found on the page.")
        else:
            print("\nNo direct download URL found in scripts. Using previous page URL:")
            print(f"{next_selected_button.link}")
            # Do NOT fetch the previous page again
    else:
        print("\nNo additional entries found at the next URL.")

if __name__ == "__main__":
    main()
