
import streamlit as st 
import requests
import json
import os
from utils.schemas import RawMeasurement
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import plotly.express as px

import fitz
from llm.agent import invoke

st.set_page_config(page_title="Enerji AI Asistanı", layout="wide")



# ----- PDF READER -----
def read_pdf_text(uploaded_file):
    text = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


PRED_ENDPOINT = "http://localhost:8002/predict"

st.sidebar.title("Breaker ➞ Makine Eşleme")
st.sidebar.text("Sürükle‑bırak diyagram ileride gelecek…")

# ----- Verileri JSON dosyasından oku -----
if "measurements" not in st.session_state:
    st.session_state.measurements = []

    with open(r"C:\Users\sozcu\Desktop\sample.json", "r") as f:
        data = json.load(f)

    for item in data:
        measurement = RawMeasurement(
            timestamp=datetime.fromisoformat(item["timestamp"]),
            breaker_id=item["breaker_id"],
            metrics={
                "voltage": item.get("voltage", 0),
                "current": item.get("current", 0),
                "active_power": item.get("active_power", 0),
                "energy": item.get("energy", 0),
                "reactive_power": 0,
                "apparent_power": 0,
                "power_factor": 0.9,
                "leakage_current": item.get("leakage_current", 0),
                "temperature": 25
            }
        )
        st.session_state.measurements.append(measurement)

# ----- TABS -----
tab_dash, tab_upload, tab_chat = st.tabs(["📊 Dashboard", "📂 PDF Upload", "🤖 Chatbot"])

# -----------------------------------------------------------
# DASHBOARD TAB
# -----------------------------------------------------------
with tab_dash:
    st.header("Canlı Ölçümler")

    col1, col2 = st.columns(2)

    with col1:
        breaker_id = st.text_input("Breaker ID", value="CB-01")
        current = st.number_input("Akım (A)", value=30.0)
        voltage = st.number_input("Gerilim (V)", value=230.0)

        if st.button("Gönder"):
            measurement = RawMeasurement(
                timestamp=datetime.utcnow(),
                breaker_id=breaker_id,
                metrics={
                    "current": current,
                    "voltage": voltage,
                    "active_power": current * voltage / 1000,
                    "energy": (current * voltage / 1000) * 1,
                    "reactive_power": 0,
                    "apparent_power": 0,
                    "power_factor": 0.9,
                    "leakage_current": 0,
                    "temperature": 25
                }
            )
            st.session_state.measurements.append(measurement)

    with col2:
        if st.button("24 saat Tahmin"):
            js = [m.model_dump_json() for m in st.session_state.measurements]
            resp = requests.post(PRED_ENDPOINT, json={"data": js}).json()
            st.metric("Beklenen Fatura (TL)", resp["expected_cost"])

