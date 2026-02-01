import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request, render_template_string, redirect
import json
import os
import time
import secrets
from datetime import datetime
from collections import OrderedDict

app = Flask(__name__)

# --- CONFIGURACIÓN ORIGINAL ---
API_KEY_VALIDA = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"
PATH_DISCO = "/data/bcv_data.json"
PATH_CONOCIDOS = "/data/conocidos.json"
PATH_ULTIMO_ENVIO = "/data/ultimo_envio.txt"
TELEGRAM_TOKEN = "8097155705:AAECM-VdtI98giBr1Vl2WZ6ynNKHMTkfxPw"
TELEGRAM_CHAT_ID = "-5248292296"
INTERVALO_BINANCE_MINUTOS = 90

# --- NUEVA CONFIGURACIÓN ADMINISTRATIVA ---
PATH_DB_LLAVES = "/data/db_llaves.json"

# --- FUNCIONES DE BASE DE DATOS ADMINISTRATIVA ---
def cargar_db_llaves():
    if not os.path.exists(PATH_DB_LLAVES):
        return {"llaves": {}}
    try:
        with open(PATH_DB_LLAVES, "r") as f:
            return json.load(f)
    except: return {"llaves": {}}

def guardar_db_llaves(db):
    with open(PATH_DB_LLAVES, "w") as f:
        json.dump(db, f, indent=4)

# --- FUNCIONES ORIGINALES (SIN CAMBIOS) ---
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'}, timeout=5)
    except Exception as e:
        print(f"Error Telegram: {e}")

def get_binance_p2p():
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"asset": "USDT", "fiat": "VES", "merchantCheck": False, "page": 1, "rows": 1, "tradeType": "BUY", "transAmount": "500"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        datos = r.json()
        if datos.get('success') and len(datos['data']) > 0:
            return datos['data'][0]['adv']['price']
    except: return "N/A"
    return "N/A"

def registrar_dispositivo_nuevo(ip, agent):
    conocidos = []
    if os.path.exists(PATH_CONOCIDOS):
        try:
            with open(PATH_CONOCIDOS, 'r') as f: conocidos = json.load(f)
        except: conocidos = []
    if ip not in conocidos:
        conocidos.append(ip)
        with open(PATH_CONOCIDOS, 'w') as f: json.dump(conocidos, f)
        enviar_telegram(f"🚀 ¡Nuevo ESP32 detectado!\n📍 IP: {ip}\n🤖 Agent: {agent}")

def debe_enviar_binance():
    ahora = time.time()
    if not os.path.exists(PATH_ULTIMO_ENVIO): return True
    try:
        with open(PATH_ULTIMO_ENVIO, 'r') as f: ultimo_envio = float(f.read().strip())
        return ((ahora - ultimo_envio) / 60) >= INTERVALO_BINANCE_MINUTOS
    except: return True

def actualizar_hora_envio():
    with open(PATH_ULTIMO_ENVIO, 'w') as f: f.write(str(time.time()))

def leer_datos_disco():
    if os.path.exists(PATH_DISCO):
        try:
            with open(PATH_DISCO, 'r') as f: return json.load(f)
        except: pass
    return {"usd_actual": 361.4906, "eur_actual": 432.7151, "fecha_actual": "2026-01-28", "usd_previo": 361.4906, "eur_previo": 432.7151, "fecha_previa": "2026-01-28"}

def get_bcv_data():
    datos_viejos = leer_datos_disco()
    url = "https://www.bcv.org.ve/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            dolar_actual = float(soup.find(id="dolar").find('strong').text.strip().replace(',', '.'))
            euro_actual = float(soup.find(id="euro").find('strong').text.strip().replace(',', '.'))
            fecha_tag = soup.find("span", property="dc:date") or soup.find("span", class_="date-display-single")
            fecha_sitio = fecha_tag['content'].split('T')[0] if fecha_tag and fecha_tag.has_attr('content') else time.strftime("%Y-%m-%d")

            if dolar_actual != datos_viejos.get("usd_actual") or fecha_sitio != datos_viejos.get("fecha_actual"):
                datos_finales = {"usd_actual": dolar_actual, "eur_actual": euro_actual, "fecha_actual": fecha_sitio, "usd_previo": datos_viejos.get("usd_actual"), "eur_previo": datos_viejos.get("eur_actual"), "fecha_previa": datos_viejos.get("fecha_actual")}
                with open(PATH_DISCO, 'w') as f: json.dump(datos_finales, f)
            else: datos_finales = datos_viejos

            u_ant, e_ant = datos_finales["usd_previo"], datos_finales["eur_previo"]
            return OrderedDict([
                ("current", {"usd": datos_finales["usd_actual"], "eur": datos_finales["eur_actual"], "date": datos_finales["fecha_actual"]}),
                ("previous", {"usd": u_ant, "eur": e_ant, "date": datos_finales["fecha_previa"]}),
                ("changePercentage", {"usd": round(((datos_finales["usd_actual"] - u_ant) / u_ant) * 100, 4), "eur": round(((datos_finales["eur_actual"] - e_ant) / e_ant) * 100, 4)})
            ])
    except: return None

