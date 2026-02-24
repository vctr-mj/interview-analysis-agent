"""
Modulo para formatear el analisis de entrevistas en posts listos para LinkedIn.
Genera contenido optimizado para engagement en la plataforma.
"""

import json
import time
import re
from pathlib import Path
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

MAX_RETRIES = 3
RETRY_BASE_DELAY = 15  # segundos, se duplica en cada reintento

LINKEDIN_POST_PROMPT = """Eres un ghostwriter que transforma entrevistas de trabajo en posts para
LinkedIn escritos en primera persona. Tu tono es conversacional, honesto y directo.
Escribes como alguien que cuenta su experiencia real, no como un creador de contenido.
Sin formulas motivacionales, sin clickbait, sin frases genericas.

=== ESTRATEGIA: POSTS POR CATEGORIA ===

NO generes un post por cada pregunta. En su lugar, AGRUPA la informacion de la entrevista
en estas 3 categorias y genera UN post por categoria:

1. **tecnico**: Conocimientos duros. Agrupa las preguntas tecnicas (arquitectura, herramientas,
   coding, system design, etc.) y construye un post que hile las mas interesantes en una
   narrativa cohesiva. Elige las 2-3 preguntas tecnicas con mas sustancia, no las repitas todas.

2. **soft_skills**: Habilidades blandas. Agrupa preguntas conductuales y situacionales
   (liderazgo, trabajo en equipo, resolucion de conflictos, comunicacion). Enfocate en como
   el candidato manejo la situacion, donde fallo al comunicarse, o que habilidad se esperaba
   para el puesto. Se honesto: si la respuesta fue mala, cuentalo.

3. **negocio**: Empresa, puesto y rol. Usa la informacion que el entrevistador compartio
   sobre la empresa (estructura del equipo, tecnologias, cultura, clientes, beneficios,
   dia a dia, crecimiento) combinada con las preguntas de cultura/logistica para construir
   un post sobre lo que revela la entrevista acerca de la empresa o el rol. Si no hay
   suficiente informacion de empresa, enfocate en que revelan las preguntas sobre lo que
   la empresa realmente busca.

REGLAS DE AGRUPACION:
- Genera MINIMO 3 posts (uno por categoria), MAXIMO 6.
- Solo genera un segundo post de la misma categoria si hay informacion densa y variada
  que justifique dividirlo (ej: 5+ preguntas tecnicas profundas sobre temas distintos).
- Si una categoria no tiene informacion suficiente (ej: no hubo preguntas tecnicas),
  omite esa categoria. Pero intenta generar al menos las 3.
- Cada post debe funcionar de forma independiente. No hagas referencias cruzadas.

=== LAS 3 PRIMERAS LINEAS (CRITICO) ===

LinkedIn solo muestra ~3 lineas antes de "...ver mas".
Si esas lineas no enganchan, nadie lee el resto.
Las primeras 3 lineas DEBEN generar curiosidad, tension o identificacion.
NUNCA pongas tips, consejos ni la respuesta en las primeras 3 lineas. Solo engancha.

Varia el estilo del hook entre estos 4 tipos (NO repitas el mismo estilo en posts consecutivos):

1. Narrativo con tension: primera persona, cuenta que paso, incluye un conflicto o giro.
   Ej: "En mi ultima entrevista tecnica me quede en silencio 10 segundos.
   No porque no supiera. Sino porque la pregunta no tenia sentido."

2. Confesion/vulnerabilidad: admitir algo que normalmente no se dice en publico.
   Ej: "Respondi esta pregunta con total seguridad.
   Cuando colgue, me di cuenta de que estaba completamente equivocado."

3. Reflexivo/contrario: cuestiona la pregunta, el proceso o una creencia popular.
   Ej: "Me hicieron una pregunta que revelaba mas problemas de la empresa que del candidato."

4. Observacion con postura: algo que notaste o aprendiste, con una opinion clara.
   Ej: "Despues de varias entrevistas empece a notar un patron.
   Las empresas que hacen esta pregunta rara vez saben que buscan."

=== ESTRUCTURA DEL POST ===

Despues del hook, sigue esta estructura:

1. LA PREGUNTA (o las preguntas clave): citadas textualmente, separadas con salto de linea.
   Si agrupas varias preguntas, puedes introducirlas como "me hicieron varias preguntas
   sobre X, pero esta fue la que me hizo pensar: ..."
2. DESARROLLO: experiencia real con argumentacion. Varia entre estos enfoques:
   - A veces la respuesta del candidato fue buena: refuerzala con la optima.
   - A veces la respuesta no fue la mejor: cuentalo con honestidad, y luego
     comparte que habria sido mejor decir.
   - A veces combina ambas: "Respondi X, no estuvo mal, pero despues entendi
     que la clave era Y."
   Usa el enfoque que encaje mejor con el tema. No siempre tiene que ser positivo.
3. CONSEJO/REFLEXION: directo y crudo. Algo que el lector pueda aplicar.
   No uses frases motivacionales vacias.
4. CIERRE: reflexion contundente. Ocasionalmente incluye una pregunta o invitacion
   a la conversacion, pero SOLO cuando surja de forma natural. No fuerces un CTA
   en todos los posts. Un buen cierre sin pregunta es mejor que un CTA forzado.

=== EJEMPLO DE REFERENCIA (tono y estructura) ===

Este es un ejemplo real de LinkedIn con el tono y estructura que debes seguir:

\"\"\"
Alguna vez, en una entrevista, me preguntaron:
"Cual seria el primer modelo que implementarias?"

Se me hizo —y se los dije— una pregunta tramposa.
Sin conocer la empresa, el negocio, los datos ni las necesidades reales,
asumir que un modelo es "el correcto" es, en el mejor de los casos, ingenuo;
en el peor, soberbio.

Se los explique asi.
No les gusto. Me dijeron que me faltaba iniciativa.

Y aqui va el consejo:

Muchas veces, quienes entrevistan no necesariamente saben mas que ustedes del tema.
En ocasiones, simplemente improvisan preguntas "al aire" que suenan bien,
pero carecen de rigor tecnico o de contexto de negocio.

Ojo con eso.
La falta de seriedad y de criterio en una entrevista suele ser un sintoma
de fallas mas profundas dentro de la organizacion.
\"\"\"

Observa: narrativa en primera persona, honestidad (le fue mal y lo cuenta),
argumento tecnico solido, consejo directo, cierre contundente sin CTA forzado.

=== REGLAS GENERALES ===

- Escribe TODOS los posts en espanol, sin importar el idioma de la entrevista original.
- Saltos de linea frecuentes (una idea por linea), como se escribe en LinkedIn.
- NO uses emojis salvo que encaje naturalmente (maximo 1-2 por post, no obligatorio).
- Maximo 3-5 hashtags al final, separados del contenido.
- Longitud ideal: 1200-1800 caracteres.
- NUNCA uses frases tipo "Atencion!", "ESTO es lo que nadie te dice",
  "El secreto es...", "Te cuento por que..." ni formulas de clickbait.
- NO uses "tu" o "usted" en exceso. Habla como si estuvieras contando algo
  a un grupo de colegas, no dando una clase.

Devuelve UNICAMENTE un objeto JSON con este esquema:

{
    "posts": [
        {
            "categoria": "tecnico | soft_skills | negocio",
            "titulo_interno": "Titulo corto para identificar el post",
            "contenido": "El post completo listo para copiar y pegar en LinkedIn",
            "hashtags": ["#hashtag1", "#hashtag2"],
            "mejor_horario": "martes 8:00 AM | miercoles 10:00 AM | jueves 12:00 PM",
            "preguntas_incluidas": [1, 3, 5]
        }
    ]
}"""


