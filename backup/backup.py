import requests
from bs4 import BeautifulSoup
import re
import time

try:
    import inquirer
except ImportError:
    inquirer = None

def get_var_url_from_html(html):
    # Extracts var url = ... from <script> tags in the HTML, robust to formatting
    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    for idx, script in enumerate(script_tags):
        script_content = script.get_text()  # More robust than script.string
        print(f"\n[DEBUG] Script tag #{idx} content:\n{script_content}\n")
        if script_content:
            # Regex: var url = '...'; or var url = "...";
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", script_content)
            print(f"[DEBUG] Regex match: {match.group(1) if match else 'None'}")
            if match:
                return match.group(1)
    print("[DEBUG] No var url found in any <script> tag.")
    return None

def get_h4_p_button_options(soup):
    # Returns a list of (label, link) tuples for <h4> immediately followed by <p> with <a> buttons
    options = []
    # --- Extract var url from any <script> tags ---
    script_tags = soup.find_all("script")
    js_urls = []
    for script in script_tags:
        script_content = script.get_text()
        if script_content:
            match = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+)['\"]", script_content)
            if match:
                js_urls.append(match.group(1))
    if js_urls:
        for idx, url in enumerate(js_urls, 1):
            label = f"[JS var url #{idx}]"
            options.append((label, url))
    # --- Standard <h4><p><a> logic ---
    for h4 in soup.find_all("h4"):
        next_elem = h4.find_next_sibling()
        if next_elem and next_elem.name == "p":
            buttons = next_elem.find_all("a")
            h4_text = h4.get_text(strip=True)
            for btn in buttons:
                btn_text = btn.get_text(strip=True)
                link = btn.get('href', '')
                label = f"{h4_text} | {btn_text}"
                options.append((label, link))
    return options

def save_html_to_file(html, filename="debug_fetched.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Saved fetched HTML to {filename}")

def fetch_and_save_var_url(var_url, filename="debug_fetched.html"):
    import requests
    try:
        response = requests.get(var_url)
        response.raise_for_status()
        with open(filename, "w", encoding=response.encoding or "utf-8") as f:
            f.write(response.text)
        print(f"[INFO] Saved fetched content from var url to {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch or save var url: {e}")

def list_h4_p_buttons_true_order(soup):
    # Only consider <h4> directly followed by <p> (true sibling order)
    found_any = False
    for idx, h4 in enumerate(soup.find_all("h4"), 1):
        next_elem = h4.find_next_sibling()
        if next_elem and next_elem.name == "p":
            buttons = next_elem.find_all("a")
            if buttons:
                found_any = True
                print(f"<h4> tag #{idx}: {h4.get_text(strip=True)[:80]}")
                print(f"    Found {len(buttons)} <a> buttons in immediate sibling <p>:")
                for bidx, btn in enumerate(buttons, 1):
                    link = btn.get('href', '')
                    print(f"      Button #{bidx}: {btn.get_text(strip=True)[:80]} | Link: {link}")
    if not found_any:
        print("[INFO] No <h4> directly followed by <p> with buttons found.")

def fetch_download_buttons_from_var_url(var_url, labels=None):
    """
    Fetches the page at var_url and extracts download button links matching the given labels.
    Returns a dict {label: href}.
    """
    import requests
    from bs4 import BeautifulSoup
    if labels is None:
        labels = ["Download [Server : 10Gbps]", "Download [Server : 1]"]
    try:
        resp = requests.get(var_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = {}
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            if text in labels:
                results[text] = a.get("href")
        # Fill missing
        for label in labels:
            if label not in results:
                results[label] = None
        return results
    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse {var_url}: {e}")
        return {label: None for label in (labels or [])}

def main():
    url = "https://vegamovies.bot/download-peaky-blinders-season-1-6-hindi-org-480p-720p-1080p-bluray/"
    response = requests.get(url)
    if response.status_code == 200:
        print("[INFO] Page fetched successfully!")
        soup = BeautifulSoup(response.text, "html.parser")
        article = soup.find("article")
        if article:
            hr = article.find("hr")
            if hr:
                descendants = list(article.descendants)
                hr_index = descendants.index(hr)
                h3_tags = [tag for tag in descendants[hr_index+1:] if getattr(tag, 'name', None) == 'h3']
                options = []
                option_map = {}
                for idx, h3 in enumerate(h3_tags, 1):
                    h3_text = h3.get_text(strip=True)
                    for sib in h3.find_all_next():
                        if sib == h3:
                            continue
                        if getattr(sib, 'name', None) == 'h3':
                            break
                        if getattr(sib, 'name', None) == 'a':
                            btn_text = sib.get_text(strip=True)
                            link = sib.get('href', '')
                            label = f"{h3_text} | {btn_text}"
                            options.append(label)
                            option_map[label] = link
                if not options:
                    print("[WARN] No button links found to select.")
                    return
                if inquirer is None:
                    print("[ERROR] 'inquirer' package is not installed. Please install it with: pip install inquirer")
                    return
                question = [
                    inquirer.List(
                        'choice',
                        message="Select the button link you want to fetch:",
                        choices=options
                    )
                ]
                answer = inquirer.prompt(question)
                if answer and 'choice' in answer:
                    selected_label = answer['choice']
                    selected_link = option_map[selected_label]
                    print(f"\n[RESULT] You selected: {selected_label}\nLink: {selected_link}")
                    # Fetch the selected link and list h4/p pairs in true order
                    print(f"\n[INFO] Fetching selected link...")
                    try:
                        link_resp = requests.get(selected_link)
                        if link_resp.status_code == 200:
                            print("[INFO] Link fetched successfully!\n")
                            link_soup = BeautifulSoup(link_resp.text, "html.parser")
                            print("[INFO] Listing all <h4> tags with immediate sibling <p> containing buttons on the fetched page:\n")
                            h4p_options = get_h4_p_button_options(link_soup)
                            if h4p_options:
                                h4p_labels = [label for label, _ in h4p_options]
                                h4p_map = {label: link for label, link in h4p_options}
                                question2 = [
                                    inquirer.List(
                                        'choice',
                                        message="Select the <h4>/<p> button link you want to fetch:",
                                        choices=h4p_labels
                                    )
                                ]
                                answer2 = inquirer.prompt(question2)
                                if answer2 and 'choice' in answer2:
                                    selected_label2 = answer2['choice']
                                    selected_link2 = h4p_map[selected_label2]
                                    print(f"\n[RESULT] You selected: {selected_label2}\nLink: {selected_link2}")
                                    # Wait 1 second before fetching (to allow for loader)
                                    print("[INFO] Waiting 1 second for loader...")
                                    time.sleep(1)
                                    resp3 = requests.get(selected_link2)
                                    if resp3.status_code == 200:
                                        # Save HTML for debug
                                        save_html_to_file(resp3.text)
                                        var_url = get_var_url_from_html(resp3.text)
                                        if var_url:
                                            print(f"[INFO] Found var_url: {var_url}")
                                            button_links = fetch_download_buttons_from_var_url(var_url)
                                            for label, href in button_links.items():
                                                print(f"{label}: {href}")
                                            fetch_and_save_var_url(var_url, "debug_fetched.html")
                                        else:
                                            print("[INFO] No var_url found in the fetched page.")
                                    else:
                                        print(f"[ERROR] Failed to fetch {selected_link2}: Status code {resp3.status_code}")
                                else:
                                    print("[INFO] No selection made for <h4>/<p> buttons.")
                            else:
                                print("[INFO] No <h4> with immediate sibling <p> containing buttons found for terminal UI.")
                        else:
                            print(f"[ERROR] Failed to fetch link: Status code {link_resp.status_code}")
                    except Exception as e:
                        print(f"[ERROR] Exception while fetching link: {e}")
                else:
                    print("[INFO] No selection made.")
            else:
                print("[WARN] <hr> tag not found inside <article>.")
        else:
            print("[WARN] <article> tag not found on the page.")
    else:
        print(f"[ERROR] Failed to fetch page: Status code {response.status_code}")

if __name__ == "__main__":
    main()