# --- RUTAS ADMINISTRATIVAS (NUEVAS) ---

HTML_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <title>Panel Control Letreros</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #007bff; color: white; }
        .btn { padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; color: white; text-decoration: none; font-size: 13px; }
        .btn-add { background: #28a745; padding: 10px 20px; font-size: 15px; }
        .btn-edit { background: #17a2b8; }
        .btn-status { background: #ffc107; color: black; }
        .btn-del { background: #dc3545; }
        code { background: #f8f9fa; padding: 4px; border-radius: 4px; font-size: 14px; color: #e83e8c; word-break: break-all; border: 1px solid #ddd; }
        .status-activa { color: green; font-weight: bold; }
        .status-bloqueada { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🛠️ Gestión de API Keys para Letreros</h2>
        <form action="/crear" method="post" style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            <input type="text" name="cliente" placeholder="Nombre del Cliente / Ubicación" required style="padding: 10px; width: 300px; border: 1px solid #ccc; border-radius: 4px;">
            <button type="submit" class="btn btn-add">Generar Nueva Clave</button>
        </form>

        <table>
            <tr>
                <th>Cliente</th>
                <th>API Key (SHA-256)</th>
                <th>Estado</th>
                <th>Acciones</th>
            </tr>
            {% for key, info in db.llaves.items() %}
            <tr>
                <td>
                    <form action="/editar/{{ key }}" method="post" style="display:flex; gap:5px;">
                        <input type="text" name="nuevo_nombre" value="{{ info.cliente }}" style="padding: 5px; border: 1px solid #ccc; width: 150px;">
                        <button class="btn btn-edit">OK</button>
                    </form>
                </td>
                <td><code>{{ key }}</code></td>
                <td class="status-{{ info.estado }}">{{ info.estado.upper() }}</td>
                <td>
                    <form action="/cambiar_estado/{{ key }}" method="post" style="display:inline;">
                        <button class="btn btn-status">Bloquear/Activar</button>
                    </form>
                    <form action="/eliminar/{{ key }}" method="post" style="display:inline;">
                        <button class="btn btn-del" onclick="return confirm('¿Eliminar?')">X</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin():
    db = cargar_db_llaves()
    return render_template_string(HTML_PANEL, db=db)

@app.route('/crear', methods=['POST'])
def crear():
    nombre = request.form.get('cliente')
    nueva_key = secrets.token_hex(32)
    db = cargar_db_llaves()
    db["llaves"][nueva_key] = {"cliente": nombre, "estado": "activa", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/editar/<key>', methods=['POST'])
def editar(key):
    nuevo_nombre = request.form.get('nuevo_nombre')
    db = cargar_db_llaves()
    if key in db["llaves"]:
        db["llaves"][key]["cliente"] = nuevo_nombre
        guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/cambiar_estado/<key>', methods=['POST'])
def cambiar_estado(key):
    db = cargar_db_llaves()
    if key in db["llaves"]:
        actual = db["llaves"][key]["estado"]
        db["llaves"][key]["estado"] = "bloqueada" if actual == "activa" else "activa"
        guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/eliminar/<key>', methods=['POST'])
def eliminar(key):
    db = cargar_db_llaves()
    if key in db["llaves"]:
        del db["llaves"][key]
        guardar_db_llaves(db)
    return redirect('/admin')

# --- RUTA PRINCIPAL (ORIGINAL CON NOTIFICACIÓN) ---
@app.route('/')
def home():
    enviar_telegram(f"📡 *Consulta del ESP32*\n📍 IP: `{request.remote_addr}`")
    registrar_dispositivo_nuevo(request.remote_addr, request.headers.get('User-Agent'))

    if debe_enviar_binance():
        precio = get_binance_p2p()
        enviar_telegram(f"📊 *BINANCE P2P*\n\n💵 Precio: `{precio} VES`")
        actualizar_hora_envio()

    if request.headers.get('x-dolarvzla-key') != API_KEY_VALIDA:
        return Response('{"error": "No autorizado"}', status=401, mimetype='application/json')

    data = get_bcv_data()
    return Response(json.dumps(data), mimetype='application/json') if data else Response('{"error": "Error"}', status=500, mimetype='application/json')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
