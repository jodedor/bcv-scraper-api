import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request
import json
import os
import time
from collections import OrderedDict

app = Flask(__name__)

API_KEY_VALIDA = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"
PATH_DISCO = "/data/bcv_data.json"

# --- CONFIGURACIÓN TELEGRAM ---
PATH_CONOCIDOS = "/data/conocidos.json"
TELEGRAM_TOKEN = "8097155705:AAECM-VdtI98giBr1Vl2WZ6ynNKHMTkfxPw"
TELEGRAM_CHAT_ID = "-5248292296"


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': mensaje}, timeout=5)
    except Exception as e:
        print(f"Error Telegram: {e}")

def registrar_dispositivo_nuevo(ip, agent):
    conocidos = []
    if os.path.exists(PATH_CONOCIDOS):
        try:
            with open(PATH_CONOCIDOS, 'r') as f:
                conocidos = json.load(f)
        except: conocidos = []
    
    if ip not in conocidos:
        conocidos.append(ip)
        with open(PATH_CONOCIDOS, 'w') as f:
            json.dump(conocidos, f)
        
        msg = f"🚀 ¡Nuevo ESP32 detectado!\n📍 IP: {ip}\n🤖 Agent: {agent}"
        enviar_telegram(msg)
# ------------------------------

# --- FUNCIÓN DE LECTURA SEGURA ---
def leer_datos_disco():
    try:
        if os.path.exists(PATH_DISCO):
            with open(PATH_DISCO, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error leyendo disco: {e}")
    
    return {
        "usd_actual": 361.4906, 
        "eur_actual": 432.7151, 
        "fecha_actual": "2026-01-28",
        "usd_previo": 361.4906,
        "eur_previo": 432.7151,
        "fecha_previa": "2026-01-28"
    }

def get_bcv_data():
    datos_viejos = leer_datos_disco()
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.encoding = 'utf-8' 
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            
            fecha_tag = soup.find("span", property="dc:date")
            if not fecha_tag:
                fecha_tag = soup.find("span", class_="date-display-single")

            if fecha_tag and fecha_tag.has_attr('content'):
                fecha_sitio = fecha_tag['content'].split('T')[0]
            else:
                fecha_sitio = time.strftime("%Y-%m-%d")

            if dolar_actual != datos_viejos.get("usd_actual") or fecha_sitio != datos_viejos.get("fecha_actual"):
                datos_para_guardar = {
                    "usd_actual": dolar_actual,
                    "eur_actual": euro_actual,
                    "fecha_actual": fecha_sitio,
                    "usd_previo": datos_viejos.get("usd_actual"),
                    "eur_previo": datos_viejos.get("eur_actual"),
                    "fecha_previa": datos_viejos.get("fecha_actual")
                }
                with open(PATH_DISCO, 'w') as f:
                    json.dump(datos_para_guardar, f)
                datos_finales = datos_para_guardar
            else:
                datos_finales = datos_viejos

            u_ant = datos_finales["usd_previo"]
            e_ant = datos_finales["eur_previo"]
            change_usd = ((datos_finales["usd_actual"] - u_ant) / u_ant) * 100
            change_eur = ((datos_finales["eur_actual"] - e_ant) / e_ant) * 100

            return OrderedDict([
                ("current", {"usd": datos_finales["usd_actual"], "eur": datos_finales["eur_actual"], "date": datos_finales["fecha_actual"]}),
                ("previous", {"usd": u_ant, "eur": e_ant, "date": datos_finales["fecha_previa"]}),
                ("changePercentage", {"usd": round(change_usd, 4), "eur": round(change_eur, 4)})
            ])
    except Exception as e:
        print(f"Error en proceso: {e}")
        return None

@app.route('/')
def home():
    print(f"--- NUEVA SOLICITUD --- Agent: {request.headers.get('User-Agent')} | IP: {request.remote_addr}")
    
    # Lógica de Telegram: Solo avisa si la IP no está en conocidos.json
    registrar_dispositivo_nuevo(request.remote_addr, request.headers.get('User-Agent'))

    if request.headers.get('x-dolarvzla-key') != API_KEY_VALIDA:
        return Response('{"error": "No autorizado"}', status=401, mimetype='application/json')

    data = get_bcv_data()
    if data:
        return Response(json.dumps(data), mimetype='application/json')
    return Response('{"error": "Error interno"}', status=500, mimetype='application/json')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
