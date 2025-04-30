from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain_community.tools import DuckDuckGoSearchRun
from utils.schemas import RawMeasurement
import json, os
import re


OPENAI_API_KEY=""
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    openai_api_key=OPENAI_API_KEY
)


# Build the prompt
def build_prompt(data: dict) -> str:
    user_question = data.get("input", "")
    devices = data.get("devices", [])

    prompt_parts = [
        "Sen bir enerji verimliliği danışmanısın. Aşağıda kullanıcı tarafından girilmiş cihaz bilgileri, teknik döküman içerikleri ve kullanıcı notları yer alıyor. Bu bilgilere dayanarak akıllı cevaplar ver.\n"
    ]

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

    prompt_parts.append(f"\nKullanıcının Sorusu: {user_question}")
    return "\n".join(prompt_parts)


#  Fix the LLM output
def fix_output(text: str) -> str:
    # Liste başlıklarını düzgün ayır
    text = re.sub(r"(\d)\.(\S)", r"\1. \2", text)
    text = re.sub(r"(\d\.\s)([A-ZÇĞİÖŞÜ])", r"\n\n\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)

    # Nokta eksikse ekle
    lines = text.splitlines()
    fixed_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.endswith((".", ":", "-", "…")):
            if not re.match(r"\d+\.\s", line):
                line += "."
        fixed_lines.append(line)

    return "\n".join(fixed_lines).strip()


# Ana LLM çağırıcı
def invoke(data: dict):
    final_prompt = build_prompt(data)

    raw_output = llm.invoke(final_prompt)
    clean_output = fix_output(raw_output.content)

    return {"output": clean_output}