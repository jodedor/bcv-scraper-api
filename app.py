import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    url = "https://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Nota: verify=False ayuda si el BCV tiene problemas con su certificado SSL
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscamos los valores del BCV
            dolar = soup.find(id="dolar").find('strong').text.strip().replace(',', '.')
            euro = soup.find(id="euro").find('strong').text.strip().replace(',', '.')
            
            # Buscamos la fecha
            fecha_element = soup.find('span', class_='date-display-single')
            fecha = fecha_element.text.strip() if fecha_element else "No disponible"

            return jsonify({
                "status": "success",
                "dolar": float(dolar),
                "euro": float(euro),
                "fecha": fecha
            })
        else:
            return jsonify({"status": "error", "message": f"BCV status {response.status_code}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Render asigna un puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
