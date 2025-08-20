import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
import time
import os
import random

API_KEY = "3ed196232cadd0979e4c78e904782f3b"  # ScraperAPI
TG_BOT_TOKEN = "8382456117:AAHlbtYbKnu2ubytyxGAqFb3dkmd2gz1ucc"
TG_CHANNEL_ID = "@bellezzadapazzi"
AFFILIATE_TAG = "bellezzaerror-21"

KEYWORDS = [
    # Skincare
    "crema viso", "siero viso", "contorno occhi", "maschera viso", "crema antirughe",
    "detergente viso", "tonico viso", "crema corpo", "olio viso",

    # Make-up
    "fondotinta", "correttore", "cipria", "rossetto", "mascara", "matita occhi",
    "ombretto", "eyeliner", "trucco viso",

    # Igiene personale
    "spazzolino elettrico", "epilatore", "rasoio donna", "schiuma da barba", "ceretta",

    # Cura e benessere
    "olio essenziale", "crema mani", "balsamo labbra", "burrocacao", "crema solare",

    # Integratori
    "integratori pelle", "integratori unghie", "biotina", "collagene", "magnesio", "acido ialuronico"
]

HEADERS = {
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

bot = Bot(token=TG_BOT_TOKEN)

INTROS = [
    "💖 È il momento di brillare, bellezza!",
    "🌟 Offerta che fa girare la testa!",
    "✨ Piccolo prezzo, grande WOW!",
    "🛍️ Colpo di fulmine in arrivo!",
    "💅 La tua beauty routine sta per cambiare."
]

CTAS = [
    "👉 Ordinalo subito su Amazon, regina 💄",
    "🧴 Clicca qui e riempi il carrello come meriti 🛒",
    "💥 Vai di click e porta a casa il tuo must-have!",
    "👑 Acchiappa l’affare prima che sparisca!",
    "📦 Spedizione Prime e zero sbatti."
]

# Scarica HTML Amazon tramite ScraperAPI
def get_soup(scrape_url):
    api_url = f"https://api.scraperapi.com/?api_key={API_KEY}&url={scrape_url}"
    r = requests.get(api_url, headers=HEADERS)
    if r.status_code != 200:
        return None
    return BeautifulSoup(r.content, "html.parser")


# Estrae prodotti da una pagina Amazon search
def extract_products(soup):
    products = []
    items = soup.select("div.s-main-slot div.s-result-item")
    for item in items:
        title = item.select_one("h2 a span")
        price_whole = item.select_one("span.a-price-whole")
        price_frac = item.select_one("span.a-price-fraction")
        old_price = item.select_one("span.a-text-price")
        availability = item.select_one("span.a-color-price")
        link = item.select_one("h2 a")

        # Controllo disponibilità
        if availability and "non disponibile" in availability.text.lower():
            continue

        if title and price_whole and link:
            try:
                current_price = float(price_whole.text.replace(".", "").replace(",", ".") + "." + (price_frac.text.strip() if price_frac else "00"))
            except:
                continue

            old_price_val = None
            if old_price:
                try:
                    old_price_val = float(old_price.text.replace("€", "").replace("\xa0", "").replace(",", "."))
                except:
                    pass

            products.append({
                "title": title.text.strip(),
                "current_price": current_price,
                "old_price": old_price_val,
                "url": "https://www.amazon.it" + link["href"]
            })
    return products


# Genera messaggio Telegram
def generate_message(product):
    title = product["title"]
    price = product["current_price"]
    old_price = product["old_price"]
    link = product["url"].split("?")[0]
    affiliate_link = f"{link}?tag={AFFILIATE_TAG}"

    intro = random.choice(INTROS)
    cta = random.choice(CTAS)

    sconto = ""
    if old_price and old_price > price:
        perc = round((old_price - price) / old_price * 100)
        if perc >= 50:
            sconto = f"\n🔴 *SUPER OFFERTA: -{perc}%*"
        else:
            sconto = f"\n🔥 Sconto: -{perc}%"

    msg = (
        f"{intro}\n\n"
        f"*{title[:70]}*\n"
        f"💸 Prezzo: *{price:.2f}€*"
    )

    if old_price:
        msg += f"\n❌ Prezzo prima: {old_price:.2f}€"
    msg += sconto
    msg += f"\n\n{cta}\n[🛒 CLICCA QUI PER VEDERE IL PRODOTTO]({affiliate_link})"

    return msg


# Posta su Telegram
posted_links = set()

def post_product(product):
    link = product["url"].split("?")[0]
    if link in posted_links:
        return
    msg = generate_message(product)
    bot.send_message(chat_id=TG_CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    posted_links.add(link)
    print(f"✅ Postato: {product['title']}")


# MAIN
if __name__ == "__main__":
    for kw in KEYWORDS:
        print(f"🔎 Cerco: {kw}")
        url = f"https://www.amazon.it/s?k={kw.replace(' ', '+')}"
        soup = get_soup(url)
        if not soup:
            continue
        prodotti = extract_products(soup)
        for p in prodotti[:3]:
            if p["old_price"] and p["old_price"] > p["current_price"]:
                post_product(p)
            time.sleep(1)
        time.sleep(2)
