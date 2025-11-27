import json
import datetime
from openai import OpenAI
import os

# Inicializar cliente OpenAI (automáticamente usa la clave OPENAI_API_KEY)
client = OpenAI() 

def transcribe_video_audio(file_path):
    """Convierte el archivo de video/audio a texto usando Whisper."""
    try:
        # Nota: Asume que el archivo es directamente aceptado o ya es audio (mp3/wav)
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                response_format="text"
            )
            return transcript
    except Exception as e:
        print(f"❌ Error en la transcripción de {os.path.basename(file_path)}: {e}")
        return None

def analyze_transcript(transcript, video_filename):
    """Utiliza GPT-4o para extraer y estructurar la información clave en JSON."""
    print("-> Analizando transcripción con GPT-4o...")
    
    # Definición estricta del prompt y del formato JSON
    system_prompt = f"""
    Eres un Agente Analista de Entrevistas. Extrae los datos y devuelve ÚNICAMENTE un objeto JSON, sin texto adicional.
    
    Esquema JSON Requerido:
    {{
        "nombre_archivo": "{video_filename}",
        "fecha_analisis": "{datetime.date.today().isoformat()}",
        "puesto": "Título del puesto.",
        "empresa": "Nombre de la empresa.",
        "salario_rango": "Salario, rango salarial, o 'No mencionado'.",
        "beneficios_clave": "3 beneficios clave mencionados.",
        "preguntas_respuestas": [
            {{
                "pregunta": "Pregunta clave del reclutador.",
                "respuesta_resumen": "Resumen conciso de la respuesta del candidato (máx. 3 oraciones)."
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analiza la siguiente transcripción: \n\n{transcript}"}
            ],
            response_format={"type": "json_object"}
        )
        
        json_output = response.choices[0].message.content
        return json.loads(json_output)
        
    except Exception as e:
        print(f"❌ Error en el análisis de LLM: {e}")
        return None