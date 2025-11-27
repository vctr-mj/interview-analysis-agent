import gspread
from google.oauth2.service_account import Credentials
import os

# Credenciales de Google Sheets (rutas leídas desde .env)
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

def setup_gspread_client(worksheet_name):
    """Configura la conexión y retorna la hoja de trabajo."""
    print("Conectando con Google Sheets...")
    
    if not SPREADSHEET_ID or not GOOGLE_SHEETS_CREDENTIALS_FILE:
        print("❌ Error: Variables de Google Sheets no configuradas en .env.")
        return None

    try:
        # Carga las credenciales y autoriza
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(worksheet_name)
    except Exception as e:
        print(f"❌ Error de conexión a Google Sheets: {e}")
        return None

def store_data_in_sheet(worksheet, data_json):
    """Añade la data estructurada a la hoja."""
    
    # Formatea el resumen de preguntas y respuestas
    qa_summary = ""
    for item in data_json.get('preguntas_respuestas', []):
        qa_summary += f"P: {item['pregunta']}\nR: {item['respuesta_resumen']}\n\n"
        
    # Define la fila de datos
    row_data = [
        data_json.get("nombre_archivo", ""),
        data_json.get("fecha_analisis", ""),
        data_json.get("puesto", ""),
        data_json.get("empresa", ""),
        data_json.get("salario_rango", ""),
        data_json.get("beneficios_clave", ""),
        qa_summary.strip()
    ]
    
    try:
        # Comprueba si la primera fila está vacía y agrega encabezados
        if not worksheet.row_values(1):
            headers = ["Archivo", "Fecha Análisis", "Puesto", "Empresa", "Salario/Rango", "Beneficios Clave", "Resumen P/R"]
            worksheet.append_row(headers)
            print("Encabezados de Google Sheets creados.")

        worksheet.append_row(row_data)
        print(f"✅ Datos de {data_json['nombre_archivo']} guardados exitosamente.")
        return True
    except Exception as e:
        print(f"❌ Error al guardar datos en Google Sheets: {e}")
        return False