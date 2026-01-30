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

# --- FUNCIÓN DE LECTURA SEGURA ---
def leer_datos_disco():
    try:
        if os.path.exists(PATH_DISCO):
            with open(PATH_DISCO, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error leyendo disco: {e}")
    
    # Si el archivo no existe o está mal, devolvemos un backup para que no de Error 502
    return {
        "usd_actual": 361.4906, 
        "eur_actual": 432.7151, 
        "fecha_actual": "2026-01-28",
        "usd_previo": 361.4906,
        "eur_previo": 432.7151,
        "fecha_previa": "2026-01-28"
    }

def get_bcv_data():
    # 1. Leer lo que tenemos guardado
    datos_viejos = leer_datos_disco()
    
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer valores nuevos
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            # Extraer fecha del sitio
            # 1. Intentamos buscar por la clase CSS
            fecha_tag = soup.find(class_="date-display-single")

            if fecha_tag:
                # 2. Intentamos sacar el atributo 'content' si existe
                if fecha_tag.has_attr('content'):
                    fecha_sitio = fecha_tag['content'].split('T')[0]
                else:
                    # 3. Si no tiene 'content', limpiamos el texto "Lunes, 02 Febrero 2026"
                    # Esto es un respaldo por si el BCV cambia el formato
                    fecha_sitio = fecha_tag.text.strip()
            else:
    # 4. Si todo falla, que ponga la fecha del sistema para no enviar vacío
    import datetime
    fecha_sitio = datetime.datetime.now().strftime("%Y-%m-%d")

print(f"DEBUG: Fecha extraída -> {fecha_sitio}")
            # 2. COMPARAR: ¿El precio del BCV cambió respecto a lo que tenemos en el disco?
            if dolar_actual != datos_viejos.get("usd_actual"):
                # Si cambió, lo que antes era 'actual' ahora pasa a ser 'previo'
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

            # 3. CALCULAR PORCENTAJES
            u_ant = datos_finales["usd_previo"]
            e_ant = datos_finales["eur_previo"]
            change_usd = ((datos_finales["usd_actual"] - u_ant) / u_ant) * 100
            change_eur = ((datos_finales["eur_actual"] - e_ant) / e_ant) * 100

            # 4. RESPUESTA FORMATEADA PARA EL ESP32
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
    # Validación de Key
    if request.headers.get('x-dolarvzla-key') != API_KEY_VALIDA:
        return Response('{"error": "No autorizado"}', status=401, mimetype='application/json')

    data = get_bcv_data()
    if data:
        return Response(json.dumps(data), mimetype='application/json')
    return Response('{"error": "Error interno"}', status=500, mimetype='application/json')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
