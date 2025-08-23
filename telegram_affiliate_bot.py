import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

if not all([TG_BOT_TOKEN, TG_CHANNEL_ID, SCRAPER_API_KEY, AFFILIATE_TAG]):
    raise ValueError("❌ Una o più variabili ambiente mancanti. Controlla il file .env o la configurazione Railway.")

bot = Bot(token=TG_BOT_TOKEN)
SENT_PRODUCTS = set()

SEARCH_URL = f"https://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url=https://www.amazon.it/s?rh=n%3A6198082031%2Cp_n_deal_type%3A26901107031"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def extract_products(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("[data-asin]")
    print(f"🔎 Trovati {len(items)} elementi da Amazon.")
    products = []

    for item in items:
        asin = item.get("data-asin")
        if not asin or asin in SENT_PRODUCTS:
            continue

        title_el = item.select_one("h2 span")
        price_whole = item.select_one(".a-price .a-price-whole")
        price_fraction = item.select_one(".a-price .a-price-fraction")
        original_price_el = item.select_one(".a-text-price .a-offscreen")
        sold_by = item.select_one(".a-row.a-size-base.a-color-secondary")
        image_el = item.select_one("img")

        if not title_el or not price_whole:
            continue

        title = title_el.get_text(strip=True)
        image = image_el["src"] if image_el else ""
        try:
            price = float((price_whole.get_text() + (price_fraction.get_text() if price_fraction else "")).replace(".", "").replace(",", "."))
        except:
            continue

        if original_price_el:
            try:
                original_price = float(original_price_el.get_text(strip=True).replace("€", "").replace(".", "").replace(",", "."))
                discount = round((original_price - price) / original_price * 100)
            except:
                discount = 0
        else:
            discount = 0

        link = f"https://www.amazon.it/dp/{asin}/?tag={AFFILIATE_TAG}"

        venduto_spedito = sold_by.get_text(" ", strip=True) if sold_by else "Informazione non disponibile"

        msg = f"💥 *{title}*\n\n"
        msg += f"💶 Prezzo: {price:.2f}€"
        if discount:
            msg += f" (-{discount}%)"
        msg += f"\n📦 {venduto_spedito}\n"

        if discount >= 60:
            msg += "\n🔥 *ERRORE DI PREZZO?!* 🔥\n"
        elif discount >= 15:
            msg += "\n✨ Offerta interessante!\n"
        else:
            msg += "\n📉 Sconto leggero, ma potrebbe valerne la pena.\n"

        msg += f"\n👉 [Vedi su Amazon]({link})"

        products.append({
            "asin": asin,
            "message": msg,
            "image": image,
            "discount": discount
        })

    return products

def send_product(product):
    try:
        bot.send_photo(
            chat_id=TG_CHANNEL_ID,
            photo=product["image"],
            caption=product["message"],
            parse_mode="Markdown"
        )
        SENT_PRODUCTS.add(product["asin"])
        print(f"✅ Inviato: {product['asin']}")
    except Exception as e:
        print(f"❌ Errore invio prodotto {product['asin']}: {e}")

def main():
    while True:
        print("🔁 Avvio scansione prodotti...\n")
        try:
            response = requests.get(SEARCH_URL, headers=HEADERS)
            html = response.text

            if "html" not in response.headers.get("Content-Type", ""):
                print("❌ HTML non valido ricevuto.")
                time.sleep(60 * 5)
                continue

            products = extract_products(html)

            if products:
                print(f"📦 Trovati {len(products)} prodotti con sconto.")
                best_products = sorted(products, key=lambda x: x["discount"], reverse=True)

                for i, product in enumerate(best_products):
                    if product["discount"] >= 15 or i == 0:  # invia il primo comunque
                        send_product(product)
            else:
                print("📭 Nessun prodotto rilevante trovato.")

        except Exception as e:
            print(f"❌ Errore generale: {e}")

        print("⏱️ Attendo 60 minuti prima della prossima scansione...\n")
        time.sleep(60 * 60)

if __name__ == "__main__":
    main()
