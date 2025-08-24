import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
import asyncio
import re
import time

# Env
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# Costanti
HEADERS = {"User-Agent": "Mozilla/5.0"}
URL = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url=https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031&language=it_IT"

sent_products = set()

async def send_to_telegram(bot, product):
    try:
        # Componi messaggio in stile influencer con ironia
        message = f"🛒 <b>{product['title']}</b>\n\n"
        if product['coupon']:
            message += f"🎟️ <b>Coupon disponibile!</b>\n"
        message += f"💰 <b>Ora a:</b> <b>{product['price']}</b>\n"
        if product['old_price']:
            message += f"💸 <b>Prezzo Consigliato:</b> <s>{product['old_price']}</s>\n"
        if product['lowest_30d']:
            message += f"📉 <b>Più basso ultimi 30 giorni:</b> {product['lowest_30d']}\n"
        if product['discount']:
            message += f"🔥 <b>Sconto:</b> {product['discount']}\n"
        if product['sold_by'] != "Non disponibile":
            message += f"🏪 <b>Venduto da:</b> {product['sold_by']}\n"
        if product['shipped_by'] != "Non disponibile":
            message += f"🚚 <b>Spedito da:</b> {product['shipped_by']}\n"
        message += f"\n👉 <a href='{product['link']}'>Scopri l’offerta su Amazon!</a>\n\n"
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
        lowest_30d_tag = product.find('span', string=re.compile(r"Prezzo più basso"))
        coupon_tag = product.find('span', string=re.compile(r"Coupon"))

        image_tag = product.select_one('img')
        link_tag = product.select_one('a.a-link-normal')

        if not title_tag or not price_tag:
            continue

        price = price_tag.text.strip()
        old_price = old_price_tag.text.strip() if old_price_tag else ""
        lowest_30d = lowest_30d_tag.find_next('span').text.strip() if lowest_30d_tag else ""
        has_coupon = True if coupon_tag else False

        discount = ""
        try:
            if old_price:
                p1 = float(re.sub(r"[^\d,]", "", old_price).replace(",", "."))
                p2 = float(re.sub(r"[^\d,]", "", price).replace(",", "."))
                sconto = round(100 - (p2 / p1 * 100))
                if sconto < 25:
                    continue
                discount = f"-{sconto}%" if sconto <= 70 else f"⚠️ Sconto anomalo: -{sconto}%"
        except:
            continue

        sold_by = "Non disponibile"
        shipped_by = "Non disponibile"
        merchant_info = product.select_one('.a-row.a-size-base.a-color-secondary')
        if merchant_info:
            merchant_text = merchant_info.get_text(strip=True)
            if "Venduto da" in merchant_text:
                sold_by_match = re.search(r"Venduto da ([^\.]+)", merchant_text)
                if sold_by_match:
                    sold_by = sold_by_match.group(1).strip()
            if "Spedito da" in merchant_text:
                shipped_by_match = re.search(r"Spedito da ([^\.]+)", merchant_text)
                if shipped_by_match:
                    shipped_by = shipped_by_match.group(1).strip()

        found.append({
            "asin": asin,
            "title": title_tag.text.strip(),
            "price": price,
            "old_price": old_price,
            "lowest_30d": lowest_30d,
            "discount": discount,
            "coupon": has_coupon,
            "image": image_tag["src"] if image_tag else "",
            "link": f"https://www.amazon.it/dp/{asin}/?tag={AFFILIATE_TAG}&language=it_IT",
            "sold_by": sold_by,
            "shipped_by": shipped_by
        })

    print(f"📦 Trovati {len(found)} prodotti con sconto.")
    return found

async def main():
    print("🔁 Avvio scansione prodotti...\n")
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
