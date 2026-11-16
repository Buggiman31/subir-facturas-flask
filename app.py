import base64
import json
import os
from flask import Flask, render_template_string, request
import gspread

app = Flask(__name__)

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
        # 1. Cargar credenciales desde la variable de entorno de Render
        credenciales_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not credenciales_json:
            return "Error: La variable de entorno GOOGLE_CREDENTIALS_JSON no está configurada en Render.", 500

        creds_dict = json.loads(credenciales_json)
        gc = gspread.service_account_from_dict(creds_dict)
        
        sh = gc.open("Emisor Facturas")
        worksheet = sh.sheet1

        # 2. Datos de prueba para registrar en Google Sheets
        nueva_fila = [
            "2026-11-16",
            "Usuario Celular",
            "Parqueadero Principal",
            "Cliente General",
            "0999999999001",
            1,
            file.filename,
            0,
            15,
            0,
            "Efectivo"
        ]

        worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")

        return """
        <div style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h1 style="color: #28a745;">✅ ¡Factura procesada con éxito!</h1>
            <p>Los datos se han guardado correctamente en tu Google Sheets.</p>
            <a href="/" style="display: inline-block; margin-top: 20px; text-decoration: none; background: #007bff; color: white; padding: 10px 20px; border-radius: 5px;">Procesar otra factura</a>
        </div>
        """

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return f"Ocurrió un error en la ejecución: {e}", 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=False)
