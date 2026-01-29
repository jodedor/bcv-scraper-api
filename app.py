import requests
from bs4 import BeautifulSoup
from flask import Flask, Response
import json
from collections import OrderedDict
import os

app = Flask(__name__)

# Datos previos simulados
DATA_PREVIA = {
    "usd": 361.491,
    "eur": 432.715,
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
            
            # Extraer y formatear a 3 decimales
            dolar_actual = round(float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.')), 3)
            euro_actual = round(float(soup.find(id="euro").find('strong').text.strip().replace(',', '.')), 3)
            fecha_actual = "2026-01-29"

            # Cálculos con 3 decimales
            change_usd = round(((dolar_actual - DATA_PREVIA["usd"]) / DATA_PREVIA["usd"]) * 100, 3)
            change_eur = round(((euro_actual - DATA_PREVIA["eur"]) / DATA_PREVIA["eur"]) * 100, 3)

            # Usamos OrderedDict para FORZAR el orden de las llaves
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

            # Generamos el JSON manualmente para asegurar que Flask no lo reordene
            json_response = json.dumps(data)
            return Response(json_response, mimetype='application/json')
            
        else:
            return Response('{"error": "BCV no responde"}', mimetype='application/json', status=500)
    except Exception as e:
        return Response(f'{{"error": "{str(e)}"}}', mimetype='application/json', status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