def format_for_linkedin(analysis_data: dict) -> dict | None:
    """
    Transforma el analisis de una entrevista en posts formateados para LinkedIn.

    Agrupa la informacion por categorias (tecnico, soft_skills, negocio) en lugar
    de generar un post por cada pregunta individual.

    Args:
        analysis_data: Diccionario con el analisis de la entrevista (output de analyzer.py).

    Returns:
        Diccionario con los posts formateados, o None si falla.
    """
    preguntas = analysis_data.get("preguntas", [])
    metadata = analysis_data.get("metadata", {})
    info_empresa = analysis_data.get("informacion_empresa", [])
    resumen = analysis_data.get("resumen", {})

    if not preguntas:
        print("  [ERROR] No hay preguntas para formatear.")
        return None

    print(f"  Generando posts por categoria para LinkedIn ({len(preguntas)} preguntas base)...")

    user_prompt = f"""Analiza la siguiente entrevista y genera posts para LinkedIn AGRUPADOS POR CATEGORIA
(tecnico, soft_skills, negocio). NO generes un post por cada pregunta.

Contexto de la entrevista:
- Puesto: {metadata.get('puesto', 'No especificado')}
- Empresa: {metadata.get('empresa', 'No especificado')}
- Tipo: {metadata.get('tipo_entrevista', 'No especificado')}

Preguntas identificadas (con categoria, respuesta del candidato y respuesta optima):
{json.dumps(preguntas, ensure_ascii=False, indent=2)}

Informacion que el entrevistador compartio sobre la empresa/rol:
{json.dumps(info_empresa, ensure_ascii=False, indent=2) if info_empresa else "No se identifico informacion adicional de la empresa."}

Evaluacion general del candidato:
- Fortalezas: {', '.join(resumen.get('fortalezas_candidato', ['No identificadas']))}
- Areas de mejora: {', '.join(resumen.get('areas_mejora', ['No identificadas']))}
- Impresion general: {resumen.get('impresion_general', 'No disponible')}

Instrucciones:
- Agrupa las preguntas por categoria y genera 1 post por categoria (minimo 3, maximo 6).
- Para el post "tecnico": elige las 2-3 preguntas tecnicas con mas sustancia.
- Para el post "soft_skills": enfocate en donde el candidato fallo o brillo al comunicarse.
- Para el post "negocio": combina la informacion de empresa con las preguntas de cultura/logistica.
- Solo divide una categoria en 2 posts si hay informacion muy densa y variada.
- En "preguntas_incluidas" indica los numeros de las preguntas que usaste para cada post."""

    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=LINKEDIN_POST_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )

            result = json.loads(response.text)

            if "posts" not in result:
                print("  [ERROR] La respuesta no contiene posts.")
                return None

            num_posts = len(result["posts"])
            print(f"  [OK] {num_posts} posts generados para LinkedIn")
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
                print(f"  [ERROR] Fallo al generar posts: {e}")
                return None

    return None


