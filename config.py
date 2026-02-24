import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Rutas del proyecto ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TRANSCRIPTIONS_DIR = OUTPUT_DIR / "transcriptions"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"
LINKEDIN_DIR = OUTPUT_DIR / "linkedin_posts"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
ANALYSIS_ARCHIVE_DIR = ARCHIVE_DIR / "analysis"
LINKEDIN_ARCHIVE_DIR = ARCHIVE_DIR / "linkedin_posts"

# --- Carpeta de grabaciones ---
INTERVIEWS_FOLDER = os.getenv("INTERVIEWS_FOLDER", "")

# --- Whisper (transcripcion local) ---
# Opciones: tiny | base | small | medium | large | turbo
# - tiny/base: rapido, menor calidad (~1 GB RAM)
# - small: buen balance velocidad/calidad (~2 GB RAM)
# - medium: alta calidad, mas lento (~5 GB RAM) - recomendado sin GPU
# - turbo: maxima calidad, rapido (~6 GB VRAM) - recomendado con GPU NVIDIA
# - large: maxima calidad, lento (~10 GB VRAM) - requiere GPU
# Con GPU NVIDIA + PyTorch CUDA: usar "turbo" (ver README para setup)
# Sin GPU: usar "medium"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")

# --- Gemini (analisis LLM) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Formatos de archivo soportados ---
SUPPORTED_EXTENSIONS = (".mkv", ".mp4", ".mov", ".avi", ".mp3", ".wav")

# --- LinkedIn: horarios optimos de publicacion ---
LINKEDIN_TIMEZONE = os.getenv("LINKEDIN_TIMEZONE", "America/Mexico_City")
LINKEDIN_BEST_HOURS = [8, 10, 12, 17]  # Horas con mayor engagement

# --- Crear directorios si no existen ---
TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
LINKEDIN_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
LINKEDIN_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
