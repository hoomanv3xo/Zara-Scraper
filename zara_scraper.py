"""
Zara Shirt Scraper
Scrapes product name, price, and image URL from Zara category pages
using ScraperAPI (with JS rendering) and the site's embedded JSON payload.

Outputs: zara_shirts.csv, zara_shirts.json, zara_shirts_gallery.html
"""

import os
import sys
import json
import requests
import pandas as pd
from urllib.parse import urlencode
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Prefer an environment variable; fall back to a prompt if not set.
API_KEY = os.environ.get('SCRAPERAPI_KEY')
if not API_KEY:
    API_KEY = input("Enter your ScraperAPI key: ").strip()

URLS = [
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464',
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464&page=2',
    'https://www.zara.com/ww/en/man-shirts-l737.html?v1=2351464&page=3',
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))


# ---------------------------------------------------------------------------
# SCRAPING LOGIC
# ---------------------------------------------------------------------------

def get_scraperapi_url(url):
    payload = {'api_key': API_KEY, 'url': url, 'render': 'true'}
    return 'https://api.scraperapi.com/?' + urlencode(payload)


def scrape_page(url):
    proxy_url = get_scraperapi_url(url)
    print(f"Fetching: {url}")
    response = requests.get(proxy_url, timeout=90)
    print(f"  Status: {response.status_code}, Length: {len(response.text)}")

    soup = BeautifulSoup(response.text, 'html.parser')

    big_script = None
    for s in soup.find_all('script'):
        if s.string and 'window.zara.viewPayload' in s.string:
            big_script = s.string
            break

    if not big_script:
        print("  Couldn't find viewPayload script on this page — skipping.")
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


# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------

def save_csv(products, path):
    df = pd.DataFrame(products)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows to {path}")


def save_json(products, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"Saved to {path}")


def save_html_gallery(products, path):
    html_content = "<html><body style='font-family:sans-serif;'>"
    for p in products:
        html_content += "<div style='margin-bottom:30px;'>"
        html_content += f"<h3>{p['product_name']}</h3>"
        html_content += f"<p>{p['price']}</p>"
        if p.get('image_url'):
            html_content += f"<img src='{p['image_url']}' width='200'>"
        html_content += "</div><hr>"
    html_content += "</body></html>"

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Saved to {path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    all_products = []
    for url in URLS:
        all_products.extend(scrape_page(url))

    print(f"\nTotal products scraped: {len(all_products)}\n")

    if not all_products:
        print("No products found — nothing to save.")
        return

    save_csv(all_products, os.path.join(OUTPUT_DIR, 'zara_shirts.csv'))
    save_json(all_products, os.path.join(OUTPUT_DIR, 'zara_shirts.json'))
    save_html_gallery(all_products, os.path.join(OUTPUT_DIR, 'zara_shirts_gallery.html'))

    print("\nDone. Files saved next to this script/executable.")


if __name__ == '__main__':
    main()
    input("\nPress Enter to exit...")