def save_posts_as_text(posts_data: dict, output_dir: str, base_filename: str, metadata: dict = None) -> list:
    """
    Guarda cada post como archivo .txt individual listo para copiar/pegar.

    La cabecera interna (que no se sube a LinkedIn) incluye informacion de
    contexto para identificar facilmente el post: puesto, empresa, archivo origen.

    Args:
        posts_data: Diccionario con los posts generados.
        output_dir: Directorio donde guardar los archivos.
        base_filename: Nombre base del archivo original (sin extension).
        metadata: Diccionario con metadata de la entrevista (puesto, empresa, nombre_archivo).

    Returns:
        Lista de rutas a los archivos creados.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata = metadata or {}
    puesto = metadata.get("puesto", "No especificado")
    empresa = metadata.get("empresa", "No especificado")
    archivo_origen = metadata.get("nombre_archivo", base_filename)

    CATEGORIAS_LABEL = {
        "tecnico": "Tecnico",
        "soft_skills": "Soft Skills",
        "negocio": "Negocio/Empresa/Rol",
    }

    saved_files = []
    posts = posts_data.get("posts", [])

    # Contador por categoria para manejar multiples posts de la misma categoria
    cat_counter = {}

    for post in posts:
        categoria = post.get("categoria", "general")
        cat_counter[categoria] = cat_counter.get(categoria, 0) + 1
        cat_num = cat_counter[categoria]

        # Obtener el titulo y sanitizar caracteres invalidos para Windows/Linux
        titulo_crudo = post.get("titulo_interno", f"post_{categoria}")
        titulo_limpio = re.sub(r'[<>:"/\\|?*]', '', titulo_crudo)
        titulo = titulo_limpio.replace(" ", "_")[:50]

        # Nombre de archivo: {base}_{categoria}_{num}_{titulo}.txt
        if cat_num > 1:
            filename = f"{base_filename}_{categoria}_{cat_num:02d}_{titulo}.txt"
        else:
            filename = f"{base_filename}_{categoria}_{titulo}.txt"
        filepath = output_path / filename

        categoria_label = CATEGORIAS_LABEL.get(categoria, categoria.capitalize())
        preguntas_nums = post.get("preguntas_incluidas", [])
        preguntas_str = ", ".join(f"#{n}" for n in preguntas_nums) if preguntas_nums else "N/A"

        content_lines = [
            f"{'=' * 60}",
            f"POST PARA LINKEDIN - {categoria_label}",
            f"Puesto: {puesto} | Empresa: {empresa}",
            f"Archivo origen: {archivo_origen}",
            f"Titulo interno: {post.get('titulo_interno', '')}",
            f"Mejor horario: {post.get('mejor_horario', 'No especificado')}",
            f"Caracteres: {len(post.get('contenido', ''))}",
            f"Preguntas base: {preguntas_str}",
            f"{'=' * 60}",
            "",
            post.get("contenido", ""),
            "",
            f"{'=' * 60}",
            f"Hashtags: {' '.join(post.get('hashtags', []))}",
            f"{'=' * 60}",
        ]

        filepath.write_text("\n".join(content_lines), encoding="utf-8")
        saved_files.append(str(filepath))

    print(f"  [OK] {len(saved_files)} archivos .txt guardados en {output_dir}")
    return saved_files
