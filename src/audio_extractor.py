"""
Modulo para extraer audio de archivos de video (MKV, MP4, etc.) usando ffmpeg.
Genera archivos temporales .mp3 optimizados para la transcripcion.
"""

import subprocess
import tempfile
import os
from pathlib import Path


def extract_audio(video_path: str | Path) -> str | None:
    """
    Extrae la pista de audio de un archivo de video y la guarda como MP3 temporal.

    Args:
        video_path: Ruta absoluta al archivo de video.

    Returns:
        Ruta al archivo MP3 temporal, o None si falla.
    """
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"  [ERROR] Archivo no encontrado: {video_path}")
        return None

    # Crear archivo temporal para el audio extraido
    temp_dir = tempfile.gettempdir()
    audio_filename = f"{video_path.stem}_audio.mp3"
    audio_path = os.path.join(temp_dir, audio_filename)

    print(f"  [1/3] Extrayendo audio de: {video_path.name}")

    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",                  # Sin video
            "-acodec", "libmp3lame",
            "-ab", "64k",           # Bitrate bajo, suficiente para voz
            "-ar", "16000",         # 16kHz, optimo para Whisper
            "-ac", "1",             # Mono
            "-y",                   # Sobreescribir si existe
            audio_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max por archivo
        )

        if result.returncode != 0:
            print(f"  [ERROR] ffmpeg fallo: {result.stderr[:200]}")
            return None

        # Verificar que el archivo se creo y tiene contenido
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            print("  [ERROR] El archivo de audio extraido esta vacio.")
            return None

        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"  [OK] Audio extraido: {audio_filename} ({size_mb:.1f} MB)")
        return audio_path

    except FileNotFoundError:
        print("  [ERROR] ffmpeg no esta instalado o no esta en el PATH.")
        print("  Instala ffmpeg: https://ffmpeg.org/download.html")
        return None
    except subprocess.TimeoutExpired:
        print("  [ERROR] La extraccion de audio excedio el tiempo limite (5 min).")
        return None
    except Exception as e:
        print(f"  [ERROR] Error inesperado en la extraccion: {e}")
        return None


def cleanup_temp_audio(audio_path: str) -> None:
    """Elimina el archivo de audio temporal despues de procesarlo."""
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    except OSError:
        pass  # No es critico si falla la limpieza
