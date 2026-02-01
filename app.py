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

# --- CONFIGURACIÓN ---
PATH_DISCO = "/data/bcv_data.json"
PATH_CONOCIDOS = "/data/conocidos.json"
PATH_ULTIMO_ENVIO = "/data/ultimo_envio.txt"
PATH_DB_LLAVES = "/data/db_llaves.json"

TELEGRAM_TOKEN = "8097155705:AAECM-VdtI98giBr1Vl2WZ6ynNKHMTkfxPw"
TELEGRAM_CHAT_ID = "-5248292296"
INTERVALO_BINANCE_MINUTOS = 90

# --- FUNCIONES DE GESTIÓN DE LLAVES ---

def cargar_db_llaves():
    # Si no existe, creamos la estructura base
    if not os.path.exists(PATH_DB_LLAVES):
        db = {"llaves": {}}
    else:
        try:
            with open(PATH_DB_LLAVES, "r") as f:
                db = json.load(f)
        except:
            db = {"llaves": {}}
    
    # AUTO-INYECCIÓN DE LLAVE MAESTRA (Asegura que siempre aparezca en el panel)
    maestra = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"
    if maestra not in db["llaves"]:
        db["llaves"][maestra] = {
            "cliente": "SISTEMA (LLAVE MAESTRA)",
            "estado": "activa",
            "fecha": "2026-01-01 00:00:00"
        }
        with open(PATH_DB_LLAVES, "w") as f:
            json.dump(db, f, indent=4)
            
    return db

def guardar_db_llaves(db):
    with open(PATH_DB_LLAVES, "w") as f:
        json.dump(db, f, indent=4)

# --- FUNCIONES ORIGINALES (BCV Y TELEGRAM) ---

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

# --- PANEL ADMINISTRATIVO CON BOTÓN DE COPIAR ---

