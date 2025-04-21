from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain_community.tools import DuckDuckGoSearchRun
from ml.predict import predict_last_24h
from utils.schemas import RawMeasurement
import json, os

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def get_predictions(json_str: str):
    data = [RawMeasurement(**j) for j in json.loads(json_str)]
    return predict_last_24h(data)

tools = [
    Tool.from_function(
        name="get_predictions",
        func=get_predictions,
        description="Breaker ölçümlerinden gelecek ay fatura tahmini üretir"
    ),
    DuckDuckGoSearchRun(name="search_devices")
]

agent = initialize_agent(
    tools,
    llm,
    agent_type="openai-tools",
    verbose=True,
    system_message="Sen bir enerji verimliliği danışmanısın. Yanıtlarını Türkçe ver."
)

if __name__ == "__main__":
    sample = json.dumps([json.load(open("sample.json"))])
    resp = agent.invoke({"input": "Daha verimli bir motor öner ve faturayı tahmin et", "json_str": sample})
    print(resp["output"])
