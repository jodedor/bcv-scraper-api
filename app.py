import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request, render_template_string, redirect
import json
import os
import time
import secrets
from datetime import datetime
from collections import OrderedDict
from apscheduler.schedulers.background import BackgroundScheduler
app = Flask(__name__)
# --- FUNCIÓN CRON-JOB: CIERRE MENSUAL ---
def ejecutar_cierre_mensual():
    url_cron = "https://chamba.rf.gd/cron/cron_cierre_mensual.php?key=M1Cl4v3S3cr3t4Mag4tr0n1c2026"
    print(f"⏰ [CRON SYSTEM] Iniciando petición de cierre mensual a: {url_cron}")
    try:
        # Hacemos la petición HTTP externa
        respuesta = requests.get(url_cron, timeout=30, verify=False)
        
        # Registramos el resultado en la consola de Render y enviamos reporte a tu Telegram
        if respuesta.status_code == 200:
            print("✅ [CRON SYSTEM] Cierre mensual ejecutado con éxito en InfinityFree.")
            enviar_telegram("📆 *SISTEMA CRON*:\nEl cierre mensual se ejecutó exitosamente en InfinityFree. 🎉")
        else:
            print(f"⚠️ [CRON SYSTEM] El servidor remoto respondió con código: {respuesta.status_code}")
            enviar_telegram(f"⚠️ *SISTEMA CRON*:\nInfinityFree respondió con código `{respuesta.status_code}` al intentar el cierre mensual.")
            
    except Exception as e:
        print(f"❌ [CRON SYSTEM] Error al conectar con InfinityFree: {e}")
        enviar_telegram(f"🚨 *SISTEMA CRON*:\nError crítico al ejecutar el cierre mensual:\n`{str(e)}`")
# --- CONFIGURACIÓN ---
PATH_DISCO = "/data/bcv_data.json"
PATH_CONOCIDOS = "/data/conocidos.json"
PATH_ULTIMO_ENVIO = "/data/ultimo_envio.txt"
PATH_DB_LLAVES = "/data/db_llaves.json"
PATH_CONFIG = "/data/config_sistema.json" # <--- NUEVO

TELEGRAM_TOKEN = "8097155705:AAECM-VdtI98giBr1Vl2WZ6ynNKHMTkfxPw"
TELEGRAM_CHAT_ID = "-5248292296"
INTERVALO_BINANCE_MINUTOS = 90

# --- GESTIÓN DEL MODO EMERGENCIA ---
def gestionar_emergencia(accion="leer"):
    if not os.path.exists(PATH_CONFIG):
        config = {"modo_emergencia": False}
        with open(PATH_CONFIG, "w") as f: json.dump(config, f)
    with open(PATH_CONFIG, "r") as f:
        try: config = json.load(f)
        except: config = {"modo_emergencia": False}
    if accion == "toggle":
        config["modo_emergencia"] = not config.get("modo_emergencia", False)
        with open(PATH_CONFIG, "w") as f: json.dump(config, f)
        estado = "ACTIVADO 🚨" if config["modo_emergencia"] else "DESACTIVADO ✅"
        enviar_telegram(f"SISTEMA: Modo Emergencia {estado}")
    return config.get("modo_emergencia", False)

# --- FUNCIONES DE GESTIÓN DE LLAVES (ORIGINALES) ---
def cargar_db_llaves():
    if not os.path.exists(PATH_DB_LLAVES):
        db = {"llaves": {}}
    else:
        try:
            with open(PATH_DB_LLAVES, "r") as f: db = json.load(f)
        except: db = {"llaves": {}}
    maestra = "ebb828bc705a3da8954f60aaf0c594fe3300fe1cdb57f9b03d8eec176889b802"
    if maestra not in db["llaves"]:
        db["llaves"][maestra] = {"cliente": "SISTEMA (LLAVE MAESTRA)", "estado": "activa", "fecha": "2026-01-01 00:00:00"}
        guardar_db_llaves(db)
    return db

def guardar_db_llaves(db):
    with open(PATH_DB_LLAVES, "w") as f: json.dump(db, f, indent=4)

# --- FUNCIONES AUXILIARES (ORIGINALES) ---
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'}, timeout=5)
    except Exception as e: print(f"Error Telegram: {e}")

