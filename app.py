import requests
from bs4 import BeautifulSoup
from flask import Flask, Response
import json
from collections import OrderedDict
import os
import time

app = Flask(__name__)

# --- CONFIGURACIÓN DEL CACHE ---
cache_data = None
last_update_time = 0
CACHE_DURATION = 3600  # 1 hora en segundos

# Datos históricos (puedes actualizarlos manualmente aquí cuando cambien)
DATA_PREVIA = {
    "usd": 361.4906,
    "eur": 432.71509291,
    "date": "2026-01-28"
}

def get_bcv_data():
    """Realiza el scraping real al BCV"""
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # verify=False es necesario para el BCV a veces
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            fecha_actual = "2026-01-29" # O extraer dinámicamente

            change_usd = ((dolar_actual - DATA_PREVIA["usd"]) / DATA_PREVIA["usd"]) * 100
            change_eur = ((euro_actual - DATA_PREVIA["eur"]) / DATA_PREVIA["eur"]) * 100

            # Estructura idéntica y ordenada
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
                    ("usd", round(change_usd, 14)), # Manteniendo precisión para tu Wemos
                    ("eur", round(change_eur, 14))
                ]))
            ])
            return data
    except Exception as e:
        print(f"Error haciendo scraping: {e}")
    return None

@app.route('/')
def home():
    global cache_data, last_update_time
    
    current_time = time.time()
    
    # ¿Necesitamos actualizar? (Si no hay datos o si el cache expiró)
    if cache_data is None or (current_time - last_update_time) > CACHE_DURATION:
        print("🔄 Cache expirado o vacío. Consultando al BCV...")
        new_data = get_bcv_data()
        if new_data:
            cache_data = new_data
            last_update_time = current_time
        elif cache_data is None:
            # Si el BCV falla y no tenemos nada guardado, error
            return Response('{"error": "No se pudo obtener datos del BCV"}', status=500, mimetype='application/json')
    
    # Responder con lo que hay en cache (es instantáneo)
    return Response(json.dumps(cache_data), mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
