import base64
import os
import socket
from flask import Flask, render_template_string, request
import gspread
import requests
import urllib3

# Silenciar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)


def parse_numero(val):
    """Convierte texto numérico con comas (ej. '360,00') a float o int limpio."""
    if isinstance(val, (int, float)):
        return val
    if not val:
        return 0
    val_clean = str(val).replace(".", "").replace(",", ".")
    try:
        f = float(val_clean)
        return int(f) if f.is_integer() else f
    except ValueError:
        return val


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Subir Factura</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: sans-serif; padding: 20px; background-color: #f4f6f8; margin: 0; }
    .card { background: white; padding: 25px; border-radius: 12px; max-width: 400px; margin: 20px auto; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .custom-file-upload { display: inline-block; padding: 14px; color: #fff; background-color: #007bff; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; }
    input[type="file"] { display: none; }
    button { width: 100%; padding: 14px; background-color: #28a745; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; margin-top: 15px; cursor: pointer; }
    button:disabled { background-color: #ccc; }
    #fileName { margin-top: 10px; font-size: 13px; color: #555; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Escanear Factura</h2>
    <form action="/procesar" method="post" enctype="multipart/form-data" onsubmit="deshabilitarBoton()">
      <label for="foto" class="custom-file-upload">📸 Tomar / Seleccionar Foto</label>
      <input type="file" id="foto" name="foto" accept="image/*" capture="environment" required onchange="mostrarNombre()">
      <div id="fileName"></div>
      <button type="submit" id="btnSubmit">Subir y Registrar</button>
    </form>
  </div>
  <script>
    function mostrarNombre() {
      const input = document.getElementById('foto');
      if (input.files.length > 0) {
        document.getElementById('fileName').innerText = "Archivo: " + input.files[0].name;
      }
    }
    function deshabilitarBoton() {
      const btn = document.getElementById('btnSubmit');
      btn.disabled = true;
      btn.innerText = "Procesando...";
    }
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/procesar", methods=["POST"])
def procesar():
    if "foto" not in request.files:
        return "No se envió ninguna imagen.", 400

    file = request.files["foto"]
    if file.filename == "":
        return "No se seleccionó ningún archivo.", 400

    try:
        # 1. Leer y codificar la imagen
        encoded_string = base64.b64encode(file.read()).decode("utf-8")

        payload = {
            "filename": file.filename,
            "image_base64": encoded_string,
        }

        # 2. Webhook de Producción HTTP
        url_webhook = (
            "http://sitecdesarrollo.172.10.219.15.sslip.io/webhook/factura/datos"
        )

        session = requests.Session()
        session.trust_env = False

        response = session.post(
            url_webhook,
            json=payload,
            verify=False,
            headers={"Connection": "close"},
        )

        print(f"Estado de la respuesta: {response.status_code}")

        if response.status_code == 200:
            datos_factura = response.json()
            print("Datos extraídos:", datos_factura)

            # 3. Conexión con Google Sheets
            ruta_credenciales = os.path.join(
                os.path.dirname(__file__), "credentials.json"
            )
            gc = gspread.service_account(filename=ruta_credenciales)
            sh = gc.open("Emisor Facturas")
            worksheet = sh.sheet1

            # 4. Mapeo adaptable de campos devueltos
            nueva_fila = [
                datos_factura.get("Fecha de Solicitud", ""),
                datos_factura.get("Solicitante", ""),
                datos_factura.get("Parqueadero", ""),
                datos_factura.get(
                    "Nombre del cliente o Razón social",
                    datos_factura.get("Nombre del Cliente o Razón Social", ""),
                ),
                str(datos_factura.get("RUC o CI", "")),
                parse_numero(datos_factura.get("Cantidad", 0)),
                datos_factura.get(
                    "Descripcion",
                    datos_factura.get("Descripción del Producto/Servicio", ""),
                ),
                parse_numero(datos_factura.get("Subtotal", 0)),
                parse_numero(datos_factura.get("% IVA", 0)),
                parse_numero(datos_factura.get("Total", 0)),
                datos_factura.get("Forma de Pago", ""),
            ]

            # 5. Insertar la fila en Google Sheets
            worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
            print("Fila agregada exitosamente a Google Sheets.")

            return """
            <div style="font-family: sans-serif; text-align: center; padding: 40px;">
                <h1 style="color: #28a745;">✅ ¡Factura procesada con éxito!</h1>
                <a href="/" style="display: inline-block; margin-top: 20px; text-decoration: none; background: #007bff; color: white; padding: 10px 20px; border-radius: 5px;">Procesar otra factura</a>
            </div>
            """
        else:
            return f"Error devuelto por el servidor n8n: {response.text}", 500

    except Exception as e:
        print(f"Ocurrió un error en la ejecución: {e}")
        return f"Ocurrió un error en la ejecución: {e}", 500


def obtener_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    ip_local = obtener_ip_local()
    puerto = 5000
    print("\n" + "=" * 50)
    print("🚀 Servidor Iniciado")
    print(f"📱 Abre en el navegador de tu celular: http://{ip_local}:{puerto}")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=puerto, debug=True)