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

KEYWORDS = [
    "crema viso", "siero viso", "contorno occhi", "maschera viso", "crema antirughe",
    "detergente viso", "tonico viso", "crema corpo", "olio viso", "fondotinta",
    "correttore", "cipria", "rossetto", "mascara", "matita occhi", "ombretto",
    "eyeliner", "trucco viso", "spazzolino elettrico", "epilatore", "rasoio donna",
    "schiuma da barba", "ceretta", "olio essenziale", "crema mani", "balsamo labbra",
    "burrocacao", "crema solare", "integratori pelle", "magnesio", "acido ialuronico",
    "scrub viso", "kit skincare", "tonico illuminante", "patch occhi", "primer viso",
    "lucidalabbra", "pennelli trucco", "beauty blender", "rullo giada", "face roller",
    "vitamina c viso", "detergente schiumogeno", "cura della pelle", "cura capelli",
    "cosmetici naturali", "make up kit", "skincare coreana", "pelle sensibile"
]

# Load already posted links
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
            timeout=15,
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

            venduto_da = item.select_one(".a-row.a-size-base.a-color-secondary")
            venduto_testo = venduto_da.text.strip() if venduto_da else "Venditore non specificato"

            prodotti.append({
                "title": title,
                "url": url,
                "image": image,
                "current_price": current_price,
                "old_price": old_price,
                "venduto_da": venduto_testo
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
                "💣 *Occhio: prezzo sbagliato?*"
            ]
            discount = f"{phrases[hash(product['title']) % len(phrases)]} (-{discount_val}%)"
        else:
            discount = f"💸 *Sconto*: -{discount_val}%"

    msg = (
        f"💖 *{product['title']}*\n"
        f"💰 *Prezzo ora:* {price}\n"
        f"{discount}\n"
        f"{shipping_info}\n"
        f"👉 [Scopri l’offerta su Amazon]({product['url']})\n"
        f"_Offerta segnalata da BeautyBot — la tua BFF delle occasioni 💅_"
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
        for kw in KEYWORDS:
            print(f"🔎 Cerco: {kw}")
            url = f"https://www.amazon.it/s?k={kw.replace(' ', '+')}"
            soup = get_soup(url)
            if not soup:
                continue
            prodotti = extract_products(soup)
            for p in prodotti[:8]:  # Max 8 prodotti per keyword
                if p["old_price"] and p["old_price"] > p["current_price"]:
                    post_product(p)
                time.sleep(1)
            time.sleep(2)

        print("🕒 Attesa 60 minuti per nuova scansione...\n")
        time.sleep(60 * 60)