def get_binance_p2p():
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"asset": "USDT", "fiat": "VES", "merchantCheck": False, "page": 1, "rows": 1, "tradeType": "BUY", "transAmount": "500"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        datos = r.json()
        if datos.get('success') and len(datos['data']) > 0: return datos['data'][0]['adv']['price']
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
    return {"usd_actual": 361.4906, "eur_actual": 432.7151, "fecha_actual": "2026-01-28", "usd_previo": 361.4906, "eur_previo": 432.7151, "fecha_previa": "2026-01-28", "timestamp": 0}

def get_bcv_data():
    datos_viejos = leer_datos_disco()
    
    # --- LÓGICA DE EMERGENCIA ---
    if gestionar_emergencia("leer"):
        print("🚨 EMERGENCIA: Entregando datos de disco.")
        return OrderedDict([
            ("current", {"usd": datos_viejos["usd_actual"], "eur": datos_viejos["eur_actual"], "date": datos_viejos["fecha_actual"]}),
            ("previous", {"usd": datos_viejos["usd_previo"], "eur": datos_viejos["eur_previo"], "date": datos_viejos["fecha_previa"]}),
            ("changePercentage", {"usd": 0.0, "eur": 0.0})
        ])

    # --- LÓGICA DE CACHÉ ---
    tiempo_actual = time.time()
    ultimo_timestamp = datos_viejos.get("timestamp", 0)
    if (tiempo_actual - ultimo_timestamp) < 3600:
        u_act, u_prev = datos_viejos["usd_actual"], datos_viejos["usd_previo"]
        e_act, e_prev = datos_viejos["eur_actual"], datos_viejos["eur_previo"]
        return OrderedDict([
            ("current", {"usd": u_act, "eur": e_act, "date": datos_viejos["fecha_actual"]}),
            ("previous", {"usd": u_prev, "eur": e_prev, "date": datos_viejos["fecha_previa"]}),
            ("changePercentage", {
                "usd": round(((u_act - u_prev) / u_prev * 100), 4) if u_prev != 0 else 0,
                "eur": round(((e_act - e_prev) / e_prev * 100), 4) if e_prev != 0 else 0
            })
        ])
    
    # --- SCRAPING ACTUALIZADO AL NUEVO HTML ---
    url = "https://www.bcv.org.ve/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Captura de USD y EUR usando los IDs específicos
            dolar_container = soup.find(id="dolar")
            dolar_actual = float(dolar_container.find('strong').text.strip().replace(',', '.'))
            
            euro_container = soup.find(id="euro")
            euro_actual = float(euro_container.find('strong').text.strip().replace(',', '.'))
            
            # Captura de fecha desde el atributo 'content' (ISO: 2026-03-10)
            fecha_tag = soup.find("span", class_="date-display-single")
            if fecha_tag and fecha_tag.has_attr('content'):
                fecha_sitio = fecha_tag['content'].split('T')[0]
            else:
                fecha_sitio = time.strftime("%Y-%m-%d")

            # Solo actualizamos si la fecha es nueva para evitar rotación incorrecta
            if fecha_sitio > datos_viejos.get("fecha_actual", ""):
                datos_finales = {
                    "usd_actual": dolar_actual, 
                    "eur_actual": euro_actual, 
                    "fecha_actual": fecha_sitio, 
                    "usd_previo": datos_viejos.get("usd_actual"), 
                    "eur_previo": datos_viejos.get("eur_actual"), 
                    "fecha_previa": datos_viejos.get("fecha_actual"),
                    "timestamp": time.time()
                }
                with open(PATH_DISCO, 'w') as f: json.dump(datos_finales, f)
            else:
                datos_finales = datos_viejos

            u_act, u_ant = datos_finales["usd_actual"], datos_finales["usd_previo"]
            e_act, e_ant = datos_finales["eur_actual"], datos_finales["eur_previo"]
            
            # Mantenemos el OrderedDict exacto para el ESP32
            return OrderedDict([
                ("current", {"usd": u_act, "eur": e_act, "date": datos_finales["fecha_actual"]}),
                ("previous", {"usd": u_ant, "eur": e_ant, "date": datos_finales["fecha_previa"]}),
                ("changePercentage", {
                    "usd": round(((u_act - u_ant) / u_ant * 100), 4) if u_ant != 0 else 0,
                    "eur": round(((e_act - e_ant) / e_ant * 100), 4) if e_ant != 0 else 0
                })
            ])
    except Exception as e:
        print(f"Error en Scraping: {e}")
        return None
