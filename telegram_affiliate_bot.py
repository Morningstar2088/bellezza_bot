import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
import asyncio
import re
import time
import pickle
from datetime import datetime

# Env
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# File per tenere traccia degli ASIN inviati
SENT_FILE = "sent_products.pkl"

def load_sent_products():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "rb") as f:
            return pickle.load(f)
    return set()

def save_sent_products(data):
    with open(SENT_FILE, "wb") as f:
        pickle.dump(data, f)

sent_products = load_sent_products()

# Costanti
HEADERS = {"User-Agent": "Mozilla/5.0"}
URL = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031"

# Badge dinamici
def get_discount_badge(percent):
    if percent >= 60:
        return "⚠️ Errore di prezzo"
    elif percent >= 50:
        return "🔥 Super offerta"
    elif percent >= 40:
        return "💥 Affare imperdibile"
    elif percent >= 30:
        return "📉 Sconto interessante"
    else:
        return f"-{percent}%"

async def send_to_telegram(bot, product):
    try:
        message = f"🛍️ <b>{product['title']}</b>\n\n"
        message += f"💸 <b>Prezzo:</b> <s>{product['old_price']}</s> → <b>{product['price']}</b>\n"
        message += f"🔥 <b>Sconto:</b> {product['discount']}\n"
        if product['sold_by'] != "Non disponibile":
            message += f"🏪 <b>Venduto da:</b> {product['sold_by']}\n"
        if product['shipped_by'] != "Non disponibile":
            message += f"🚚 <b>Spedito da:</b> {product['shipped_by']}\n"
        message += f"🔗 <a href='{product['link']}'>Acquista ora su Amazon</a>\n\n"
        message += "#bellezza #offerte #amazon"

        await bot.send_photo(
            chat_id=TG_CHANNEL_ID,
            photo=product['image'],
            caption=message,
            parse_mode=ParseMode.HTML
        )
        print(f"✅ Inviato: {product['asin']}")
    except Exception as e:
        print(f"❌ Errore invio prodotto {product['asin']}: {e}")

def extract_products_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    products = soup.select('div[data-asin]')
    print(f"🔎 Trovati {len(products)} elementi da Amazon.")
    found = []

    for product in products:
        asin = product.get('data-asin')
        if not asin or asin in sent_products:
            continue

        title_tag = product.select_one('h2 span')
        price_tag = product.select_one('.a-price span.a-offscreen')
        old_price_tag = product.select_one('.a-price.a-text-price span.a-offscreen')
        image_tag = product.select_one('img')

        if not title_tag or not price_tag or not old_price_tag:
            continue

        price = price_tag.text.strip()
        old_price = old_price_tag.text.strip()

        try:
            p1 = float(re.sub(r"[^\d,]", "", old_price).replace(",", "."))
            p2 = float(re.sub(r"[^\d,]", "", price).replace(",", "."))
            sconto = round(100 - (p2 / p1 * 100))
            if sconto < 25:
                continue
        except:
            continue

        sold_by = "Non disponibile"
        shipped_by = "Non disponibile"
        merchant_info = product.select_one('.a-row.a-size-base.a-color-secondary')
        if merchant_info:
            merchant_text = merchant_info.get_text(strip=True)
            if "Venduto da" in merchant_text:
                match = re.search(r"Venduto da ([^\.]+)", merchant_text)
                if match:
                    sold_by = match.group(1).strip()
            if "Spedito da" in merchant_text:
                match = re.search(r"Spedito da ([^\.]+)", merchant_text)
                if match:
                    shipped_by = match.group(1).strip()

        found.append({
            "asin": asin,
            "title": title_tag.text.strip(),
            "price": price,
            "old_price": old_price,
            "discount": get_discount_badge(sconto),
            "image": image_tag["src"] if image_tag else "",
            # ✅ Forzatura lingua italiana su Amazon
            "link": f"https://www.amazon.it/dp/{asin}/?tag={AFFILIATE_TAG}&language=it_IT",
            "sold_by": sold_by,
            "shipped_by": shipped_by
        })

    print(f"📦 Trovati {len(found)} prodotti con sconto.")
    return found

async def main():
    print("🔁 Avvio scansione prodotti...\n")

    # BLOCCHI ORARI: PUBBLICA SOLO TRA LE 08:00 e 22:00 (commentato temporaneamente)
    # current_hour = datetime.now().hour
    # if not (8 <= current_hour < 22):
    #     print("⏸️ Fuori orario (08:00–22:00). Nessuna pubblicazione.\n")
    #     return

    bot = Bot(token=TG_BOT_TOKEN)

    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            print("✅ HTML ricevuto correttamente:\n")
            products = extract_products_from_html(response.text)
            for product in products:
                if product['asin'] not in sent_products:
                    await send_to_telegram(bot, product)
                    sent_products.add(product['asin'])
                    save_sent_products(sent_products)
                    await asyncio.sleep(2)
        else:
            print(f"❌ Errore richiesta: {response.status_code}")
    except Exception as e:
        print(f"❌ Errore generale: {e}")

    print("\n⏱️ Attendo 60 minuti prima della prossima scansione...")

if __name__ == "__main__":
    while True:
        asyncio.run(main())
        time.sleep(3600)
