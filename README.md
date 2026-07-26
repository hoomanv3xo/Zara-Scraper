# Zara-Scraper

A Python notebook that scrapes men's shirt listings from Zara (name, price, and product image) and exports the results to CSV, JSON, and an HTML gallery.

## How it works

Zara's product grid is rendered with JavaScript, and the page is protected against basic bot scraping. Rather than fighting the DOM directly, this script:

1. Sends each category URL through **ScraperAPI** with `render=true`, which loads the page in a real headless browser (executing JavaScript) and returns the fully rendered HTML.
2. Instead of relying on fragile CSS selectors (which Zara changes periodically), it locates the embedded `window.zara.viewPayload` JSON blob in a `<script>` tag on the page. This is the same data Zara's frontend uses to hydrate the page, and it contains clean, structured info for every product — name, price, and full-resolution image URLs — regardless of whether that product has scrolled into view yet.
3. Parses that JSON to build a list of products, then exports the results.

This approach is more resilient than scraping rendered HTML: even if Zara changes class names or page layout, the underlying JSON structure tends to stay stable for much longer.

## Requirements

* Python 3
* A [ScraperAPI](https://www.scraperapi.com/) account and API key
* Packages: `requests`, `beautifulsoup4`, `pandas` (for CSV export)

Install packages if needed:

```bash
pip install requests beautifulsoup4 pandas
```

## Setup

1. Open `scraper.ipynb` in Jupyter.
2. Replace the `API\_KEY` value with your own ScraperAPI key.

   * **Don't commit your real key to GitHub or share the notebook publicly with it included.** Consider loading it from an environment variable instead:

```python
     import os
     API\_KEY = os.environ.get('SCRAPERAPI\_KEY')
     ```

3. Update the `urls` list with whichever Zara category page(s) you want to scrape. Add `\&page=2`, `\&page=3`, etc. to the query string for additional pages.

## Usage

Run the notebook cells in order. The `scrape\_page(url)` function:

* Fetches the rendered page through ScraperAPI
* Extracts the `viewPayload` JSON
* Returns a list of dicts: `{'product\_name': ..., 'price': ..., 'image\_url': ...}`

Run it across all your URLs and combine into `all\_products`:

```python
all\_products = \[]
for url in urls:
    all\_products.extend(scrape\_page(url))
```

### Exporting results

**CSV**

```python
import pandas as pd
df = pd.DataFrame(all\_products)
df.to\_csv('zara\_shirts\_with\_images.csv', index=False)
```

**JSON**

```python
import json
with open('zara\_shirts\_with\_images.json', 'w', encoding='utf-8') as f:
    json.dump(all\_products, f, indent=2, ensure\_ascii=False)
```

**HTML gallery (view products with images in a browser)**

```python
html\_content = "<html><body style='font-family:sans-serif;'>"
for p in all\_products:
    html\_content += f"<div style='margin-bottom:30px;'>"
    html\_content += f"<h3>{p\['product\_name']}</h3>"
    html\_content += f"<p>{p\['price']}</p>"
    if p\['image\_url']:
        html\_content += f"<img src='{p\['image\_url']}' width='200'>"
    html\_content += "</div><hr>"
html\_content += "</body></html>"

with open('zara\_shirts\_gallery.html', 'w', encoding='utf-8') as f:
    f.write(html\_content)
```

## Notes \& gotchas

* **`render=true` costs more ScraperAPI credits** per request than a plain fetch. Check remaining credits anytime with:

```python
  import requests
  r = requests.get(f"https://api.scraperapi.com/account?api\_key={API\_KEY}")
  print(r.json())
  ```

* **Duplicate-looking entries are expected.** The same shirt often appears multiple times in different colorways, each as a separate entry.
* **Product counts may vary slightly page to page.** Zara's grid layout occasionally groups or displays items in ways that don't map 1:1 to a fixed "products per page" count — this is normal.
* **If scraping breaks in the future**, the most likely cause is Zara restructuring their page. Start by checking whether `window.zara.viewPayload` still exists in the page's `<script>` tags, and re-inspect the JSON shape (`productGroups` → `elements` → `commercialComponents` → `detail.colors\[0].xmedia`) since Zara could change this structure too, just less often than CSS classes.
* **Running in Jupyter, not Scrapy.** This project intentionally avoids the `scrapy` framework since it doesn't play well with Jupyter's event loop (can cause `ReactorNotRestartable` errors or kernel crashes). Plain `requests` + `BeautifulSoup` is simpler and more reliable here.

## Security reminder

Your ScraperAPI key is a secret. Avoid:

* Committing it to a public GitHub repo
* Sharing the notebook with the key still filled in
* Posting output/screenshots that include it

