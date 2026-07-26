"""
Zara Shirt Scraper (GUI version)
A simple desktop app with a "Run Scraper" button, progress log, and
buttons to open the output files once done.

Outputs (saved next to the .exe / script): zara_shirts.csv, zara_shirts.json,
zara_shirts_gallery.html
"""

import os
import sys
import json
import threading
import webbrowser
import requests
import pandas as pd
from urllib.parse import urlencode
from bs4 import BeautifulSoup

import tkinter as tk
from tkinter import scrolledtext, messagebox

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

URLS = [
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464',
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464&page=2',
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464&page=3',
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CSV_PATH = os.path.join(OUTPUT_DIR, 'zara_shirts.csv')
JSON_PATH = os.path.join(OUTPUT_DIR, 'zara_shirts.json')
HTML_PATH = os.path.join(OUTPUT_DIR, 'zara_shirts_gallery.html')


# ---------------------------------------------------------------------------
# SCRAPING LOGIC (same as the console version)
# ---------------------------------------------------------------------------

def get_scraperapi_url(api_key, url):
    payload = {'api_key': api_key, 'url': url, 'render': 'true'}
    return 'https://api.scraperapi.com/?' + urlencode(payload)


def scrape_page(api_key, url, log):
    proxy_url = get_scraperapi_url(api_key, url)
    log(f"Fetching: {url}")
    response = requests.get(proxy_url, timeout=90)
    log(f"  Status: {response.status_code}, Length: {len(response.text)}")

    soup = BeautifulSoup(response.text, 'html.parser')

    big_script = None
    for s in soup.find_all('script'):
        if s.string and 'window.zara.viewPayload' in s.string:
            big_script = s.string
            break

    if not big_script:
        log("  Couldn't find product data on this page — skipping.")
        return []

    start = big_script.find('window.zara.viewPayload = ') + len('window.zara.viewPayload = ')
    depth = 0
    end = None
    for i in range(start, len(big_script)):
        if big_script[i] == '{':
            depth += 1
        elif big_script[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    payload = json.loads(big_script[start:end])
    product_groups = payload.get('productGroups', [])

    results = []
    for group in product_groups:
        for element in group.get('elements', []):
            for component in element.get('commercialComponents', []):
                name = component.get('name')
                price_raw = component.get('price')
                price = f"{price_raw / 100:.2f} EUR" if price_raw else None

                image_url = None
                colors = component.get('detail', {}).get('colors', [])
                if colors:
                    xmedia = colors[0].get('xmedia', [])
                    if xmedia:
                        large_imgs = [m for m in xmedia if 'large' in m.get('allowedScreens', [])]
                        chosen = large_imgs[0] if large_imgs else xmedia[0]
                        image_url = chosen.get('extraInfo', {}).get('deliveryUrl')

                results.append({
                    'product_name': name,
                    'price': price,
                    'image_url': image_url,
                })

    return results


def save_outputs(products, log):
    df = pd.DataFrame(products)
    df.to_csv(CSV_PATH, index=False)
    log(f"Saved {len(df)} rows to {CSV_PATH}")

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    log(f"Saved to {JSON_PATH}")

    html_content = "<html><body style='font-family:sans-serif;'>"
    for p in products:
        html_content += "<div style='margin-bottom:30px;'>"
        html_content += f"<h3>{p['product_name']}</h3>"
        html_content += f"<p>{p['price']}</p>"
        if p.get('image_url'):
            html_content += f"<img src='{p['image_url']}' width='200'>"
        html_content += "</div><hr>"
    html_content += "</body></html>"
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    log(f"Saved to {HTML_PATH}")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class ScraperApp:
    def __init__(self, root):
        self.root = root
        root.title("Zara Shirt Scraper")
        root.geometry("560x420")
        root.resizable(False, False)

        tk.Label(root, text="ScraperAPI Key:").pack(pady=(12, 0))
        self.api_key_entry = tk.Entry(root, width=50, show="*")
        self.api_key_entry.pack(pady=(0, 10))

        # Prefill from environment variable if present
        env_key = os.environ.get('SCRAPERAPI_KEY')
        if env_key:
            self.api_key_entry.insert(0, env_key)

        self.run_button = tk.Button(root, text="Run Scraper", command=self.start_scrape,
                                     bg="#222", fg="white", padx=10, pady=6)
        self.run_button.pack(pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(root, width=68, height=15, state='disabled')
        self.log_box.pack(padx=10, pady=(0, 10))

        button_frame = tk.Frame(root)
        button_frame.pack()

        self.open_html_button = tk.Button(button_frame, text="Open Gallery", command=self.open_gallery, state='disabled')
        self.open_html_button.grid(row=0, column=0, padx=5)

        self.open_folder_button = tk.Button(button_frame, text="Open Output Folder", command=self.open_folder, state='disabled')
        self.open_folder_button.grid(row=0, column=1, padx=5)

    def log(self, message):
        self.log_box.configure(state='normal')
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state='disabled')

    def start_scrape(self):
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Missing API Key", "Please enter your ScraperAPI key.")
            return

        self.run_button.config(state='disabled', text="Running...")
        self.open_html_button.config(state='disabled')
        self.open_folder_button.config(state='disabled')

        # Run scraping in a background thread so the GUI doesn't freeze
        thread = threading.Thread(target=self.run_scrape, args=(api_key,), daemon=True)
        thread.start()

    def run_scrape(self, api_key):
        try:
            all_products = []
            for url in URLS:
                all_products.extend(scrape_page(api_key, url, self.log))

            self.log(f"\nTotal products scraped: {len(all_products)}\n")

            if not all_products:
                self.log("No products found — nothing to save.")
            else:
                save_outputs(all_products, self.log)
                self.log("\nDone!")
                self.open_html_button.config(state='normal')
                self.open_folder_button.config(state='normal')

        except Exception as e:
            self.log(f"\nError: {e}")
            messagebox.showerror("Scraping failed", str(e))

        finally:
            self.run_button.config(state='normal', text="Run Scraper")

    def open_gallery(self):
        if os.path.exists(HTML_PATH):
            webbrowser.open(f"file://{HTML_PATH}")

    def open_folder(self):
        if sys.platform == 'win32':
            os.startfile(OUTPUT_DIR)
        elif sys.platform == 'darwin':
            os.system(f'open "{OUTPUT_DIR}"')
        else:
            os.system(f'xdg-open "{OUTPUT_DIR}"')


if __name__ == '__main__':
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()
