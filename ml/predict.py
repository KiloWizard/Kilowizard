import joblib
import pandas as pd
import json

from utils.schemas import RawMeasurement
from sklearn.ensemble import IsolationForest


def predict_energy(voltage: float, current: float, active_power: float, n_days: int = 5):
    # Modeli yükle
    model = joblib.load("C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\ml\\bill_predictor.pkl")

    # n_days kadar aynı ölçüm değerleriyle tahmin yapılacak
    input_data = pd.DataFrame([{
        "voltage": voltage,
        "current": current,
        "active_power": active_power
    }] * n_days)

    predictions = model.predict(input_data)
    total_energy = predictions.sum()
    estimated_cost = total_energy * 2.1  # 1 kWh = 2.1 TL varsayımı

    return {
        "daily_predictions_kWh": [round(p, 2) for p in predictions],
        "total_energy_kWh": round(float(total_energy), 2),
        "estimated_cost_TL": round(float(estimated_cost), 2)
    }

def breaker_based_billing(json_path="C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\data\\sample.json"):
    # JSON dosyasını oku
    with open(json_path, "r") as f:
        data = json.load(f)

    # Veriyi pandas DataFrame'e çevir
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date

    # Devre ve güne göre enerji tüketimini topla
    grouped = df.groupby(['breaker_id', 'date'])['energy'].sum().reset_index()

    # Günlük tüketimi TL'ye çevir (örnek: 2.1 TL/kWh)
    grouped['daily_cost_TL'] = grouped['energy'] * 2.1

    # Her devre için toplam enerji ve toplam maliyeti hesapla
    total = grouped.groupby('breaker_id').agg({
        'energy': 'sum',
        'daily_cost_TL': 'sum'
    }).reset_index()

    # JSON formatında çıktı hazırla
    result = {
        row['breaker_id']: {
            "total_energy_kWh": round(row['energy'], 2),
            "total_cost_TL": round(row['daily_cost_TL'], 2)
        }
        for _, row in total.iterrows()
    }

    return result

def leakage_anomaly_detection(json_path="C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\data\\sample.json"):
    # JSON verisini oku
    with open(json_path, "r") as f:
        data = json.load(f)

    # Pandas DataFrame'e çevir
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Gerekli alanları seç
    leakage_data = df[['breaker_id', 'timestamp', 'leakage_current']]

    # Isolation Forest modelini kur
    model = IsolationForest(contamination=0.05, random_state=42)
    leakage_data['anomaly'] = model.fit_predict(leakage_data[['leakage_current']])

    # Anomali (-1) olanları grupla
    result = {}
    for _, row in leakage_data.iterrows():
        if row['anomaly'] == -1:
            breaker = row['breaker_id']
            date = str(row['timestamp'].date())
            if breaker not in result:
                result[breaker] = []
            result[breaker].append(date)

    return result

def fault_detection(json_path="C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\data\\sample.json"):
    with open(json_path, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Gerekli alanlar
    fault_data = df[['breaker_id', 'timestamp', 'voltage', 'current', 'active_power']]

    # Modeli kur
    model = IsolationForest(contamination=0.05, random_state=42)
    fault_data['anomaly'] = model.fit_predict(fault_data[['voltage', 'current', 'active_power']])

    # Anomali (-1) olanları grupla
    result = {}
    for _, row in fault_data.iterrows():
        if row['anomaly'] == -1:
            breaker = row['breaker_id']
            date = str(row['timestamp'].date())
            if breaker not in result:
                result[breaker] = []
            result[breaker].append(date)

    return result

if __name__ == "__main__":
    output = fault_detection()
    print(json.dumps(output, indent=2))

# if __name__ == "__main__":
#     output = leakage_anomaly_detection()
#     print(json.dumps(output, indent=2))


# if __name__ == "__main__":
#     result = predict_energy(voltage=230.0, current=12.0, active_power=2.8, n_days=5)
#     print(json.dumps(result, indent=2))
#
#
# if __name__ == "__main__":
#     output = breaker_based_billing()
#     print(json.dumps(output, indent=2))