"""
Modulo de transcripcion de audio a texto usando Whisper local.
Ejecuta el modelo directamente en la maquina (CPU o GPU), sin costo.
La transcripcion incluye marcas de tiempo por segmento para poder
validar contra el audio/video original.
"""

import os
import whisper
from config import WHISPER_MODEL_SIZE

# Singleton: el modelo se carga una sola vez y se reutiliza entre archivos
_model = None


def _get_model():
    """Carga el modelo de Whisper una sola vez (lazy loading)."""
    global _model
    if _model is None:
        print(f"  Cargando modelo Whisper '{WHISPER_MODEL_SIZE}'...")
        print(f"  (La primera vez descarga el modelo, puede tardar unos minutos)")
        _model = whisper.load_model(WHISPER_MODEL_SIZE)
        print(f"  [OK] Modelo Whisper cargado")
    return _model


def _format_timestamp(seconds: float) -> str:
    """Convierte segundos (float) a formato HH:MM:SS."""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribe_audio(audio_path: str) -> str | None:
    """
    Transcribe un archivo de audio a texto usando Whisper local.

    A diferencia de la API de OpenAI, Whisper local no tiene limite
    de tamano de archivo. Procesa cualquier duracion directamente.

    La transcripcion incluye marcas de tiempo por segmento en formato:
    [HH:MM:SS - HH:MM:SS] Texto del segmento...

    Args:
        audio_path: Ruta al archivo de audio (MP3, WAV, etc.).

    Returns:
        Texto transcrito con marcas de tiempo, o None si falla.
    """
    if not os.path.exists(audio_path):
        print(f"  [ERROR] Archivo de audio no encontrado: {audio_path}")
        return None

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"  [2/3] Transcribiendo audio ({file_size_mb:.1f} MB) con Whisper local...")

    try:
        model = _get_model()

        result = model.transcribe(
            audio_path,
            language="es",
            verbose=False,
        )

        segments = result.get("segments", [])

        if not segments:
            print("  [ERROR] La transcripcion resulto vacia.")
            return None

        # Formatear cada segmento con su marca de tiempo
        lines = []
        for seg in segments:
            start = _format_timestamp(seg["start"])
            end = _format_timestamp(seg["end"])
            text = seg["text"].strip()
            if text:
                lines.append(f"[{start} - {end}] {text}")

        transcript = "\n".join(lines)

        word_count = len(transcript.split())
        print(f"  [OK] Transcripcion completada: {word_count} palabras, {len(lines)} segmentos")
        return transcript

    except Exception as e:
        print(f"  [ERROR] Fallo en la transcripcion: {e}")
        return None
