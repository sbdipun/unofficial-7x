import asyncio
import re
import html
import lxml
from xml.sax.saxutils import escape
import httpx
from bs4 import BeautifulSoup
from flask import Flask, jsonify, Response

app = Flask(__name__)

# ✅ Updated URL and Headers
BASE_URL = "https://old-gods.hash4s439.workers.dev/1741178802882/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'QBcphs7Xe/KJWn1RnYQNlQ=='}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def clean_magnet_link(magnet):
    """Remove specific tracker domain from the magnet link."""
    magnet = re.sub(r'(?<=dn=)\[1337x\.HashHackers\.Com\]', '', magnet)
    magnet = re.sub(r'&+', '&', magnet)
    if magnet.endswith('&'):
        magnet = magnet[:-1]
    return magnet

async def fetch_html(url):
    """ Fetch HTML content with error handling and timeout """
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url, cookies=COOKIES, headers=HEADERS)
            if response.status_code != 200:
                print(f"❌ Failed to fetch {url} - Status Code: {response.status_code}")
                return None
            return response.text
        except httpx.TimeoutException:
            print(f"⏳ Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"🔥 Error fetching {url}: {e}")
            return None

async def fetch_title_links():
    """ Scrape the first 13 movie title links from the page """
    html = await fetch_html(BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        print("⚠️ <tbody> not found in the HTML")
        return []

    links = []
    for a in tbody.find_all('a', class_='icon'):
        title_link = a.find_next_sibling('a')
        if title_link and title_link['href'].startswith('//'):
            links.append('https:' + title_link['href'])

    return links[:13]  # ✅ Scrape only first 13 movies

async def fetch_page_details(link):
    """ Extract movie title, magnet link, and file size from a movie page """
    html = await fetch_html(link)
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.replace("Download", "").replace("Torrent", "").strip() if soup.title else "No title"

    magnet = None
    for script in soup.find_all('script'):
        if script.string:
            match = re.search(r'var mainMagnetURL\s*=\s*"(magnet:[^"]+)"', script.string)
            if match:
                magnet = match.group(1)
                break

    # ✅ Clean the magnet link by removing the specific tracker domain
    if magnet:
        magnet = clean_magnet_link(magnet)

    # Extract file size
    file_size = None
    lists = soup.find_all("ul", class_="list")
    for ul in lists:
        for li in ul.find_all("li"):
            strong_tag = li.find("strong")
            span_tag = li.find("span")
            if strong_tag and span_tag and strong_tag.text.strip() == "Total size":
                file_size = span_tag.text.strip()
                break

    return title, magnet, file_size

@app.route('/')
def home():
    return "✅ 1337x Scraper Is Running"

@app.route('/rss', methods=['GET'])
def rss():
    """ Fetch first 13 movie titles, magnet links, and file sizes as RSS feed """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    title_links = loop.run_until_complete(fetch_title_links())
    if not title_links:
        return jsonify({"error": "No links found"}), 500

    # ✅ Run multiple tasks asynchronously
    tasks = [fetch_page_details(link) for link in title_links]
    results = loop.run_until_complete(asyncio.gather(*tasks))

    # Generate RSS items
    rss_items = ""
    for title, magnet, file_size in results:
        if title and magnet:
            description = f"Size: {file_size if file_size else '.'}"
            rss_items += f"""
            <item>
                <title>{title}</title>
                <link>{magnet}</link>
                <description>{description}</description>
            </item>
            """

    # Generate the full RSS feed
    base_url = f"https://www.1377x.to/cat/Movies/1/"
    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>1337x RSS Feed</title>
            <link>{base_url}</link>
            <description>Latest Movies and TV Shows</description>
            {rss_items}
        </channel>
    </rss>
    """

    return Response(rss_feed, content_type='application/rss+xml')

if __name__ == "__main__":
    app.run(debug=True)
