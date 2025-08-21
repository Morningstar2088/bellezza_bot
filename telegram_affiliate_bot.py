import os
import time
import json
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEYS = os.getenv("SCRAPER_API_KEYS", "")
if not SCRAPER_API_KEYS:
    raise ValueError("❌ Environment variable 'SCRAPER_API_KEYS' not found. Check Railway configuration.")
SCRAPER_API_KEYS = SCRAPER_API_KEYS.split(",")

KEYWORDS = [
    "crema viso", "siero viso", "contorno occhi", "maschera viso", "crema antirughe",
    "detergente viso", "tonico viso", "crema corpo", "olio viso", "fondotinta",
    "correttore", "cipria", "rossetto", "mascara", "matita occhi",
    "ombretto", "eyeliner", "trucco viso", "spazzolino elettrico", "epilatore",
    "rasoio donna", "schiuma da barba", "ceretta", "olio essenziale", "crema mani",
    "balsamo labbra", "burrocacao", "crema solare", "integratori pelle", "magnesio",
    "acido ialuronico"
]

# Carica i link già postati
if os.path.exists("posted.json"):
    with open("posted.json", "r") as f:
        posted_links = set(json.load(f))
else:
    posted_links = set()

def save_posted_links():
    with open("posted.json", "w") as f:
        json.dump(list(posted_links), f)

bot = Bot(token=TG_BOT_TOKEN)

def get_soup(url):
    for api_key in SCRAPER_API_KEYS:
        try:
            response = requests.get(
                "http://api.scraperapi.com/",
                params={"api_key": api_key, "url": url, "country_code": "it"},
                timeout=15,
            )
            if response.status_code == 200:
                return BeautifulSoup(response.content, "html.parser")
        except Exception:
            continue
    return None

def extract_products(soup):
    prodotti = []
    items = soup.select('[data-component-type="s-search-result"]')
    for item in items:
        try:
            title_elem = item.h2.a
            title = title_elem.text.strip()
            url = "https://www.amazon.it" + title_elem["href"].split("?")[0]
            image_elem = item.select_one("img")
            image = image_elem["src"] if image_elem else None
            price_whole = item.select_one(".a-price-whole")
            price_frac = item.select_one(".a-price-fraction")
            if not (price_whole and price_frac):
                continue
            current_price = float(price_whole.text.replace(".", "").replace(",", ".")) + float("0." + price_frac.text)
            old_price_elem = item.select_one(".a-text-price .a-offscreen")
            old_price = None
            if old_price_elem:
                old_price = float(old_price_elem.text.replace("€", "").replace(".", "").replace(",", ".").strip())
            prodotti.append({
                "title": title,
                "url": url,
                "image": image,
                "current_price": current_price,
                "old_price": old_price,
            })
        except Exception:
            continue
    return prodotti

def generate_message(product):
    price = f"{product['current_price']:.2f}€"
    discount = ""
    if product["old_price"]:
        discount_val = int(100 - (product["current_price"] / product["old_price"] * 100))
        if discount_val >= 50:
            discount = "🔥 *SUPER OFFERTA!*"
        else:
            discount = f"💸 *Sconto*: {discount_val}%"
    msg = f"🛍️ *{product['title']}*\n💰 *Prezzo:* {price}\n{discount}\n👉 [Clicca qui per vedere su Amazon]({product['url']})"
    return msg

def post_product(product):
    link = product["url"].split("?")[0]
    if link in posted_links:
        return
    msg = generate_message(product)
    bot.send_message(chat_id=TG_CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    posted_links.add(link)
    save_posted_links()
    print(f"✅ Postato: {product['title']}")

# === MAIN LOOP ===
if __name__ == "__main__":
    while True:
        for kw in KEYWORDS:
            print(f"🔎 Cerco: {kw}")
            url = f"https://www.amazon.it/s?k={kw.replace(' ', '+')}"
            soup = get_soup(url)
            if not soup:
                continue
            prodotti = extract_products(soup)
            for p in prodotti[:5]:  # max 5 per keyword
                if p["old_price"] and p["old_price"] > p["current_price"]:
                    post_product(p)
                time.sleep(1)
            time.sleep(2)

        print("🕒 Attesa 60 minuti per nuova scansione...\n")
        time.sleep(60 * 60)
