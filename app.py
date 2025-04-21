import streamlit as st, requests, json, os
from utils.schemas import RawMeasurement
from datetime import datetime

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

with tab_upload:
    st.header("Makine PDF Yükle")
    pdf_file = st.file_uploader("Teknik dökümanı seç", type=["pdf"])
    if pdf_file:
        st.success(f"Yüklendi: {pdf_file.name} (örnek embed işlemi burada yapılacak)")

with tab_chat:
    st.header("Enerji Chatbot")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])
    if prompt := st.chat_input("Sorunuzu yazın…"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role":"user","content":prompt})
        # ----- LLM çağrısı -----
        from llm.agent import agent
        answer = agent.invoke({"input": prompt})
        st.chat_message("assistant").markdown(answer["output"])
        st.session_state.messages.append({"role":"assistant","content":answer["output"]})
