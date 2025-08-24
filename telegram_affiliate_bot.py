import os
import json
import re
import time
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode

# === ENV ===
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# === COSTANTI ===
HEADERS = {"User-Agent": "Mozilla/5.0"}
URL = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031&language=it_IT"
SENT_FILE = "sent_products.json"

# === CARICA ASIN GIÀ INVIATI ===
if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r") as f:
        sent_products = set(json.load(f))
else:
    sent_products = set()

# === INVIA A TELEGRAM ===
async def send_to_telegram(bot, product):
    try:
        msg = f"✨ <b>{product['title']}</b>\n\n"
        msg += f"💸 <b>Prezzo:</b> <s>{product['old_price']}</s> → <b>{product['price']}</b>\n"
        msg += f"🔥 <b>Sconto:</b> {product['discount']}\n"
        if product["coupon"]:
            msg += f"🎁 <b>Coupon:</b> {product['coupon']}\n"
        if product["sold_by"] != "Non disponibile":
            msg += f"🏪 <b>Venduto da:</b> {product['sold_by']}\n"
        if product["shipped_by"] != "Non disponibile":
            msg += f"🚚 <b>Spedito da:</b> {product['shipped_by']}\n"
        msg += f"👉 <a href='{product['link']}'>Scopri l’offerta su Amazon</a>\n\n"
        msg += "#offerte #amazon #bellezza"

        await bot.send_photo(
            chat_id=TG_CHANNEL_ID,
            photo=product["image"],
            caption=msg,
            parse_mode=ParseMode.HTML
        )
        print(f"✅ Inviato: {product['asin']}")
    except Exception as e:
        print(f"❌ Errore invio prodotto {product['asin']}: {e}")

# === ESTRAI PRODOTTI ===
def extract_products_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('div[data-asin]')
    print(f"🔎 Trovati {len(items)} elementi da Amazon.")
    found = []

    for item in items:
        asin = item.get("data-asin")
        if not asin or asin in sent_products:
            continue

        title_tag = item.select_one("h2 span")
        price_tag = item.select_one(".a-price span.a-offscreen")
        old_price_tag = item.select_one(".a-price.a-text-price span.a-offscreen")
        image_tag = item.select_one("img")

        if not title_tag or not price_tag or not old_price_tag:
            continue

        # Salta prezzi in €/kg o €/ml
        if any(unit in price_tag.text.lower() for unit in ["€/l", "€/ml", "€/kg", "€ / l", "€ / kg"]):
            continue

        try:
            p_old = float(re.sub(r"[^\d,]", "", old_price_tag.text).replace(",", "."))
            p_new = float(re.sub(r"[^\d,]", "", price_tag.text).replace(",", "."))
            discount = round(100 - (p_new / p_old * 100))
            if discount < 25:
                continue
        except:
            continue

        # Coupon
        coupon = ""
        coupon_tag = item.select_one(".s-coupon-unclipped .a-color-base")
        if coupon_tag:
            coupon_text = coupon_tag.get_text(strip=True)
            if "%" in coupon_text or "€" in coupon_text:
                coupon = coupon_text

        # Venduto / Spedito
        sold_by = "Non disponibile"
        shipped_by = "Non disponibile"
        merchant_info = item.select_one('.a-row.a-size-base.a-color-secondary')
        if merchant_info:
            text = merchant_info.get_text(strip=True)
            match_v = re.search(r"Venduto da ([^\.]+)", text)
            match_s = re.search(r"Spedito da ([^\.]+)", text)
            if match_v:
                sold_by = match_v.group(1).strip()
            if match_s:
                shipped_by = match_s.group(1).strip()

        found.append({
            "asin": asin,
            "title": title_tag.text.strip(),
            "price": price_tag.text.strip(),
            "old_price": old_price_tag.text.strip(),
            "discount": f"-{discount}%" if discount <= 60 else f"⚠️ -{discount}%",
            "coupon": coupon,
            "image": image_tag["src"] if image_tag else "",
            "link": f"https://www.amazon.it/dp/{asin}/?tag={AFFILIATE_TAG}&language=it_IT",
            "sold_by": sold_by,
            "shipped_by": shipped_by
        })

    print(f"📦 Trovati {len(found)} prodotti con sconto.")
    return found

# === MAIN ===
async def main():
    # ORARIO ATTIVO (commentato per ora)
    # hour = datetime.now().hour
    # if hour < 8 or hour > 22:
    #     print("⏰ Fuori orario 08–22. Non invio.")
    #     return

    print("🔁 Avvio scansione prodotti...\n")
    bot = Bot(token=TG_BOT_TOKEN)

    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            print("✅ HTML ricevuto correttamente:\n")
            products = extract_products_from_html(response.text)
            for product in products:
                if product["asin"] not in sent_products:
                    await send_to_telegram(bot, product)
                    sent_products.add(product["asin"])
                    with open(SENT_FILE, "w") as f:
                        json.dump(list(sent_products), f)
                    await asyncio.sleep(2)
        else:
            print(f"❌ Errore richiesta: {response.status_code}")
    except Exception as e:
        print(f"❌ Errore generale: {e}")

    print("\n⏱️ Attendo 60 minuti prima della prossima scansione...")

# === LOOP ===
if __name__ == "__main__":
    while True:
        asyncio.run(main())
        time.sleep(3600)
