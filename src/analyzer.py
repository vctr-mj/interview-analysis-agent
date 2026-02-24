"""
Modulo de analisis de transcripciones con Gemini.
Extrae preguntas del reclutador, genera respuestas optimas y metadata.
"""

import json
import time
import datetime
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

MAX_RETRIES = 3
RETRY_BASE_DELAY = 15  # segundos, se duplica en cada reintento

SYSTEM_PROMPT = """Eres un Agente experto en analisis de entrevistas de trabajo.
Tu tarea es analizar la transcripcion de una entrevista e identificar con precision
las preguntas que el reclutador hizo al candidato.

La transcripcion incluye marcas de tiempo por segmento en formato:
[HH:MM:SS - HH:MM:SS] Texto del segmento...

Usa estas marcas de tiempo para determinar el rango de tiempo en que se hace
cada pregunta en la grabacion original.

Reglas:
- Identifica TODAS las preguntas del reclutador, no solo las principales.
- Para cada pregunta, incluye el rango de tiempo donde aparece en la grabacion.
  El rango debe cubrir desde que el reclutador empieza a formular la pregunta
  hasta que termina de hacerla (antes de que el candidato responda).
- Para cada pregunta, resume la respuesta que dio el candidato.
- Genera una "respuesta optima" profesional que el candidato podria haber dado,
  mas estructurada, concisa y con mayor impacto.
- Clasifica cada pregunta por categoria: tecnica, conductual, situacional, cultura, logistica.
- Extrae metadata general de la entrevista.
- Identifica TODA informacion relevante que el entrevistador comparta sobre la empresa,
  el puesto, el equipo, tecnologias, cultura de trabajo, beneficios, proceso de seleccion,
  clientes, dia a dia del rol, oportunidades de crecimiento, etc. Esta informacion
  aparece cuando el entrevistador describe o explica aspectos de la empresa/rol,
  no cuando hace preguntas al candidato. Cada pieza de informacion debe ser un item
  separado con su rango de tiempo. Si no hay informacion relevante, devuelve una lista vacia.

Devuelve UNICAMENTE un objeto JSON valido con este esquema exacto:

{
    "metadata": {
        "nombre_archivo": "<se proporcionara>",
        "fecha_analisis": "<se proporcionara>",
        "puesto": "Titulo del puesto discutido o 'No mencionado'",
        "empresa": "Nombre de la empresa o 'No mencionado'",
        "duracion_estimada": "Duracion estimada de la entrevista basada en el contenido",
        "tipo_entrevista": "tecnica | rrhh | mixta | filtro_inicial"
    },
    "preguntas": [
        {
            "numero": 1,
            "rango_tiempo": "HH:MM:SS - HH:MM:SS",
            "categoria": "tecnica | conductual | situacional | cultura | logistica",
            "pregunta": "La pregunta exacta o parafraseada del reclutador",
            "respuesta_candidato": "Resumen de lo que respondio el candidato (max 3 oraciones)",
            "respuesta_optima": "Una respuesta profesional, estructurada y de alto impacto (max 5 oraciones). Usa el metodo STAR si aplica.",
            "tip": "Un consejo breve para responder mejor este tipo de pregunta"
        }
    ],
    "informacion_empresa": [
        {
            "rango_tiempo": "HH:MM:SS - HH:MM:SS",
            "tema": "estructura_equipo | tecnologias_herramientas | cultura_trabajo | clientes | crecimiento_carrera | proceso_seleccion | beneficios | dia_a_dia | otro",
            "detalle": "Resumen claro y conciso de la informacion compartida por el entrevistador sobre la empresa o el rol"
        }
    ],
    "resumen": {
        "total_preguntas": 0,
        "fortalezas_candidato": ["Fortaleza 1", "Fortaleza 2"],
        "areas_mejora": ["Area 1", "Area 2"],
        "impresion_general": "Evaluacion breve del desempeno del candidato"
    }
}"""


def analyze_transcript(transcript: str, filename: str) -> dict | None:
    """
    Analiza una transcripcion con Gemini y extrae preguntas del reclutador.

    Args:
        transcript: Texto completo de la transcripcion.
        filename: Nombre del archivo original (para metadata).

    Returns:
        Diccionario con el analisis estructurado, o None si falla.
    """
    print(f"  [3/3] Analizando transcripcion con {GEMINI_MODEL}...")

    user_prompt = f"""Analiza la siguiente transcripcion de entrevista.

Nombre del archivo: {filename}
Fecha de analisis: {datetime.date.today().isoformat()}

--- TRANSCRIPCION ---
{transcript}
--- FIN TRANSCRIPCION ---"""

    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )

            result = json.loads(response.text)

            # Validar estructura minima
            if "preguntas" not in result:
                print("  [ERROR] El analisis no contiene la clave 'preguntas'.")
                return None

            num_preguntas = len(result.get("preguntas", []))
            num_info_empresa = len(result.get("informacion_empresa", []))
            print(f"  [OK] Analisis completado: {num_preguntas} preguntas identificadas, {num_info_empresa} datos de empresa extraidos")
            return result

        except json.JSONDecodeError:
            print("  [ERROR] La respuesta del modelo no es JSON valido.")
            return None
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in str(e) or "resource exhausted" in error_str or "rate" in error_str

            if is_rate_limit and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"  [RATE LIMIT] Reintentando en {delay}s... (intento {attempt}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                print(f"  [ERROR] Fallo en el analisis: {e}")
                return None

    return None
