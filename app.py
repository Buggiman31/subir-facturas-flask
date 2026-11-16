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

        # Nota: Aquí puedes integrar tu lógica de procesamiento o llamada interna si lo deseas, 
        # o registrar directamente los datos en Google Sheets.
        
        # 2. Conexión con Google Sheets
        ruta_credenciales = os.path.join(
            os.path.dirname(__file__), "credentials.json"
        )
        gc = gspread.service_account(filename=ruta_credenciales)
        sh = gc.open("Emisor Facturas")
        worksheet = sh.sheet1

        # 3. Datos de ejemplo o extraídos de la factura
        nueva_fila = [
            "2026-11-16",           # Fecha de Solicitud
            "Usuario Celular",      # Solicitante
            "Parqueadero Principal",# Parqueadero
            "Cliente General",      # Razón social
            "0999999999001",        # RUC o CI
            1,                      # Cantidad
            file.filename,          # Descripción
            0,                      # Subtotal
            15,                     # % IVA
            0,                      # Total
            "Efectivo"              # Forma de Pago
        ]

        # 4. Insertar la fila en Google Sheets
        worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
        print("Fila agregada exitosamente a Google Sheets.")

        return """
        <div style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h1 style="color: #28a745;">✅ ¡Factura procesada con éxito!</h1>
            <p>Los datos se han guardado correctamente en tu Google Sheets.</p>
            <a href="/" style="display: inline-block; margin-top: 20px; text-decoration: none; background: #007bff; color: white; padding: 10px 20px; border-radius: 5px;">Procesar otra factura</a>
        </div>
        """

    except Exception as e:
        print(f"Ocurrió un error en la ejecución: {e}")
        return f"Ocurrió un error en la ejecución: {e}", 500


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=False)
