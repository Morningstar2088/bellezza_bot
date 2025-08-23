import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

if not TG_BOT_TOKEN or not TG_CHANNEL_ID or not SCRAPER_API_KEY or not AFFILIATE_TAG:
    raise ValueError("❌ Manca una o più variabili d'ambiente. Verifica su Railway.")

bot = Bot(token=TG_BOT_TOKEN)

AMAZON_URL = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031&dc"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def parse_discount(text):
    try:
        return int(text.replace('%', '').replace('-', '').strip())
    except:
        return 0

def find_amazon_deals():
    print(f"🔎 Scansione Amazon – categoria Bellezza (Offerte del giorno)...")

    try:
        response = requests.get(AMAZON_URL, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")
        items = soup.select("div.s-result-item")

        for item in items:
            title = item.select_one("h2 span")
            link_tag = item.select_one("a.a-link-normal")
            price_whole = item.select_one("span.a-price-whole")
            price_frac = item.select_one("span.a-price-fraction")
            discount_tag = item.select_one("span.a-letter-space + span")

            if title and price_whole and discount_tag:
                title_text = title.get_text(strip=True)
                product_url = "https://www.amazon.it" + link_tag["href"].split("?")[0]
                price = price_whole.get_text(strip=True) + "," + (price_frac.get_text(strip=True) if price_frac else "00")
                discount = parse_discount(discount_tag.get_text())
                seller = "Venditore non specificato"
                shipper = "Spedizione non specificata"

                # Estrai da venduto e spedito
                seller_info = item.select_one("div.a-row.a-size-base.a-color-secondary")
                if seller_info:
                    parts = seller_info.get_text(separator="|").split("|")
                    if len(parts) >= 1:
                        seller = parts[0].strip()
                    if len(parts) >= 2:
                        shipper = parts[1].strip()

                # Filtro sullo sconto
                if discount >= 25:
                    if discount >= 60:
                        price_tag = "🚨 *ERRORE DI PREZZO?*"
                    else:
                        price_tag = "💸 *Offerta interessante!*"

                    message = (
                        f"{price_tag}\n\n"
                        f"*{title_text}*\n"
                        f"💰 Prezzo: *{price} €*  \n"
                        f"📉 Sconto: *-{discount}%*  \n"
                        f"🏷️ Venduto da: _{seller}_\n"
                        f"📦 Spedito da: _{shipper}_\n"
                        f"🔗 [Vai all’offerta]({product_url}?tag={AFFILIATE_TAG})"
                    )

                    bot.send_message(chat_id=TG_CHANNEL_ID, text=message, parse_mode="Markdown", disable_web_page_preview=False)
                    print(f"[✓] Inviato: {title_text[:50]}...")

        print("⏱️ Attesa 60 minuti per nuova scansione...")
    except Exception as e:
        print(f"❌ Errore durante la scansione: {e}")

# Loop infinito
while True:
    find_amazon_deals()
    time.sleep(3600)
