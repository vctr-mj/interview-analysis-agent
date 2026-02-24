"""
FLUJO 2: Formateo para LinkedIn
=================================
Lee los analisis JSON generados por el Flujo 1 y genera posts
formateados listos para copiar y pegar en LinkedIn.

Uso:
    python flow_format.py                   # Formatea todos los analisis pendientes
    python flow_format.py --file analisis.json  # Formatea un analisis especifico
    python flow_format.py --list            # Lista analisis disponibles
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

GEMINI_RATE_LIMIT_DELAY = 6  # segundos entre requests para no superar 10 req/min

from config import ANALYSIS_DIR, LINKEDIN_DIR, LINKEDIN_ARCHIVE_DIR
from src.linkedin_formatter import format_for_linkedin, save_posts_as_text


def get_available_analyses() -> list[Path]:
    """Retorna la lista de archivos JSON de analisis disponibles."""
    return sorted(ANALYSIS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


CATEGORIAS_POSTS = ("_tecnico_", "_soft_skills_", "_negocio_")


def get_formatted_files() -> set:
    """Retorna un set con los stems de analisis ya formateados."""
    formatted = set()
    for txt_file in LINKEDIN_DIR.glob("*.txt"):
        name = txt_file.stem
        # Los archivos siguen el patron: {stem_analisis}_{categoria}_{titulo}.txt
        for cat in CATEGORIAS_POSTS:
            idx = name.find(cat)
            if idx != -1:
                formatted.add(name[:idx])
                break
    return formatted


def list_analyses():
    """Muestra los analisis disponibles con su estado."""
    analyses = get_available_analyses()
    formatted = get_formatted_files()

    if not analyses:
        print("[INFO] No hay analisis disponibles.")
        print(f"  Ejecuta primero: python flow_analyze.py")
        return

    print(f"\n{'=' * 70}")
    print(f"  ANALISIS DISPONIBLES")
    print(f"{'=' * 70}")

    for i, path in enumerate(analyses, 1):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            metadata = data.get("metadata", {})
            num_preguntas = len(data.get("preguntas", []))
            puesto = metadata.get("puesto", "N/A")
            empresa = metadata.get("empresa", "N/A")

            status = "[FORMATEADO]" if path.stem in formatted else "[PENDIENTE] "

            print(f"  {i}. {status} {path.name}")
            print(f"     Puesto: {puesto} | Empresa: {empresa} | Preguntas: {num_preguntas}")
        except (json.JSONDecodeError, KeyError):
            print(f"  {i}. [ERROR] {path.name} - JSON invalido")

    print(f"{'=' * 70}\n")


def format_single_analysis(json_path: str | Path, reprocess: bool = False) -> bool:
    """
    Formatea un analisis JSON en posts para LinkedIn.

    Returns:
        True si el formateo fue exitoso.
    """
    json_path = Path(json_path)

    if not json_path.exists():
        print(f"[ERROR] Archivo no encontrado: {json_path}")
        return False

    print(f"\n{'=' * 60}")
    print(f"  FORMATEANDO: {json_path.name}")
    print(f"{'=' * 60}")

    try:
        analysis_data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"  [ERROR] El archivo no contiene JSON valido.")
        return False

    # Generar posts con Gemini
    posts_data = format_for_linkedin(analysis_data)
    if not posts_data:
        return False

    base_filename = json_path.stem
    metadata = analysis_data.get("metadata", {})

    # Archivar posts anteriores si se esta reprocesando
    if reprocess:
        for old_txt in LINKEDIN_DIR.glob(f"{base_filename}_*.txt"):
            if old_txt.is_file():
                archive_path = LINKEDIN_ARCHIVE_DIR / old_txt.name
                try:
                    old_txt.rename(archive_path)
                except Exception as e:
                    print(f"  [AVISO] No se pudo archivar el post anterior {old_txt.name}: {e}")

    # Guardar como archivos .txt individuales
    saved_files = save_posts_as_text(posts_data, str(LINKEDIN_DIR), base_filename, metadata)

    if saved_files:
        print(f"\n  Posts guardados en: {LINKEDIN_DIR}")
        print(f"  Archivos generados:")
        for f in saved_files:
            print(f"    -> {Path(f).name}")
        return True

    return False


def format_all(reprocess: bool = False) -> dict:
    """
    Formatea todos los analisis que no hayan sido procesados.

    Returns:
        Diccionario con estadisticas del formateo.
    """
    analyses = get_available_analyses()
    formatted = get_formatted_files()

    if not analyses:
        print("[INFO] No hay analisis disponibles para formatear.")
        print(f"  Ejecuta primero: python flow_analyze.py")
        return {"total": 0, "exitosos": 0, "fallidos": 0, "omitidos": 0}

    if reprocess:
        pending = analyses
        omitted = 0
    else:
        pending = [a for a in analyses if a.stem not in formatted]
        omitted = len(analyses) - len(pending)

    print(f"\n{'#' * 60}")
    print(f"  FLUJO 2: FORMATEO PARA LINKEDIN")
    print(f"{'#' * 60}")
    print(f"  Analisis disponibles: {len(analyses)}")
    print(f"  Ya formateados: {omitted}")
    print(f"  Pendientes: {len(pending)}")
    print(f"{'#' * 60}")

    if not pending:
        print("\n  Todos los analisis ya fueron formateados.")
        return {"total": len(analyses), "exitosos": 0, "fallidos": 0, "omitidos": omitted}

    stats = {"total": len(analyses), "exitosos": 0, "fallidos": 0, "omitidos": omitted}

    for i, analysis_path in enumerate(pending):
        success = format_single_analysis(analysis_path, reprocess=reprocess)

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
    print(f"  Carpeta:   {LINKEDIN_DIR}")
    print(f"{'#' * 60}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Flujo 2: Formateo de analisis para LinkedIn"
    )
    parser.add_argument(
        "--file", "-f",
        help="Formatear un archivo de analisis especifico (JSON)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Listar analisis disponibles y su estado",
    )
    parser.add_argument(
        "--reprocess", "-r",
        action="store_true",
        help="Re-formatear analisis ya procesados y archivar los posts antiguos",
    )

    args = parser.parse_args()

    if args.list:
        list_analyses()
        sys.exit(0)

    if args.file:
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = ANALYSIS_DIR / filepath

        success = format_single_analysis(filepath, reprocess=True)
        sys.exit(0 if success else 1)
    else:
        stats = format_all(reprocess=args.reprocess)
        sys.exit(0 if stats["fallidos"] == 0 else 1)


if __name__ == "__main__":
    main()