HTML_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <title>Panel Control Letreros</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 1300px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        .header-area { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .header-actions { display: flex; gap: 10px; align-items: center; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: auto; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #007bff; color: white; white-space: nowrap; }
        
        .col-key { width: 50%; }
        
        .btn { padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; color: white; text-decoration: none; font-size: 13px; font-family: sans-serif; }
        .btn-add { background: #28a745; padding: 10px 20px; font-size: 15px; }
        .btn-edit { background: #17a2b8; }
        .btn-status { background: #ffc107; color: black; }
        .btn-del { background: #dc3545; }
        .btn-copy { background: #6c757d; margin-left: 5px; font-size: 11px; }
        .btn-backup { background: #343a40; }
        .btn-import { background: #6f42c1; } /* Color morado para diferenciar */
        
        code { 
            background: #f8f9fa; 
            padding: 5px 8px; 
            border-radius: 4px; 
            font-size: 13px; 
            color: #e83e8c; 
            font-family: 'Courier New', monospace;
            border: 1px solid #ddd;
        }
        
        .status-activa { color: green; font-weight: bold; }
        .status-bloqueada { color: red; font-weight: bold; }
        input[type="text"] { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        
        .copy-notif { font-size: 10px; color: #28a745; display: none; margin-left: 5px; }
        
        /* Estilo para el input de archivo oculto */
        .import-form { display: inline-flex; align-items: center; gap: 5px; background: #f1f1f1; padding: 5px; border-radius: 4px; border: 1px dashed #ccc; }
    </style>
    <script>
        function copiarAlPortapapeles(texto, btnId) {
            navigator.clipboard.writeText(texto).then(function() {
                var aviso = document.getElementById('aviso-' + btnId);
                aviso.style.display = 'inline';
                setTimeout(function() { aviso.style.display = 'none'; }, 2000);
            });
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header-area">
            <h2 style="margin:0;">🛠️ Gestión de API Keys para Letreros</h2>
            <div class="header-actions">
                <form action="/importar_backup" method="post" enctype="multipart/form-data" class="import-form">
                    <input type="file" name="archivo_json" accept=".json" required style="font-size: 11px; width: 150px;">
                    <button type="submit" class="btn btn-import">📥 Importar</button>
                </form>
                <a href="/descargar_backup" class="btn btn-backup">💾 Descargar Backup</a>
            </div>
        </div>

        <form action="/crear" method="post" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <strong>Nuevo Cliente:</strong> 
            <input type="text" name="cliente" placeholder="Nombre o Ubicación" required style="width: 300px;">
            <button type="submit" class="btn btn-add">Generar Nueva Clave</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>Cliente</th>
                    <th class="col-key">API Key (SHA-256)</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                {% for key, info in db.llaves.items() %}
                <tr>
                    <td>
                        <form action="/editar/{{ key }}" method="post" style="display:flex; gap:5px;">
                            <input type="text" name="nuevo_nombre" value="{{ info.cliente }}" style="width: 140px;">
                            <button class="btn btn-edit">OK</button>
                        </form>
                    </td>
                    <td class="col-key">
                        <code>{{ key }}</code>
                        <button class="btn btn-copy" onclick="copiarAlPortapapeles('{{ key }}', '{{ loop.index }}')">Copiar</button>
                        <span id="aviso-{{ loop.index }}" class="copy-notif">¡Copiado!</span>
                    </td>
                    <td class="status-{{ info.estado }}">{{ info.estado.upper() }}</td>
                    <td style="white-space: nowrap;">
                        <form action="/cambiar_estado/{{ key }}" method="post" style="display:inline;">
                            <button class="btn btn-status">Bloquear/Activar</button>
                        </form>
                        <form action="/eliminar/{{ key }}" method="post" style="display:inline;">
                            <button class="btn btn-del" onclick="return confirm('¿Eliminar?')">X</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
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

# --- RUTA PRINCIPAL (CON VALIDACIÓN DINÁMICA) ---

@app.route('/')
def home():
    # Extraer la llave que envía el ESP32
    api_key_recibida = request.headers.get('x-dolarvzla-key')
    
    # Cargar base de datos de llaves
    db = cargar_db_llaves()
    
    # VALIDACIÓN DINÁMICA:
    # 1. ¿La llave existe en nuestro JSON?
    # 2. ¿Su estado es 'activa'?
    if api_key_recibida not in db["llaves"] or db["llaves"][api_key_recibida]["estado"] != "activa":
        print(f"🚫 Acceso Denegado: {api_key_recibida} | IP: {request.remote_addr}")
        return Response('{"error": "No autorizado o llave bloqueada"}', status=401, mimetype='application/json')

    # Si pasa la validación, obtenemos el nombre para el log/telegram
    nombre_cliente = db["llaves"][api_key_recibida]["cliente"]

    # Notificaciones y registros
    enviar_telegram(f"📡 *Consulta autorizada*\n👤 Cliente: `{nombre_cliente}`\n📍 IP: `{request.remote_addr}`")
    registrar_dispositivo_nuevo(request.remote_addr, request.headers.get('User-Agent'))

    if debe_enviar_binance():
        precio = get_binance_p2p()
        enviar_telegram(f"📊 *BINANCE P2P*\n\n💵 Precio: `{precio} VES`")
        actualizar_hora_envio()

    data = get_bcv_data()
    return Response(json.dumps(data), mimetype='application/json') if data else Response('{"error": "Error"}', status=500, mimetype='application/json')

@app.route('/descargar_backup')
def descargar_backup():
    db = cargar_db_llaves()
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    nombre_archivo = f"respaldo_llaves_{fecha_str}.json"
    
    return Response(
        json.dumps(db, indent=4),
        mimetype='application/json',
        headers={"Content-disposition": f"attachment; filename={nombre_archivo}"}
    )

@app.route('/importar_backup', methods=['POST'])
def importar_backup():
    if 'archivo_json' not in request.files:
        return redirect('/admin')
    
    archivo = request.files['archivo_json']
    if archivo.filename == '':
        return redirect('/admin')

    if archivo:
        try:
            contenido = json.load(archivo)
            # Verificación básica de estructura
            if "llaves" in contenido:
                guardar_db_llaves(contenido)
        except Exception as e:
            print(f"Error al importar: {e}")
            
    return redirect('/admin')



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
