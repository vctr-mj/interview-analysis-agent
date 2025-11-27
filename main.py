import os
from dotenv import load_dotenv
from sheets_utils import setup_gspread_client, store_data_in_sheet
from ai_processor import transcribe_video_audio, analyze_transcript

# Cargar variables de entorno del archivo .env
load_dotenv()

# --- CONFIGURACIÓN DESDE .ENV ---
# La ruta de la carpeta de entrevistas se lee de las variables de entorno
INTERVIEWS_FOLDER = os.getenv("INTERVIEWS_FOLDER")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")

def process_interviews():
    """Función principal que recorre la carpeta, procesa cada video y almacena."""
    
    if not INTERVIEWS_FOLDER or not os.path.exists(INTERVIEWS_FOLDER):
        print("❌ Error: La carpeta de entrevistas no está configurada o no existe.")
        print(f"Ruta configurada: {INTERVIEWS_FOLDER}")
        return

    print("--- INICIO DEL PROCESO DE ANÁLISIS DE ENTREVISTAS ---")
    
    # Conexión a Google Sheets
    worksheet = setup_gspread_client(WORKSHEET_NAME)
    if not worksheet:
        return
    
    # 1. Recorrer la carpeta
    for filename in os.listdir(INTERVIEWS_FOLDER):
        if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mp3')):
            video_path = os.path.join(INTERVIEWS_FOLDER, filename)
            
            print(f"\n[INICIANDO PROCESO: {filename}]")
            
            # 2. Transcribir
            transcript = transcribe_video_audio(video_path)
            if not transcript:
                continue

            # 3. Analizar
            analysis_data = analyze_transcript(transcript, filename)
            if not analysis_data:
                continue
                
            # 4. Almacenar
            store_data_in_sheet(worksheet, analysis_data)

    print("\n--- PROCESO COMPLETADO ---")

if __name__ == "__main__":
    process_interviews()