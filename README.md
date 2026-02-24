# Interview Analysis Agent

Agente de IA que analiza grabaciones de entrevistas de trabajo, extrae las preguntas del reclutador, genera respuestas optimas y formatea todo como posts listos para LinkedIn.

**Costo de operacion: $0** - Usa Whisper local (gratis) + Gemini API tier gratuito.

## Como funciona

El proyecto tiene **2 flujos independientes** con un punto de revision manual entre ellos:

```
FLUJO 1: Analisis                         FLUJO 2: Formato LinkedIn
========================                  ========================
Grabacion (.mkv/.mp4)                     Analisis (.json)
    |                                         |
    v                                         v
Extraer audio (ffmpeg)                    Generar posts (Gemini)
    |                                         |
    v                                         v
Transcribir (Whisper local)               Guardar como .txt
    |                                         |
    v                                         v
Analizar preguntas (Gemini)               Posts listos para
    |                                     copiar/pegar en LinkedIn
    v
Guardar analisis (.json)
    |
    v
[REVISION MANUAL] <-- Tu revisas antes de continuar
```

## Que extrae

Para cada entrevista, el agente identifica:

- **Todas las preguntas** que hizo el reclutador
- **Rango de tiempo** de cada pregunta en la grabacion (HH:MM:SS - HH:MM:SS)
- **Categoria** de cada pregunta (tecnica, conductual, situacional, cultura, logistica)
- **Respuesta del candidato** (resumen)
- **Respuesta optima** sugerida (usando metodo STAR cuando aplica)
- **Tips** para mejorar la respuesta
- **Informacion de la empresa** compartida por el entrevistador (estructura del equipo, tecnologias, cultura, clientes, crecimiento, beneficios, dia a dia del rol, etc.)
- **Metadata**: puesto, empresa, tipo de entrevista
- **Evaluacion general**: fortalezas, areas de mejora

## Stack tecnologico

| Componente | Tecnologia | Costo |
|---|---|---|
| Transcripcion | Whisper local (`openai-whisper`) | Gratis |
| Analisis / LLM | Google Gemini API (`google-genai`) | Gratis (tier gratuito) |
| Extraccion audio | ffmpeg | Gratis |
| Lenguaje | Python 3.10+ | - |

## Requisitos

