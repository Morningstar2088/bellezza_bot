import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from urllib.parse import urljoin

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

if not all([TG_BOT_TOKEN, TG_CHANNEL_ID, SCRAPER_API_KEY, AFFILIATE_TAG]):
    raise ValueError("❌ Una o più variabili ambiente mancanti. Controlla il file .env o la configurazione Railway.")

bot = Bot(token=TG_BOT_TOKEN)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

URL = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=" + \
      "https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031&dc&qid=1755976088&rnid=26901106031&ref=sr_nr_p_n_deal_type_0"

sent_products = set()

def parse_price(text):
    try:
        return float(text.replace("€", "").replace(",", ".").strip())
    except:
        return None

def get_discount_percent(original_price, discounted_price):
    try:
        return round((1 - discounted_price / original_price) * 100)
    except:
        return 0

def generate_message(title, discount_percent, original_price, price, sold_by, shipped_by, url):
    if discount_percent >= 60:
        tag = "🚨 ERRORE DI PREZZO?"
    elif discount_percent >= 40:
        tag = "🔥 AFFARE IMPERDIBILE!"
    else:
        tag = "✨ Offerta top!"

    style_prefixes = [
        f"{tag} 😱", f"{tag} 💥", f"{tag} 💖", f"{tag} 👀", f"{tag} 🤑"
    ]
    prefix = style_prefixes[hash(title) % len(style_prefixes)]

    return f"""{prefix}

🛍️ *{title.strip()}*

💸 Prezzo: ~{original_price}€~ → *{price}€*  
📉 Sconto: *-{discount_percent}%*  
📦 Venduto da: `{sold_by}`  
🚚 Spedito da: `{shipped_by}`

🔗 [Acquista ora]({url})
"""

def scrape_deals():
    print("🔁 Avvio scansione prodotti...")
    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Errore durante la richiesta HTTP: {e}")
        return

    print("✅ HTML ricevuto correttamente:")
    print(response.text[:1000])  # Mostra un'anteprima del contenuto per debug

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select("div.s-result-item")

    print(f"🔎 Trovati {len(items)} elementi da Amazon.")

    for item in items:
        try:
            title = item.select_one("h2 a span")
            if not title:
                continue
            title = title.text

            link = item.select_one("h2 a")["href"]
            full_url = urljoin("https://www.amazon.it", link)
            full_url += f"&tag={AFFILIATE_TAG}"

            price_whole = item.select_one("span.a-price span.a-offscreen")
            original_price_el = item.select_one("span.a-text-price span.a-offscreen")

            if not price_whole or not original_price_el:
                continue

            price = parse_price(price_whole.text)
            original_price = parse_price(original_price_el.text)

            if not price or not original_price:
                continue

            discount = get_discount_percent(original_price, price)
            if discount < 25:
                continue

            product_id = full_url.split("/dp/")[1].split("/")[0]
            if product_id in sent_products:
                continue
            sent_products.add(product_id)

            sold_by = item.select_one("div.a-row.a-size-base.a-color-secondary") or ""
            shipped_by = item.select_one("div.a-row.a-size-base.a-color-secondary.a-text-bold") or ""

            msg = generate_message(
                title=title,
                discount_percent=discount,
                original_price=original_price,
                price=price,
                sold_by=sold_by.text.strip() if sold_by else "N/D",
                shipped_by=shipped_by.text.strip() if shipped_by else "N/D",
                url=full_url
            )

            bot.send_message(chat_id=TG_CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
            print(f"✅ Prodotto inviato: {title[:50]}...")

        except Exception as e:
            print(f"⚠️ Errore durante parsing/invio: {e}")
            continue

if __name__ == "__main__":
    while True:
        scrape_deals()
        print("⏱️ Attendo 60 minuti prima della prossima scansione...\n")
        time.sleep(3600)
