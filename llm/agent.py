from langchain_openai import ChatOpenAI
from ml.predict import predict_energy
from ml.predict import  fault_detection
from ml.predict import leakage_anomaly_detection
import re
import json


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    openai_api_key=OPENAI_API_KEY
)

# Prompt oluştur
def build_prompt(data: dict) -> str:
    user_question = data.get("input", "")
    devices = data.get("devices", [])
    predict_result = data.get("predict_result", {})
    faults = data.get("faults", {})
    leakage_result = data.get("leakage_result", {})

    prompt_parts = [
        "Sen bir enerji verimliliği danışmanısın. Kullanıcıya aşağıdaki verilere göre yanıt ver.\n"
    ]

    # 🔹 Cihaz bilgileri (varsa)
    if devices:
        for i, dev in enumerate(devices, 1):
            prompt_parts.append(f"\n🔹 Cihaz {i}")
            prompt_parts.append(f"Cihaz Adı: {dev.get('cihaz_adi', '-')}")
            prompt_parts.append(f"Cihaz ID: {dev.get('Cihaz_id', '-')}")
            prompt_parts.append(f"Breaker ID: {dev.get('breaker_id', '-')}")
            prompt_parts.append(f"Yüklenen PDF: {dev.get('cihaz_pdf', '-')}")

            not_ = dev.get("kullanici_promptu", "")
            if not_:
                prompt_parts.append(f"Kullanıcı Notu: {not_}")

            text = dev.get("pdf_text", "")
            if text:
                prompt_parts.append("PDF Teknik İçeriği:\n" + text[:2000] + "\n---")


    # 🔸 Tahmini fatura bilgileri (her zaman)
    if predict_result:
        prompt_parts.append("\n🔸 AI destekli fatura tahmini sonuçları:")
        prompt_parts.append(f"- Tahmini günlük tüketim (kWh): {predict_result.get('daily_predictions_kWh', [])[:5]} ...")
        prompt_parts.append(f"- Aylık toplam enerji tüketimi (kWh): {predict_result.get('total_energy_kWh', '-')} kWh")
        prompt_parts.append(f"- Tahmini fatura tutarı (TL): {predict_result.get('estimated_cost_TL', '-')} TL")
        prompt_parts.append(
            "\nBu tahmin sonuçlarını KULLAN ve kullanıcıya net, kibar ve anlaşılır bir cevap ver. "
            "Kullanıcı sadece tahmini soruyorsa bunları özetle. Ekstra bilgi sorarsa açıklama yap."
        )

    if faults:
        prompt_parts.append("\n⚠️ Anomali tespiti:")
        for breaker, dates in faults.items():
            formatted_dates = ', '.join(dates)
            prompt_parts.append(f"- {breaker}: Şüpheli günler → {formatted_dates}")
        prompt_parts.append(
            "\nKullanıcı arıza hakkında soru sorarsa bu bilgileri detaylı paylaş. Sormazsa sadece özet geç.")

    if leakage_result:
        prompt_parts.append("\n⚡ Kaçak akım anomalisi tespiti:")
        for breaker, dates in leakage_result.items():
            formatted_dates = ', '.join(dates)
            prompt_parts.append(f"- {breaker}: Şüpheli günler → {formatted_dates}")
        prompt_parts.append(
            "\nKullanıcı kaçak akım hakkında soru sorarsa bu bilgileri detaylı paylaş. Sormazsa sadece özet geç."
        )

    prompt_parts.append(f"\nKullanıcının Sorusu: {user_question}")
    return "\n".join(prompt_parts)

    # Kullanıcı sorusu
    prompt_parts.append(f"\nKullanıcının Sorusu: {user_question}")
    return "\n".join(prompt_parts)

# LLM cevabını düzelt
def fix_output(text: str) -> str:
    text = re.sub(r"(\d)\.(\S)", r"\1. \2", text)
    text = re.sub(r"(\d\.\s)([A-ZÇĞİÖŞÜ])", r"\n\n\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)

    lines = text.splitlines()
    fixed_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.endswith((".", ":", "-", "…")):
            if not re.match(r"\d+\.\s", line):
                line += "."
        fixed_lines.append(line)

    return "\n".join(fixed_lines).strip()

# LLM çağırıcı
def invoke(data: dict):
    if "predict_result" not in data:
        try:
            with open("C:\\Users\\sozcu\\Desktop\\sample.json", "r") as f:
                measurements = json.load(f)
            voltage = sum([row["voltage"] for row in measurements]) / len(measurements)
            current = sum([row["current"] for row in measurements]) / len(measurements)
            active_power = sum([row["active_power"] for row in measurements]) / len(measurements)
            data["predict_result"] = predict_energy(voltage, current, active_power, n_days=30)
        except Exception as e:
            print(f"⚠️ Tahmin verisi yüklenemedi: {e}")
            data["predict_result"] = {}

    if "faults" not in data:
        try:
            faults = fault_detection("C:\\Users\\sozcu\\Desktop\\sample.json")
            data["faults"] = faults
            print("✅ fault_detection çalıştı, sonuç:", faults)
        except Exception as e:
            print(f"⚠️ Arıza verisi yüklenemedi: {e}")
            data["faults"] = {}

    final_prompt = build_prompt(data)
    print("📢 Final Prompt:\n", final_prompt)  # prompt içeriğini görmek için

    raw_output = llm.invoke(final_prompt)
    return {"output": fix_output(raw_output.content)}
