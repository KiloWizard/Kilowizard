import streamlit as st, requests, json, os
from utils.schemas import RawMeasurement
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Enerji AI Asistanı", layout="wide")

PRED_ENDPOINT = "http://localhost:8002/predict"

# ----- Sidebar -----
st.sidebar.title("Breaker ➞ Makine Eşleme")
st.sidebar.text("Sürükle‑bırak diyagram ileride gelecek…")

# ----- Tablar -----
tab_dash, tab_upload, tab_chat = st.tabs(["📊 Dashboard", "📂 PDF Upload", "🤖 Chatbot"])

with tab_dash:
    st.header("Canlı Ölçümler")
    if "measurements" not in st.session_state:
        st.session_state.measurements = []
    col1, col2 = st.columns(2)
    with col1:
        breaker_id = st.text_input("Breaker ID", value="BRK-12-A1")
        current = st.number_input("Akım (A)", value=30.0)
        voltage = st.number_input("Gerilim (V)", value=400.0)
        if st.button("Gönder"):
            measurement = RawMeasurement(
                timestamp=datetime.utcnow(), breaker_id=breaker_id,
                metrics={"current": current, "voltage": voltage,
                         "active_power": current*voltage/1000,
                         "reactive_power": 0, "apparent_power":0,
                         "power_factor":0.9, "energy":0,
                         "leakage_current":0, "temperature":25}
            )
            st.session_state.measurements.append(measurement)
    with col2:
        if st.button("24 saat Tahmin"):
            js = [m.model_dump_json() for m in st.session_state.measurements]
            resp = requests.post(PRED_ENDPOINT, json={"data": js}).json()
            st.metric("Beklenen Fatura (TL)", resp["expected_cost"])

# -----------------------------------------------------------
# PDF UPLOAD TAB – Breaker başına dinamik cihaz yönetimi + Grafik
# -----------------------------------------------------------
with tab_upload:
    st.header("Makine PDF Yükle")

    if "devices" not in st.session_state:
        st.session_state.devices = []
    if "device_counter" not in st.session_state:
        st.session_state.device_counter = 0
    if "breakers" not in st.session_state:
        st.session_state.breakers = ["BRK‑1"]

    breakers_with_new = st.session_state.breakers + ["➕ Yeni Breaker…"]
    selection = st.selectbox("Breaker ID seç", breakers_with_new, key="sel_breaker")

    if selection == "➕ Yeni Breaker…":
        new_brk = st.text_input("Yeni Breaker ID girin")
        if st.button("Ekle"):
            if new_brk and new_brk not in st.session_state.breakers:
                st.session_state.breakers.append(new_brk)
                st.success(f"'{new_brk}' eklendi.")
                st.experimental_rerun()
        st.stop()

    breaker_id = selection
    st.divider()

    # Grafik alanı
    with st.expander("📊 Geçmiş Verilerden Grafik Oluştur"):
        zaman_araligi = st.selectbox("Zaman Aralığı", ["Son 24 saat", "Son 1 ay", "Son 3 ay", "Son 1 yıl"])
        grafik_tipi = st.selectbox("Gösterilecek Veri", [
            "Gerilim (Voltaj)",
            "Akım (Amper)",
            "Aktif Güç (kW)",
            "Hesaplanan Fatura Gideri",
            "Enerji Tüketimi (kWh)"
        ])

        # Örnek veri ile grafik (gerçek veriyle entegre edilecek)
        tarih = pd.date_range(end=datetime.today(), periods=30)
        veri = np.random.rand(len(tarih)) * 100
        fig, ax = plt.subplots()
        ax.plot(tarih, veri)
        ax.set_title(grafik_tipi)
        ax.set_ylabel(grafik_tipi)
        ax.set_xlabel("Tarih")
        st.pyplot(fig)

    # Cihaz kutuları
    existing = [d for d in st.session_state.devices if d["breaker_id"] == breaker_id]
    for dev in existing:
        with st.expander(f"🗂️ Cihaz {dev['Cihaz_id']}", expanded=True):
            cols = st.columns([2, 3, 3, 3, 1])

            cols[0].markdown("**Ayarlar**")

            dev["cihaz_adi"] = cols[1].text_input(
                "Cihaz adı", value=dev.get("cihaz_adi", ""),
                key=f"name_{dev['Cihaz_id']}"
            )

            pdf_file = cols[2].file_uploader(
                "Teknik PDF", type=["pdf"],
                key=f"pdf_{dev['Cihaz_id']}"
            )
            if pdf_file:
                dev["cihaz_pdf"] = pdf_file.name
                dev["file_obj"] = pdf_file

            dev["kullanıcı_promptu"] = cols[3].text_input(
                "Kullanıcı promptu", value=dev.get("kullanıcı_promptu", ""),
                key=f"prompt_{dev['Cihaz_id']}"
            )

            if cols[4].button("🗑️", key=f"del_{dev['Cihaz_id']}"):
                st.session_state.devices.remove(dev)
                st.experimental_rerun()

    if st.button("➕ Yeni Cihaz Ekle"):
        new_id = st.session_state.device_counter
        st.session_state.device_counter += 1
        st.session_state.devices.append({
            "Cihaz_id": new_id,
            "cihaz_pdf": "null",
            "breaker_id": breaker_id,
            "kullanıcı_promptu": "",
        })
        st.experimental_rerun()

    with st.expander("📄 JSON Çıktısını Gör"):
        st.json(st.session_state.devices)


with tab_chat:
    st.header("Enerji Chatbot")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])
    if prompt := st.chat_input("Sorunuzu yazın…"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role":"user","content":prompt})
        from llm.agent import agent
        answer = agent.invoke({"input": prompt})
        st.chat_message("assistant").markdown(answer["output"])
        st.session_state.messages.append({"role":"assistant","content":answer["output"]})
