import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request
import json
from collections import OrderedDict
import os
import time

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# Esta es la llave que ya tiene tu Wemos configurada
API_KEY_VALIDA = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"

cache_data = None
last_update_time = 0
CACHE_DURATION = 3600  # 1 hora

DATA_PREVIA = {
    "usd": 361.4906,
    "eur": 432.71509291,
    "date": "2026-01-28"
}

def get_bcv_data():
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            fecha_actual = "2026-01-29"

            change_usd = ((dolar_actual - DATA_PREVIA["usd"]) / DATA_PREVIA["usd"]) * 100
            change_eur = ((euro_actual - DATA_PREVIA["eur"]) / DATA_PREVIA["eur"]) * 100

            data = OrderedDict([
                ("current", OrderedDict([
                    ("usd", round(dolar_actual, 4)),
                    ("eur", round(euro_actual, 8)),
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
            return data
    except Exception as e:
        print(f"Error scraping: {e}")
    return None

@app.route('/')
def home():
    global cache_data, last_update_time

    # --- VALIDACIÓN DE API KEY ---
    # Tu Wemos envía: http.addHeader("x-dolarvzla-key", config.apiKey);
    api_key_recibida = request.headers.get('x-dolarvzla-key')

    if api_key_recibida != API_KEY_VALIDA:
        return Response(
            json.dumps({"status": "error", "message": "No autorizado. API Key invalida."}),
            status=401,
            mimetype='application/json'
        )

    # --- LÓGICA DE CACHE ---
    current_time = time.time()
    if cache_data is None or (current_time - last_update_time) > CACHE_DURATION:
        new_data = get_bcv_data()
        if new_data:
            cache_data = new_data
            last_update_time = current_time
        elif cache_data is None:
            return Response('{"error": "BCV inalcanzable"}', status=500, mimetype='application/json')

    return Response(json.dumps(cache_data), mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

