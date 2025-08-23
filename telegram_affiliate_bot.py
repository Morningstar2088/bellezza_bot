import os
import time
import json
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
if not SCRAPER_API_KEY:
    raise ValueError("❌ Nessuna chiave SCRAPER_API_KEY trovata. Verifica su Railway o nel .env.")

# URL offerte del giorno categoria bellezza
CATEGORY_URL = "https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031&dc"

# Load prodotti già postati
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
    try:
        response = requests.get(
            "http://api.scraperapi.com/",
            params={"api_key": SCRAPER_API_KEY, "url": url, "country_code": "it"},
            timeout=20,
        )
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
    except Exception:
        pass
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

            venduto_da = item.select_one(".a-row.a-size-base.a-color-secondary span")
            venduto_text = venduto_da.text.strip() if venduto_da else "Venditore non specificato"

            prodotti.append({
                "title": title,
                "url": url,
                "image": image,
                "current_price": current_price,
                "old_price": old_price,
                "venduto_da": venduto_text
            })
        except Exception:
            continue
    return prodotti

def generate_message(product):
    price = f"{product['current_price']:.2f}€"
    discount = ""
    shipping_info = f"📦 *{product['venduto_da']}*"

    if product["old_price"]:
        discount_val = int(100 - (product["current_price"] / product["old_price"] * 100))
        if discount_val < 25:
            return None
        elif discount_val >= 60:
            phrases = [
                "🚨 *Errore di Prezzo?* Non ci credo 😱",
                "🧨 *Prezzo Fuori di Testa!*",
                "🎯 *Super sconto fuori norma!*",
                "💣 *Occhio: prezzo sbagliato?*",
                "🔥 *Imperdibile!*",
                "😵 *Prezzo pazzo!*"
            ]
            discount = f"{phrases[hash(product['title']) % len(phrases)]} (-{discount_val}%)"
        else:
            discount = f"💸 *Sconto:* -{discount_val}%"

    msg = (
        f"💖 *{product['title']}*\n"
        f"💰 *Prezzo ora:* {price}\n"
        f"{discount}\n"
        f"{shipping_info}\n"
        f"👉 [Scopri l’offerta su Amazon]({product['url']})\n"
        f"_BeautyBot scova per te solo i migliori affari ✨_"
    )
    return msg

def post_product(product):
    link = product["url"].split("?")[0]
    if link in posted_links:
        return
    msg = generate_message(product)
    if not msg:
        return
    bot.send_message(chat_id=TG_CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    posted_links.add(link)
    save_posted_links()
    print(f"✅ Postato: {product['title']}")

# === MAIN LOOP ===
if __name__ == "__main__":
    while True:
        print("🔍 Scansione Amazon — categoria Bellezza (Offerte del giorno)...")
        soup = get_soup(CATEGORY_URL)
        if not soup:
            print("❌ Nessun risultato")
            time.sleep(60 * 5)
            continue

        prodotti = extract_products(soup)
        count = 0
        for p in prodotti:
            if p["old_price"] and p["old_price"] > p["current_price"]:
                post_product(p)
                count += 1
                if count >= 10:
                    break
            time.sleep(1)

        print("🕒 Attesa 60 minuti per nuova scansione...\n")
        time.sleep(60 * 60)