- **Python 3.10+**
- **ffmpeg** instalado y en el PATH ([descargar](https://ffmpeg.org/download.html))
- **API key de Gemini** gratuita ([obtener](https://aistudio.google.com/apikey))
- **RAM/VRAM**: depende del escenario (ver tabla abajo)

### GPU vs CPU

El proyecto funciona en ambos escenarios. La GPU acelera significativamente la transcripcion con Whisper:

| Escenario | Modelo Whisper recomendado | Requisito | Velocidad (30 min audio) |
|---|---|---|---|
| **Con GPU NVIDIA** | `turbo` | ~6 GB VRAM | ~2-3 min |
| **Sin GPU (solo CPU)** | `medium` | ~5 GB RAM | ~10-15 min |
| **PC con poca RAM** | `small` | ~2 GB RAM | ~8-10 min |

## Instalacion

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/interview-analysis-agent.git
cd interview-analysis-agent

# 2. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Instalacion con GPU NVIDIA (recomendado si tienes GPU)

Si tienes una GPU NVIDIA con soporte CUDA, instala PyTorch con CUDA **antes** de las
demas dependencias. Esto permite que Whisper use tu GPU para transcribir mucho mas rapido.

```bash
# 3a. Instalar PyTorch con soporte CUDA
#     Consulta tu version de CUDA con: nvidia-smi
#     Luego elige el comando segun tu version (ver https://pytorch.org/get-started/locally/):

# CUDA 12.8 o superior:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# CUDA 12.6:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 4a. Instalar el resto de dependencias
pip install -r requirements.txt
```

> **Importante**: Si ejecutas `pip install -r requirements.txt` primero, `openai-whisper` instalara
> PyTorch en version CPU. Si esto sucede, reinstala PyTorch con el comando del paso 3a
> (pip detectara el conflicto y reemplazara la version CPU).

### Instalacion sin GPU (solo CPU)

```bash
# 3b. Instalar dependencias directamente
pip install -r requirements.txt
```

Whisper funcionara en CPU. Es mas lento pero perfectamente funcional.

### Verificar instalacion de PyTorch

```bash
python check_cuda.py
```

- `CUDA disponible: True` -> PyTorch detecta tu GPU, Whisper la usara automaticamente.
- `CUDA disponible: False` -> Whisper usara CPU. Si tienes GPU NVIDIA, revisa la seccion de instalacion con GPU.

### Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tu API key de Gemini, la ruta a tus grabaciones,
# y el modelo de Whisper segun tu escenario (turbo con GPU, medium sin GPU)
```

### Instalar ffmpeg

ffmpeg es necesario para extraer el audio de los archivos de video. Debe estar instalado
en tu sistema y disponible en el PATH.

**Windows:**

```bash
# Opcion 1: Con winget (recomendado)
winget install FFmpeg

# Opcion 2: Descarga manual
# 1. Descargar desde https://www.gyan.dev/ffmpeg/builds/ (release essentials)
# 2. Extraer el ZIP en una carpeta (ej: C:\ffmpeg)
# 3. Agregar C:\ffmpeg\bin al PATH del sistema:
#    - Buscar "Variables de entorno" en el menu de inicio
#    - Editar la variable "Path" del sistema
#    - Agregar la ruta a la carpeta bin (ej: C:\ffmpeg\bin)
```

**macOS:**

```bash
brew install ffmpeg
```

**Linux:**

```bash
sudo apt install ffmpeg
```

**Verificar instalacion** (cerrar y reabrir la terminal despues de instalar):

```bash
ffmpeg -version
```

Si el comando no se reconoce despues de instalar, cierra y reabre tu terminal para
que se actualice el PATH.

### Obtener API key de Gemini (gratis)

1. Ve a [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Inicia sesion con tu cuenta de Google
3. Clic en "Create API Key"
4. Copia la key y pegala en tu archivo `.env`

## Uso

### Flujo 1: Analizar entrevistas

```bash
# Procesar todas las grabaciones pendientes
python flow_analyze.py

# Procesar un archivo especifico
python flow_analyze.py --file "mi_entrevista.mkv"

# Re-analizar con Gemini (usa transcripciones cacheadas, no re-transcribe)
python flow_analyze.py --reprocess
```

Las transcripciones se cachean en `output/transcriptions/` como archivos `.txt`.
Si ya existe una transcripcion para un archivo, se omite la extraccion de audio y
transcripcion con Whisper, y se pasa directo al analisis con Gemini. Esto permite
re-ejecutar el flujo rapidamente si Gemini falla o si quieres cambiar el prompt.

#### Cuando usar `--reprocess`

El flag `--reprocess` re-ejecuta **solo el paso de analisis con Gemini** para todos
los archivos, usando las transcripciones ya cacheadas. Esto es util cuando:

- Se actualiza el prompt de analisis (por ejemplo, para extraer nuevos campos).
- Gemini fallo en algun archivo y quieres reintentarlo.
- Quieres cambiar el modelo de Gemini (en `.env`) y regenerar todos los analisis.

No re-transcribe con Whisper (el paso mas lento), asi que es rapido. Los nuevos JSON
se guardan junto a los anteriores en `output/analysis/` con un timestamp diferente.

Los resultados se guardan en `output/analysis/` como archivos JSON.

**Aqui revisas los datos** antes de continuar con el Flujo 2.

### Flujo 2: Generar posts para LinkedIn

```bash
# Ver analisis disponibles
python flow_format.py --list

# Formatear todos los analisis pendientes
python flow_format.py

# Formatear un analisis especifico
python flow_format.py --file "nombre_del_analisis.json"
```

Los posts se guardan como archivos `.txt` individuales en `output/linkedin_posts/`, listos para copiar y pegar.

## Estructura del proyecto

```
interview-analysis-agent/
|-- config.py                  # Configuracion centralizada
|-- flow_analyze.py            # Flujo 1: Grabacion -> Analisis JSON
|-- flow_format.py             # Flujo 2: Analisis JSON -> Posts LinkedIn
|-- requirements.txt           # Dependencias Python
|-- .env.example               # Plantilla de configuracion
|-- .gitignore                 # Proteccion de datos sensibles
|-- src/
|   |-- __init__.py
|   |-- audio_extractor.py     # Extraccion de audio con ffmpeg
|   |-- transcriber.py         # Transcripcion con Whisper local
|   |-- analyzer.py            # Analisis con Gemini
|   |-- linkedin_formatter.py  # Formateo de posts para LinkedIn
|-- output/                    # (gitignored) Datos generados
    |-- transcriptions/        # Cache de transcripciones (.txt con timestamps)
    |-- analysis/              # JSONs con analisis de entrevistas
    |-- linkedin_posts/        # Posts .txt listos para LinkedIn
```

## Ejemplo de output

### Analisis JSON (Flujo 1)

```json
{
  "metadata": {
    "puesto": "Senior Backend Developer",
    "empresa": "Acme Corp",
    "tipo_entrevista": "tecnica"
  },
  "preguntas": [
    {
      "numero": 1,
      "rango_tiempo": "00:02:15 - 00:02:42",
      "categoria": "tecnica",
      "pregunta": "Como manejas la escalabilidad en sistemas distribuidos?",
      "respuesta_candidato": "Menciono uso de microservicios y caching...",
      "respuesta_optima": "En mi experiencia con sistemas distribuidos...",
      "tip": "Usa ejemplos concretos con metricas de impacto."
    }
  ],
  "informacion_empresa": [
    {
      "rango_tiempo": "00:12:30 - 00:13:45",
      "tema": "estructura_equipo",
      "detalle": "El equipo de backend tiene 8 personas distribuidas entre Madrid y CDMX."
    },
    {
      "rango_tiempo": "00:14:00 - 00:14:30",
      "tema": "tecnologias_herramientas",
      "detalle": "Usan Kubernetes en AWS, con microservicios en Go y Python."
    }
  ]
}
```

### Post LinkedIn (Flujo 2)

```
Me preguntaron esto en una entrevista tecnica:

"Como manejas la escalabilidad en sistemas distribuidos?"

Esta es la mejor forma de responder:

1. Empieza con tu experiencia directa
2. Menciona herramientas especificas
3. Cierra con resultados medibles

Y tu, como responderias esta pregunta?

#Entrevistas #Backend #DesarrolloDeSoftware
```

## Seguridad

El `.gitignore` protege:
- API keys (`.env`)
- Datos de entrevistas (`output/`)
- Grabaciones de audio/video
- Notas internas personales

## Licencia

MIT
