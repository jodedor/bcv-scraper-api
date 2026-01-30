import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request
import json
from collections import OrderedDict
import os
import re

app = Flask(__name__)

# --- CONFIGURACIÓN ---
PATH_DISCO = "/data/bcv_data.json"
API_KEY_VALIDA = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"

def limpiar_fecha_bcv(texto_fecha):
    """Convierte 'Viernes, 30 Enero 2026' a '2026-01-30'"""
    meses = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
    }
    try:
        # Buscamos los números y el mes en el texto
        partes = texto_fecha.split()
        dia = partes[1].zfill(2)
        mes_nombre = partes[2]
        anio = partes[3]
        mes_num = meses.get(mes_nombre, "01")
        return f"{anio}-{mes_num}-{dia}"
    except:
        return "2026-01-30" # Fecha de respaldo en caso de error

def obtener_datos_almacenados():
    if os.path.exists(PATH_DISCO):
        with open(PATH_DISCO, 'r') as f:
            return json.load(f)
    else:
        valores_base = {
            "usd_actual": 363.6623, "eur_actual": 434.4273, "fecha_actual": "2026-01-29",
            "usd_previo": 361.4906, "eur_previo": 432.7151, "fecha_previa": "2026-01-28"
        }
        with open(PATH_DISCO, 'w') as f:
            json.dump(valores_base, f)
        return valores_base

def guardar_datos(datos):
    with open(PATH_DISCO, 'w') as f:
        json.dump(datos, f)

def get_bcv_data():
    memoria = obtener_datos_almacenados()
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            dolar_sitio = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_sitio = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            
            # Extraer y formatear fecha a YYYY-MM-DD
            fecha_raw = soup.find('span', class_='date-display-single').text.strip()
            fecha_formateada = limpiar_fecha_bcv(fecha_raw)
            
            if dolar_sitio != memoria["usd_actual"]:
                memoria["usd_previo"] = memoria["usd_actual"]
                memoria["eur_previo"] = memoria["eur_actual"]
                memoria["fecha_previa"] = memoria["fecha_actual"]
                
                memoria["usd_actual"] = dolar_sitio
                memoria["eur_actual"] = euro_sitio
                memoria["fecha_actual"] = fecha_formateada
                
                guardar_datos(memoria)

            ch_usd = ((memoria["usd_actual"] - memoria["usd_previo"]) / memoria["usd_previo"]) * 100
            ch_eur = ((memoria["eur_actual"] - memoria["eur_previo"]) / memoria["eur_previo"]) * 100

            # ESTRUCTURA EXACTA SOLICITADA
            return OrderedDict([
                ("current", OrderedDict([
                    ("usd", memoria["usd_actual"]),
                    ("eur", memoria["eur_actual"]),
                    ("date", memoria["fecha_actual"])
                ])),
                ("previous", OrderedDict([
                    ("usd", memoria["usd_previo"]),
                    ("eur", memoria["eur_previo"]),
                    ("date", memoria["fecha_previa"])
                ])),
                ("changePercentage", OrderedDict([
                    ("usd", ch_usd),
                    ("eur", ch_eur)
                ]))
            ])
    except:
        pass
    return None

@app.route('/')
def home():
    if request.headers.get('x-dolarvzla-key') != API_KEY_VALIDA:
        return Response('{"error": "No autorizado"}', status=401, mimetype='application/json')

    resultado = get_bcv_data()
    if resultado:
        return Response(json.dumps(resultado), mimetype='application/json')
    return Response('{"error": "Error"}', status=500, mimetype='application/json')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

