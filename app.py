import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import os

app = Flask(__name__)

# Simulación de datos previos (Ya que el BCV no los da en una sola tabla)
# En un escenario real, estos datos se guardarían en una base de datos
DATA_PREVIA = {
    "usd": 361.4906,
    "eur": 432.7150,
    "date": "2026-01-28"
}

@app.route('/')
def home():
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer precios actuales
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            fecha_actual = "2026-01-29" # Podrías extraerla dinámicamente o usar datetime

            # Cálculos de porcentaje de cambio
            change_usd = ((dolar_actual - DATA_PREVIA["usd"]) / DATA_PREVIA["usd"]) * 100
            change_eur = ((euro_actual - DATA_PREVIA["eur"]) / DATA_PREVIA["eur"]) * 100

            # Estructura exacta solicitada
            return jsonify({
                "current": {
                    "usd": dolar_actual,
                    "eur": euro_actual,
                    "date": fecha_actual
                },
                "previous": {
                    "usd": DATA_PREVIA["usd"],
                    "eur": DATA_PREVIA["eur"],
                    "date": DATA_PREVIA["date"]
                },
                "changePercentage": {
                    "usd": change_usd,
                    "eur": change_eur
                }
            })
        else:
            return jsonify({"status": "error", "message": "Error BCV"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
