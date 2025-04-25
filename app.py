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
import random

import fitz
from llm.agent import invoke

#pdf reader
def read_pdf_text(uploaded_file):
    text = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()

st.set_page_config(page_title="Enerji AI Asistanı", layout="wide")

PRED_ENDPOINT = "http://localhost:8002/predict"

st.sidebar.title("Breaker ➞ Makine Eşleme")
st.sidebar.text("Sürükle‑bırak diyagram ileride gelecek…")

# ----- Tablar -----
tab_dash, tab_upload, tab_chat = st.tabs(["📊 Dashboard", "📂 PDF Upload", "🤖 Chatbot"])

# -----------------------------------------------------------
# DASHBOARD TAB
# -----------------------------------------------------------
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
                timestamp=datetime.utcnow(),
                breaker_id=breaker_id,
                metrics={
                    "current": current,
                    "voltage": voltage,
                    "active_power": current * voltage / 1000,  # kW
                    "energy": (current * voltage / 1000) * 1,  # 1 saat varsayımıyla kWh
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
    valid_measurements = [
        m for m in st.session_state.get("measurements", [])
        if isinstance(m, RawMeasurement)
    ]
    
    breaker_energy = {}
    
    # Eğer breaker'lar var ama ölçüm yoksa, her birine sahte veri ata (grafik çalışsın diye)
    if not valid_measurements:
        for brk in st.session_state.breakers:
            energy = random.uniform(10, 100)
            fake_measurement = RawMeasurement(
                timestamp=datetime.utcnow(),
                breaker_id=brk,
                metrics={
                    "current": 0,
                    "voltage": 0,
                    "active_power": 0,
                    "energy": energy,
                    "reactive_power": 0,
                    "apparent_power": 0,
                    "power_factor": 0.9,
                    "leakage_current": 0,
                    "temperature": 25
                }
            )
            st.session_state.measurements.append(fake_measurement)

    # Breaker'lara göre enerji hesapla
    for m in valid_measurements:
        brk = m.breaker_id
        energy = m.metrics.get("energy", 0)
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

    st.header("🧁Breaker ekle ")

    if "devices" not in st.session_state:
        st.session_state.devices = []
    if "device_counter" not in st.session_state:
        st.session_state.device_counter = 0
    if "breakers" not in st.session_state:
        st.session_state.breakers = ["BRK‑1"]

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

                    #  Dosya içeriğini oku ve yazdır
                    pdf_text = read_pdf_text(pdf_file)
                    dev["pdf_text"] = pdf_text

                    st.success("PDF başarıyla okundu.")
                    st.code(pdf_text[:1000])

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

    with st.expander("📄 JSON Çıktısını Gör"):
        st.json(st.session_state.devices)

    st.subheader("📈 Grafik Oluştur")

    grafik_breaker = st.selectbox("Grafik için Breaker ID seç", st.session_state.breakers, key="plot_brk")
    grafik_tipi = st.selectbox("Grafik Türü", ["Aktif Güç", "Akım", "Gerilim"])
    zaman_araligi = st.selectbox("Zaman Aralığı", ["Son 24 Saat", "Son 7 Gün", "Son 30 Gün"])

    if st.button("📊 Grafiği Göster"):
        saat_sayisi = {"Son 24 Saat": 24, "Son 7 Gün": 7 * 24, "Son 30 Gün": 30 * 24}[zaman_araligi]
        zamanlar = [datetime.now() - timedelta(hours=i) for i in range(saat_sayisi)][::-1]
        degerler = np.random.uniform(10, 100, size=saat_sayisi)

        if zaman_araligi != "Son 24 Saat":
            zamanlar = zamanlar[::8]
            degerler = degerler[::8]

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
        zamanlar_b = [datetime.now() - timedelta(hours=i) for i in range(saat_sayisi_b)][::-1]

        alternatif_veriler = {
            "Sıcaklık": np.random.uniform(15, 35, size=saat_sayisi_b),
            "Güç Faktörü": np.random.uniform(0.7, 1.0, size=saat_sayisi_b),
            "Kaçak Akım": np.random.uniform(0, 0.03, size=saat_sayisi_b),
        }

        degerler_b = alternatif_veriler[alternatif_grafik_tipi]

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

    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])

    if prompt := st.chat_input("Sorunuzu yazın…"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

#LLM cağrısı
        answer = invoke({"input": prompt, "devices": st.session_state.devices})
        st.chat_message("assistant").markdown(answer["output"])
        st.session_state.messages.append({"role": "assistant", "content": answer["output"]})