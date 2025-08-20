import streamlit as st
import json
import os

st.set_page_config(page_title="Bellezza da Pazz - Dashboard", layout="centered")

st.title("📊 Dashboard - Prodotti Postati")

if os.path.exists("posted.json"):
    with open("posted.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    st.success(f"✅ Totale prodotti inviati: {len(data)}")
    
    st.markdown("### 📝 Ultimi 20 prodotti pubblicati:")
    for title in data[-20:][::-1]:
        st.write("•", title)
else:
    st.warning("⚠️ Nessun prodotto ancora inviato dal bot.")
