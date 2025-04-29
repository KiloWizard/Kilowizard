import pandas as pd
import json
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib


def load_data(json_path="C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\data\\sample.json"):
    with open(json_path, "r") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    return df

def get_daily_energy(df: pd.DataFrame):
    df['date'] = df['timestamp'].dt.date
    daily_energy = df.groupby('date')['energy'].sum().reset_index()
    daily_energy['day'] = range(len(daily_energy))
    return daily_energy

def train_model(daily_energy: pd.DataFrame):
    X = df[['voltage', 'current', 'active_power']]
    y = df['energy']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    print("Model eğitildi. Skor:", model.score(X_test, y_test))

    # Modeli diske kaydet
    joblib.dump(model, "C:\\Users\\90554\\Documents\\GitHub\\Kilowizard\\ml\\bill_predictor.pkl")
    print("Model kaydedildi: models/bill_predictor.pkl")


if __name__ == "__main__":
    df = load_data()
    train_model(df)