# --- PANEL ADMINISTRATIVO INTEGRAL ---
HTML_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <title>Panel Control Letreros</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 1300px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header-area { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .emergencia-box { padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; border: 2px solid; }
        .modo-on { background: #fff3f3; border-color: #dc3545; color: #dc3545; }
        .modo-off { background: #f3fff3; border-color: #28a745; color: #28a745; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #007bff; color: white; }
        .btn { padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; color: white; text-decoration: none; font-size: 13px; }
        .btn-panic { background: #dc3545; font-size: 16px; font-weight: bold; }
        .btn-ok-emerg { background: #28a745; font-size: 16px; font-weight: bold; }
        .btn-add { background: #28a745; padding: 10px 20px; }
        .btn-status { background: #ffc107; color: black; }
        .btn-copy { background: #6c757d; font-size: 11px; }
        .btn-backup { background: #343a40; }
        .btn-clear-cache { background: #fd7e14; font-weight: bold; } /* === NUEVO === */
        .btn-import { background: #6f42c1; }
        code { background: #f8f9fa; padding: 4px; border-radius: 4px; color: #e83e8c; border: 1px solid #ddd; }
        .copy-notif { font-size: 10px; color: #28a745; display: none; }
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
            <h2 style="margin:0;">🛠️ Gestión de API Keys e Infraestructura</h2>
            <div style="display: flex; gap: 10px;">
                <form action="/importar_backup" method="post" enctype="multipart/form-data" style="display:flex; align-items:center; gap:5px; background:#eee; padding:5px; border-radius:5px;">
                    <input type="file" name="archivo_json" accept=".json" required style="font-size:10px;">
                    <button type="submit" class="btn btn-import">📥 Importar</button>
                </form>
                <a href="/descargar_backup" class="btn btn-backup">💾 Backup</a>
            </div>
        </div>

        <div class="emergencia-box {{ 'modo-on' if emergencia else 'modo-off' }}">
            <div>
                <h3 style="margin:0;">🚨 MODO DE EMERGENCIA (BCV CAÍDO)</h3>
                <p style="margin:5px 0 0 0;">Estado: <strong>{{ 'ACTIVADO' if emergencia else 'DESACTIVADO' }}</strong></p>
            </div>
            <form action="/toggle_emergencia" method="post">
                <button type="submit" class="btn {{ 'btn-ok-emerg' if emergencia else 'btn-panic' }}">
                    {{ '✅ NORMALIZAR' if emergencia else '🔥 ACTIVAR EMERGENCIA' }}
                </button>
            </form>
        </div>

        <!-- === NUEVO: BOX LIMPIAR CACHÉ BCV === -->
        <div class="emergencia-box modo-off" style="margin-bottom: 20px;">
            <div>
                <h3 style="margin:0;">🧹 LIMPIAR CACHÉ BCV</h3>
                <p style="margin:5px 0 0 0;">Fuerza una nueva consulta al Banco Central en el próximo request</p>
            </div>
            <form action="/admin/clear-bcv-cache" method="post" onsubmit="return confirm('¿Borrar caché del BCV? El próximo request hará scraping nuevo.')">
                <button type="submit" class="btn btn-clear-cache">🔄 Forzar Actualización</button>
            </form>
        </div>
        <!-- === FIN NUEVO === -->

        <form action="/crear" method="post" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <strong>Nuevo Cliente:</strong> 
            <input type="text" name="cliente" placeholder="Nombre" required style="width:250px;">
            <button type="submit" class="btn btn-add">Generar Clave</button>
        </form>

        <table>
            <thead><tr><th>Cliente</th><th>API Key</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>
                {% for key, info in db.llaves.items() %}
                <tr>
                    <td>
                        <form action="/editar/{{ key }}" method="post" style="display:flex; gap:5px;">
                            <input type="text" name="nuevo_nombre" value="{{ info.cliente }}" style="width:120px;">
                            <button class="btn" style="background:#17a2b8;">OK</button>
                        </form>
                    </td>
                    <td>
                        <code>{{ key[:15] }}...</code>
                        <button class="btn btn-copy" onclick="copiarAlPortapapeles('{{ key }}', '{{ loop.index }}')">Copiar</button>
                        <span id="aviso-{{ loop.index }}" class="copy-notif">¡Listo!</span>
                    </td>
                    <td style="color: {{ 'green' if info.estado == 'activa' else 'red' }}; font-weight:bold;">{{ info.estado.upper() }}</td>
                    <td>
                        <form action="/cambiar_estado/{{ key }}" method="post" style="display:inline;"><button class="btn btn-status">Status</button></form>
                        <form action="/eliminar/{{ key }}" method="post" style="display:inline;"><button class="btn" style="background:#dc3545;" onclick="return confirm('¿Eliminar?')">X</button></form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# --- RUTAS DE CONTROL (ORIGINALES + NUEVAS) ---
@app.route('/admin')
def admin():
    db = cargar_db_llaves()
    emergencia = gestionar_emergencia("leer")
    return render_template_string(HTML_PANEL, db=db, emergencia=emergencia)

@app.route('/toggle_emergencia', methods=['POST'])
def toggle_emergencia():
    gestionar_emergencia("toggle")
    return redirect('/admin')

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
    nuevo = request.form.get('nuevo_nombre')
    db = cargar_db_llaves()
    if key in db["llaves"]:
        db["llaves"][key]["cliente"] = nuevo
        guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/cambiar_estado/<key>', methods=['POST'])
def cambiar_estado(key):
    db = cargar_db_llaves()
    if key in db["llaves"]:
        db["llaves"][key]["estado"] = "bloqueada" if db["llaves"][key]["estado"] == "activa" else "activa"
        guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/eliminar/<key>', methods=['POST'])
def eliminar(key):
    db = cargar_db_llaves()
    if key in db["llaves"]:
        del db["llaves"][key]
        guardar_db_llaves(db)
    return redirect('/admin')

@app.route('/descargar_backup')
def descargar_backup():
    db = cargar_db_llaves()
    return Response(json.dumps(db, indent=4), mimetype='application/json', headers={"Content-disposition": "attachment; filename=backup_llaves.json"})

@app.route('/importar_backup', methods=['POST'])
def importar_backup():
    if 'archivo_json' in request.files:
        archivo = request.files['archivo_json']
        if archivo:
            try:
                contenido = json.load(archivo)
                if "llaves" in contenido: guardar_db_llaves(contenido)
            except: pass
    return redirect('/admin')

# --- NUEVA RUTA: Limpiar caché BCV ---
@app.route('/admin/clear-bcv-cache', methods=['POST'])
def clear_bcv_cache():
    """Elimina el archivo de caché del BCV para forzar nuevo scraping"""
    try:
        if os.path.exists(PATH_DISCO):
            os.remove(PATH_DISCO)
            mensaje = "✅ Caché BCV eliminado. Próximo request hará scraping fresco."
            enviar_telegram(f"🧹 *Cache Limpiado*\n👤: Admin\n📦 Archivo: `bcv_data.json`")
        else:
            mensaje = "ℹ️ El archivo de caché no existía."
        return redirect('/admin?msg=' + mensaje)
    except Exception as e:
        error_msg = f"❌ Error al borrar caché: {str(e)}"
        enviar_telegram(f"⚠️ *Error Admin*\n{error_msg}")
        return redirect('/admin?msg=' + error_msg)

# --- RUTA PRINCIPAL ---
@app.route('/')
def home():
    api_key_recibida = request.headers.get('x-dolarvzla-key')
    db = cargar_db_llaves()
    if api_key_recibida not in db["llaves"] or db["llaves"][api_key_recibida]["estado"] != "activa":
        return Response('{"error": "No autorizado"}', status=401, mimetype='application/json')

    nombre_cliente = db["llaves"][api_key_recibida]["cliente"]
    enviar_telegram(f"📡 *Consulta*\n👤: `{nombre_cliente}`\n📍 IP: `{request.remote_addr}`")
    registrar_dispositivo_nuevo(request.remote_addr, request.headers.get('User-Agent'))

    if debe_enviar_binance():
        precio = get_binance_p2p()
        enviar_telegram(f"📊 *BINANCE P2P*\n\n💵 Precio: `{precio} VES`")
        actualizar_hora_envio()

    data = get_bcv_data()
    return Response(json.dumps(data), mimetype='application/json') if data else Response('{"error": "Error"}', status=500, mimetype='application/json')
# --- CONFIGURACIÓN Y ARRANQUE DEL PLANIFICADOR (CRON) ---
scheduler = BackgroundScheduler(timezone="America/Caracas")

# Se programa para el día 1 de cada mes a las 05:00 AM hora de Venezuela
scheduler.add_job(ejecutar_cierre_mensual, 'cron', day=4, hour=8, minute=0)

# Arranca el planificador en segundo plano
scheduler.start()
print("📆 [CRON SYSTEM] Planificador iniciado. Próximo cierre: El día 1 del mes a las 05:00 AM (Hora Vzla).")
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
