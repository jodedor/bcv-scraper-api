import requests
from bs4 import BeautifulSoup
from flask import Flask, Response
import json
from collections import OrderedDict
import os

app = Flask(__name__)

# Datos previos para que el cálculo de porcentaje no dé error
DATA_PREVIA = {
    "usd": 361.491,
    "eur": 432.715,
    "date": "28-01-2026"
}

@app.route('/')
def home():
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer y redondear
            dolar_actual = round(float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.')), 4)
            euro_actual = round(float(soup.find(id="euro").find('strong').text.strip().replace(',', '.')), 8)
            
            # Formato de fecha igual al que tu Wemos espera: DD-MM-YYYY
            fecha_actual = "29-01-2026" 

            # Cálculos solicitados
            change_usd = ((dolar_actual - DATA_PREVIA["usd"]) / DATA_PREVIA["usd"]) * 100
            change_eur = ((euro_actual - DATA_PREVIA["eur"]) / DATA_PREVIA["eur"]) * 100

            # Estructura EXACTA y ORDENADA
            data = OrderedDict([
                ("current", OrderedDict([
                    ("usd", dolar_actual),
                    ("eur", euro_actual),
                    ("date", fecha_actual)
                ])),
                ("previous", OrderedDict([
                    ("usd", DATA_PREVIA["usd"]),
                    ("eur", DATA_PREVIA["eur"]),
                    ("date", DATA_PREVIA["date"])
                ])),
                ("changePercentage", OrderedDict([
                    ("usd", change_usd),
                    ("eur", change_eur)
                ]))
            ])

            return Response(json.dumps(data), mimetype='application/json')
            
        return Response('{"error": "BCV fail"}', status=500, mimetype='application/json')
    except Exception as e:
        return Response(f'{{"error": "{str(e)}"}}', status=500, mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