# -----------------------------------------------------------
# PDF UPLOAD TAB
# -----------------------------------------------------------
with tab_upload:
    valid_measurements = st.session_state.measurements

    breaker_energy = {}
    for m in valid_measurements:
        brk = m.breaker_id
        energy = getattr(m.metrics, "energy", 0)
        breaker_energy[brk] = breaker_energy.get(brk, 0) + energy

    st.subheader("⚡ Breaker'lara Göre Enerji Payı")
    if len(breaker_energy) >= 2:
        pie_fig = px.pie(
            names=list(breaker_energy.keys()),
            values=list(breaker_energy.values()),
            title="Breaker Enerji Dağılımı (kWh)",
        )
        pie_fig.update_traces(textinfo="percent+label")
        st.plotly_chart(pie_fig, use_container_width=True)
        st.markdown("---")
    else:
        st.warning("Enerji payı gösterimi için en az 2 farklı breaker gereklidir.")

    st.header("Breaker ekle ")

    if "devices" not in st.session_state:
        st.session_state.devices = []
    if "device_counter" not in st.session_state:
        st.session_state.device_counter = 0
    if "breakers" not in st.session_state:
        st.session_state.breakers = list(set([m.breaker_id for m in st.session_state.measurements]))

    breakers_with_new = st.session_state.breakers + ["➕ Yeni Breaker…"]
    selection = st.selectbox("Breaker ID seç", breakers_with_new, key="sel_breaker")

    if selection == "➕ Yeni Breaker…":
        new_brk = st.text_input("Yeni Breaker ID girin")
        if st.button("Ekle"):
            if new_brk and new_brk not in st.session_state.breakers:
                st.session_state.breakers.append(new_brk)
                st.success(f"'{new_brk}' eklendi.")
                st.experimental_rerun()
        st.stop()

    breaker_id = selection
    st.divider()
    st.subheader(f"🔌 '{breaker_id}' için Tanımlı Cihazlar")

    existing = [d for d in st.session_state.devices if d["breaker_id"] == breaker_id]
    for dev in existing:
        cihaz_adi = dev.get("cihaz_adi", "").strip()
        exp_title = f"📂 {cihaz_adi if cihaz_adi else 'Cihaz ' + str(dev['Cihaz_id'])}"
        with st.expander(exp_title, expanded=True):
            cols = st.columns([2, 3, 3, 3, 1])
            cols[0].markdown("**Ayarlar**")

            tmp_name = cols[1].text_input("Cihaz adı", value=dev.get("cihaz_adi", ""), key=f"name_{dev['Cihaz_id']}")

            pdf_file = cols[2].file_uploader("Teknik PDF", type=["pdf"], key=f"pdf_{dev['Cihaz_id']}")
            if pdf_file is not None:
                try:
                    dev["cihaz_pdf"] = pdf_file.name
                    dev["file_obj"] = pdf_file
                    pdf_text = read_pdf_text(pdf_file)
                    dev["pdf_text"] = pdf_text

                except Exception as e:
                    st.error(f"PDF okunurken hata oluştu: {e}")

            tmp_prompt = cols[3].text_input("Kullanıcı promptu", value=dev.get("kullanıcı_promptu", ""), key=f"prompt_{dev['Cihaz_id']}")

            with cols[4]:
                if st.button("💾 Kaydet", key=f"save_{dev['Cihaz_id']}"):
                    dev["cihaz_adi"] = tmp_name
                    dev["kullanıcı_promptu"] = tmp_prompt
                    st.success(f"Cihaz {dev['Cihaz_id']} güncellendi.")
                    st.experimental_rerun()

                if st.button("🗑️ Sil", key=f"del_{dev['Cihaz_id']}"):
                    st.session_state.devices.remove(dev)
                    st.experimental_rerun()

    if st.button("➕ Yeni Cihaz Ekle"):
        new_id = st.session_state.device_counter
        st.session_state.device_counter += 1
        st.session_state.devices.append({
            "Cihaz_id": new_id,
            "cihaz_pdf": "null",
            "breaker_id": breaker_id,
            "kullanıcı_promptu": "",
        })
        st.experimental_rerun()



    st.subheader("📈 Grafik Oluştur")
    grafik_breaker = st.selectbox("Grafik için Breaker ID seç", st.session_state.breakers, key="plot_brk")
    grafik_tipi = st.selectbox("Grafik Türü", ["Aktif Güç", "Akım", "Gerilim"])
    zaman_araligi = st.selectbox("Zaman Aralığı", ["Son 7 Gün", "Son 30 Gün"])

    if st.button("📊 Grafiği Göster"):
        metric_key = {"Aktif Güç": "active_power", "Akım": "current", "Gerilim": "voltage"}[grafik_tipi]
        measurements = [m for m in st.session_state.measurements if m.breaker_id == grafik_breaker]
        zamanlar = [m.timestamp for m in measurements]
        degerler = [m.metrics.dict().get(metric_key, 0) for m in measurements]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(zamanlar, degerler, marker="o", linestyle="-")
        ax.set_title(f"{grafik_tipi} - {grafik_breaker} ({zaman_araligi})", fontsize=14)
        ax.set_xlabel("Zaman", fontsize=12)
        ax.set_ylabel(grafik_tipi, fontsize=12)
        ax.grid(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b\n%H:%M'))
        fig.autofmt_xdate()
        st.pyplot(fig)
        st.markdown("---")

    st.subheader("Anlık Grafik Takibi")
    alternatif_grafik_tipi = st.radio("Anlık Grafik Türü", ["Sıcaklık", "Güç Faktörü", "Kaçak Akım"], horizontal=True)

    if st.button("Grafiği Göster"):
        saat_sayisi_b = 48
        measurements = st.session_state.measurements[-saat_sayisi_b:]
        zamanlar_b = [m.timestamp for m in measurements]

        if alternatif_grafik_tipi == "Sıcaklık":
            degerler_b = [getattr(m.metrics, "temperature", 25) for m in measurements]
        elif alternatif_grafik_tipi == "Güç Faktörü":
            degerler_b = [getattr(m.metrics, "power_factor", 0.9) for m in measurements]
        elif alternatif_grafik_tipi == "Kaçak Akım":
            degerler_b = [getattr(m.metrics, "leakage_current", 0) for m in measurements]
        else:
            degerler_b = [0 for _ in measurements]

        fig_b, ax_b = plt.subplots(figsize=(10, 4))
        ax_b.plot(zamanlar_b, degerler_b, color="orange", marker="x", linestyle="--")
        ax_b.set_title(f"{alternatif_grafik_tipi} - {grafik_breaker} (Son 48 Saat)")
        ax_b.set_xlabel("Zaman")
        ax_b.set_ylabel(alternatif_grafik_tipi)
        ax_b.grid(True)
        fig_b.autofmt_xdate()
        st.pyplot(fig_b)

# -----------------------------------------------------------
# CHATBOT TAB
# -----------------------------------------------------------
with tab_chat:
    st.header("Enerji Chatbot")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "awaiting_response" not in st.session_state:
        st.session_state.awaiting_response = False

    # 🟦 Konuşma kutusuna tüm mesajları dök
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).markdown(msg["content"])

        st.markdown('<div id="scroll-to-end"></div>', unsafe_allow_html=True)

    # 🟩 Giriş kutusu (sadece cevap beklenmiyorsa görünür)
    if not st.session_state.awaiting_response:
        prompt = st.chat_input("Sorunuzu yazın…")
        if prompt:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.awaiting_response = True
            st.session_state.last_prompt = prompt
            st.experimental_rerun()

    # 🧠 Cevap bekleniyorsa, invoke et ve input gizliyken cevapla
    elif st.session_state.awaiting_response and "last_prompt" in st.session_state:
        prompt = st.session_state.last_prompt
        response = invoke({"input": prompt, "devices": st.session_state.get("devices", [])})
        st.chat_message("assistant").markdown(response["output"])
        st.session_state.messages.append({"role": "assistant", "content": response["output"]})
        st.session_state.awaiting_response = False
        del st.session_state.last_prompt
        st.experimental_rerun()

   




