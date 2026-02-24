"""
FLUJO 1: Analisis de Entrevistas
=================================
Escanea la carpeta de grabaciones, extrae audio de archivos MKV,
transcribe con Whisper local y analiza con Gemini. Guarda el resultado en JSON.

Uso:
    python flow_analyze.py                  # Procesa todos los archivos pendientes
    python flow_analyze.py --file video.mkv # Procesa un archivo especifico
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

GEMINI_RATE_LIMIT_DELAY = 6  # segundos entre requests para no superar 10 req/min

from config import INTERVIEWS_FOLDER, ANALYSIS_DIR, ANALYSIS_ARCHIVE_DIR, TRANSCRIPTIONS_DIR, SUPPORTED_EXTENSIONS
from src.audio_extractor import extract_audio, cleanup_temp_audio
from src.transcriber import transcribe_audio
from src.analyzer import analyze_transcript


def get_processed_files() -> set:
    """Retorna un set con los nombres de archivos ya procesados."""
    processed = set()
    for json_file in ANALYSIS_DIR.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            original = data.get("metadata", {}).get("nombre_archivo", "")
            if original:
                processed.add(original)
        except (json.JSONDecodeError, KeyError):
            continue
    return processed


def get_cached_transcript(filename: str) -> str | None:
    """Busca una transcripcion cacheada en output/transcriptions/."""
    stem = Path(filename).stem
    cache_path = TRANSCRIPTIONS_DIR / f"{stem}.txt"

    if cache_path.exists():
        content = cache_path.read_text(encoding="utf-8").strip()
        if content:
            return content
    return None


def save_transcript(transcript: str, filename: str) -> Path:
    """Guarda la transcripcion en output/transcriptions/ para reutilizarla."""
    stem = Path(filename).stem
    cache_path = TRANSCRIPTIONS_DIR / f"{stem}.txt"

    cache_path.write_text(transcript, encoding="utf-8")
    return cache_path


def save_analysis(analysis_data: dict, filename: str) -> Path:
    """Guarda el analisis como archivo JSON en output/analysis/ y archiva los antiguos."""
    stem = Path(filename).stem
    
    # Archivar analisis anteriores del mismo archivo
    for old_json in ANALYSIS_DIR.glob(f"{stem}_*.json"):
        if old_json.is_file():
            # Mover a la carpeta archive
            archive_path = ANALYSIS_ARCHIVE_DIR / old_json.name
            try:
                # Usar rename para mover el archivo
                old_json.rename(archive_path)
            except Exception as e:
                print(f"  [AVISO] No se pudo archivar el analisis anterior {old_json.name}: {e}")

    # Guardar el nuevo analisis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{stem}_{timestamp}.json"
    output_path = ANALYSIS_DIR / output_filename

    output_path.write_text(
        json.dumps(analysis_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def process_single_file(filepath: str) -> bool:
    """
    Procesa un unico archivo de video/audio: extraccion -> transcripcion -> analisis.

    Si ya existe una transcripcion cacheada en output/transcriptions/, omite la
    extraccion de audio y transcripcion con Whisper, y pasa directo al analisis
    con Gemini. Esto ahorra tiempo al re-ejecutar el flujo.

    Returns:
        True si el procesamiento fue exitoso.
    """
    filename = os.path.basename(filepath)
    print(f"\n{'=' * 60}")
    print(f"  PROCESANDO: {filename}")
    print(f"{'=' * 60}")

    audio_path = None

    try:
        # Verificar si ya existe transcripcion cacheada
        transcript = get_cached_transcript(filename)

        if transcript:
            word_count = len(transcript.split())
            print(f"  [CACHE] Transcripcion encontrada ({word_count} palabras)")
            print(f"  [CACHE] Omitiendo extraccion de audio y transcripcion")
        else:
            # Paso 1: Extraer audio (si es video)
            ext = Path(filepath).suffix.lower()
            if ext in (".mp3", ".wav"):
                audio_path = filepath
                print(f"  [1/3] Archivo de audio directo, omitiendo extraccion.")
            else:
                audio_path = extract_audio(filepath)
                if not audio_path:
                    return False

            # Paso 2: Transcribir
            transcript = transcribe_audio(audio_path)
            if not transcript:
                return False

            # Guardar transcripcion en cache para futuras ejecuciones
            cache_path = save_transcript(transcript, filename)
            print(f"  [CACHE] Transcripcion guardada en: {cache_path}")

        # Paso 3: Analizar con Gemini
        analysis = analyze_transcript(transcript, filename)
        if not analysis:
            return False

        # Guardar resultado
        output_path = save_analysis(analysis, filename)
        print(f"\n  [GUARDADO] {output_path}")
        print(f"  Preguntas encontradas: {len(analysis.get('preguntas', []))}")
        return True

    finally:
        # Limpiar audio temporal (solo si fue extraido, no si era el archivo original)
        if audio_path and audio_path != filepath:
            cleanup_temp_audio(audio_path)


def process_all(reprocess: bool = False) -> dict:
    """
    Procesa todos los archivos de la carpeta de entrevistas que no hayan sido procesados.

    Args:
        reprocess: Si True, re-analiza archivos ya procesados (usa transcripciones cacheadas).

    Returns:
        Diccionario con estadisticas del procesamiento.
    """
    if not INTERVIEWS_FOLDER or not os.path.exists(INTERVIEWS_FOLDER):
        print("[ERROR] La carpeta de entrevistas no esta configurada o no existe.")
        print(f"  Ruta configurada: {INTERVIEWS_FOLDER}")
        print("  Revisa la variable INTERVIEWS_FOLDER en tu archivo .env")
        return {"total": 0, "exitosos": 0, "fallidos": 0, "omitidos": 0}

    # Buscar archivos
    files = [
        f for f in os.listdir(INTERVIEWS_FOLDER)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]

    if not files:
        print(f"[INFO] No se encontraron archivos soportados en: {INTERVIEWS_FOLDER}")
        print(f"  Extensiones soportadas: {', '.join(SUPPORTED_EXTENSIONS)}")
        return {"total": 0, "exitosos": 0, "fallidos": 0, "omitidos": 0}

    # Filtrar ya procesados (a menos que se pida reprocesar)
    if reprocess:
        pending = files
        omitted = 0
    else:
        processed = get_processed_files()
        pending = [f for f in files if f not in processed]
        omitted = len(files) - len(pending)

    print(f"\n{'#' * 60}")
    print(f"  FLUJO 1: ANALISIS DE ENTREVISTAS")
    print(f"{'#' * 60}")
    print(f"  Archivos encontrados: {len(files)}")
    print(f"  Ya procesados: {omitted}")
    print(f"  Pendientes: {len(pending)}")
    print(f"{'#' * 60}")

    if not pending:
        print("\n  Todos los archivos ya fueron procesados.")
        print("  Usa --reprocess para re-analizar con Gemini (usa transcripciones cacheadas).")
        return {"total": len(files), "exitosos": 0, "fallidos": 0, "omitidos": omitted}

    stats = {"total": len(files), "exitosos": 0, "fallidos": 0, "omitidos": omitted}

    for i, filename in enumerate(pending):
        filepath = os.path.join(INTERVIEWS_FOLDER, filename)
        success = process_single_file(filepath)

        if success:
            stats["exitosos"] += 1
        else:
            stats["fallidos"] += 1

        # Rate limiting: esperar entre requests para no saturar Gemini (10 req/min)
        if i < len(pending) - 1:
            print(f"  [RATE LIMIT] Esperando {GEMINI_RATE_LIMIT_DELAY}s antes del siguiente archivo...")
            time.sleep(GEMINI_RATE_LIMIT_DELAY)

    # Resumen final
    print(f"\n{'#' * 60}")
    print(f"  RESUMEN")
    print(f"{'#' * 60}")
    print(f"  Exitosos:  {stats['exitosos']}")
    print(f"  Fallidos:  {stats['fallidos']}")
    print(f"  Omitidos:  {stats['omitidos']}")
    print(f"{'#' * 60}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Flujo 1: Analisis de entrevistas grabadas"
    )
    parser.add_argument(
        "--file", "-f",
        help="Procesar un archivo especifico en lugar de toda la carpeta",
    )
    parser.add_argument(
        "--reprocess", "-r",
        action="store_true",
        help="Re-analizar con Gemini archivos ya procesados (usa transcripciones cacheadas)",
    )

    args = parser.parse_args()

    if args.file:
        # Procesar archivo especifico
        filepath = args.file
        if not os.path.isabs(filepath):
            filepath = os.path.join(INTERVIEWS_FOLDER, filepath)

        if not os.path.exists(filepath):
            print(f"[ERROR] Archivo no encontrado: {filepath}")
            sys.exit(1)

        success = process_single_file(filepath)
        sys.exit(0 if success else 1)
    else:
        # Procesar toda la carpeta
        stats = process_all(reprocess=args.reprocess)
        sys.exit(0 if stats["fallidos"] == 0 else 1)


if __name__ == "__main__":
    main()
