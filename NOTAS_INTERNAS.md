# NOTAS INTERNAS
Estas notas detallan las decisiones tecnicas.

---

## 1. Analisis de herramientas evaluadas

### Transcripcion de audio (Speech-to-Text)

Se evaluaron 3 opciones para convertir audio de entrevistas a texto:

| Herramienta | Tipo | Costo | Calidad ES | Limite tamano | Elegida |
|---|---|---|---|---|---|
| OpenAI Whisper API | Cloud | $0.006/min | Excelente | 25 MB por request | No |
| Whisper local (`openai-whisper`) | Local | **Gratis** | Excelente | **Sin limite** | **Si** |
| Google Cloud Speech-to-Text | Cloud | $0.006-0.009/min | Buena | Requiere GCS bucket | No |

**Decision: Whisper local.**
- Es el mismo modelo que la API de OpenAI, pero corre en tu maquina.
- No tiene limite de tamano de archivo (la API limita a 25 MB).
- Costo cero permanente.
- Desventaja: mas lento sin GPU, pero para pocas entrevistas es aceptable.

### Modelos LLM para analisis

Se evaluaron 3 servicios de LLM para analizar transcripciones y generar contenido:

| Servicio | Modelo | API gratuita? | Costo API | JSON nativo | Calidad |
|---|---|---|---|---|---|
| OpenAI | GPT-4o | **No** | $2.50-$10/1M tokens | Si (`response_format`) | Excelente |
| Anthropic | Claude Sonnet/Opus | **No** | $3-$15/1M tokens | Manual | Excelente |
| **Google** | **Gemini 2.5 Flash** | **Si** | **Gratis** (tier gratuito) | **Si** (`response_mime_type`) | Excelente |

**Decision: Gemini 2.5 Flash (tier gratuito).**

Razonamiento:
- Claude Pro y Gemini Advanced son suscripciones web ($20/mes), NO dan API keys.
  La suscripcion de claude.ai o gemini.google.com es solo para el chat web.
  Para usar IA en codigo necesitas API keys, que son un producto separado.
- Gemini es el unico que ofrece un tier gratuito generoso para la API.
- Para el volumen de este proyecto (unas pocas entrevistas por semana), el tier
  gratuito nunca se alcanza.

### Limites del tier gratuito de Gemini (verificar en https://ai.google.dev/pricing)

| Modelo | Requests/min | Tokens/min | Requests/dia |
|---|---|---|---|
| gemini-2.5-flash | 10 | 250,000 | 500 |
| gemini-2.5-pro | 5 | 250,000 | 25 |
| gemini-2.0-flash | 15 | 1,000,000 | 1,500 |

Para este proyecto, `gemini-2.5-flash` es la mejor opcion:
- 500 requests/dia es mas que suficiente
- Buena calidad en espanol
- Respuestas rapidas (~2-5 segundos)
- Soporte nativo para JSON estructurado

Si necesitas maxima calidad de razonamiento, puedes cambiar a `gemini-2.5-pro`
en el .env, pero solo tienes 25 requests/dia gratis.

### Nota importante sobre suscripciones vs API

```
SUSCRIPCION WEB (lo que pagas)          API (lo que usa el codigo)
================================        ================================
Claude Pro ($20/mes)                    Anthropic API (creditos aparte)
  -> Solo chat en claude.ai               -> Requiere comprar creditos
  -> NO incluye API                        -> $3-$15/1M tokens

Gemini Advanced ($20/mes)               Google AI API (tier gratuito!)
  -> Solo chat en gemini.google.com        -> API key gratis en aistudio
  -> NO incluye API                        -> 500 req/dia sin costo

OpenAI Plus ($20/mes)                   OpenAI API (creditos aparte)
  -> Solo chat en chatgpt.com              -> Requiere comprar creditos
  -> NO incluye API                        -> $2.50-$10/1M tokens
```

**Conclusion**: El unico servicio donde tu suscripcion web te beneficia
indirectamente es Google, porque la API de Gemini tiene tier gratuito
independiente de tu suscripcion.

---

## 2. Modelos de Whisper - Cual elegir

El modelo se configura en `.env` con `WHISPER_MODEL_SIZE`:

| Modelo | Parametros | RAM/VRAM | Velocidad relativa | Calidad ES | Recomendacion |
|---|---|---|---|---|---|
| `tiny` | 39M | ~1 GB | 10x | Baja | Solo para pruebas rapidas |
| `base` | 74M | ~1 GB | 7x | Aceptable | Pruebas con calidad basica |
| `small` | 244M | ~2 GB | 4x | Buena | PC con poca RAM |
| `medium` | 769M | ~5 GB | 2x | **Alta** | Recomendado **sin GPU** |
| `large` | 1550M | ~10 GB | 1x | Maxima | Solo con GPU (NVIDIA) |
| `turbo` | 809M | ~6 GB | 8x | Maxima | **Recomendado con GPU** |

Recomendaciones:
- **Con GPU NVIDIA (CUDA)**: usa `turbo`. Maxima calidad a velocidad rapida.
  Un audio de 30 min tarda ~2-3 min con GPU.
  `turbo` tiene la misma calidad que `large` pero es ~8x mas rapido.
- **Sin GPU (solo CPU)**: usa `medium`. Es el mejor balance calidad/velocidad.
  Un audio de 30 min tarda ~10-15 min en CPU.
- **PC con poca RAM (<4 GB libres)**: usa `small`.
- La primera vez que ejecutes el proyecto, descargara el modelo (~1.5 GB para medium,
  ~3 GB para turbo). Despues queda cacheado en `~/.cache/whisper/`.

### Configurar PyTorch con GPU (CUDA)

Whisper usa PyTorch internamente. Para que Whisper aproveche tu GPU NVIDIA, PyTorch
debe estar compilado con soporte CUDA. **Esto NO sucede automaticamente** con
`pip install openai-whisper` (eso instala la version CPU).

#### Instalacion correcta (con GPU)

El orden importa. PyTorch con CUDA debe instalarse **antes** de openai-whisper:

```bash
# 1. Verificar tu version de CUDA
nvidia-smi
# Busca "CUDA Version: XX.X" en la esquina superior derecha

# 2. Instalar PyTorch con CUDA (elegir segun tu version)
# Para CUDA 12.8+:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
# Para CUDA 12.6:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
# Para CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# Consultar versiones: https://pytorch.org/get-started/locally/

# 3. Instalar las demas dependencias
pip install -r requirements.txt
```

#### Problema comun: PyTorch se instala sin CUDA

Si instalas `openai-whisper` antes de PyTorch con CUDA (o ejecutas `pip install -r
requirements.txt` primero), pip descarga `torch` desde PyPI estandar, que es la
version CPU. Sintoma:

```python
import torch
print(torch.__version__)  # Muestra "2.x.x+cpu" en vez de "2.x.x+cu128"
print(torch.cuda.is_available())  # False
```

Solucion: reinstalar PyTorch con CUDA (ver paso 2 arriba). No necesitas desinstalar
nada, pip reemplaza automaticamente la version CPU.

Otro sintoma es que `pip list | grep torch` muestra torch sin sufijo `+cuXXX`
mientras que torchvision y torchaudio si lo tienen. Ejemplo del problema:
```
torch              2.10.0          <-- MAL: sin +cu128
torchaudio         2.10.0+cu128    <-- OK
torchvision        0.25.0+cu128    <-- OK
```

#### Verificar que PyTorch detecta tu GPU

```python
import torch
print(f"PyTorch version: {torch.__version__}")          # Debe decir +cu128 (o similar)
print(f"CUDA disponible: {torch.cuda.is_available()}")   # Debe ser True
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")       # Nombre de tu GPU
```

---

## 3. Guia detallada de uso paso a paso

### Preparacion inicial (solo la primera vez)

```bash
# 1. Abrir terminal en la carpeta del proyecto
cd /ruta/a/tu/proyecto/entrevistas-ia-agent

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual (Windows)
venv\Scripts\activate

# 4. (Solo si tienes GPU NVIDIA) Instalar PyTorch con CUDA
#    IMPORTANTE: hacer esto ANTES de instalar requirements.txt
#    Ver seccion "Configurar PyTorch con GPU (CUDA)" arriba para elegir la version correcta
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 5. Instalar dependencias
pip install -r requirements.txt
# Esto instala: openai-whisper, google-genai, python-dotenv
# Si no hiciste el paso 4, openai-whisper instalara PyTorch version CPU (~2 GB)

# 6. Verificar que PyTorch detecta tu GPU (si aplica)
python check_cuda.py
# Debe decir True si tienes GPU. Si dice False, revisa la seccion de troubleshooting.

# 7. Configurar .env
copy .env.example .env
# Editar .env con:
#   - Tu GEMINI_API_KEY (de https://aistudio.google.com/apikey)
#   - La ruta a tu carpeta de grabaciones
#   - WHISPER_MODEL_SIZE: turbo (con GPU) o medium (sin GPU)

# 8. Verificar ffmpeg
ffmpeg -version
# Si no lo tienes: winget install FFmpeg
```

### Uso diario

```bash
# 1. Activar entorno virtual (si no esta activo)
cd /ruta/a/tu/proyecto/entrevistas-ia-agent
venv\Scripts\activate

# 2. FLUJO 1: Analizar entrevistas nuevas
python flow_analyze.py
# Esto:
#   - Escanea /ruta/a/tus/entrevistas
#   - Extrae audio de cada .mkv con ffmpeg
#   - Transcribe con Whisper local (tarda unos minutos por archivo)
#   - Analiza con Gemini (identifica preguntas del reclutador + info de empresa)
#   - Guarda JSON en output/analysis/
#   - Omite archivos ya procesados automaticamente

# 2b. RE-ANALIZAR con Gemini (si cambiaste el prompt o quieres regenerar)
python flow_analyze.py --reprocess
# Esto:
#   - Toma TODOS los archivos (incluso los ya procesados)
#   - Usa las transcripciones cacheadas en output/transcriptions/ (NO re-transcribe)
#   - Solo re-ejecuta el analisis con Gemini
#   - Guarda nuevos JSON en output/analysis/ con timestamp diferente
#   - Es rapido porque no pasa por Whisper
#
# Cuando usarlo:
#   - Actualizaste el prompt en src/analyzer.py (ej: agregaste un campo nuevo)
#   - Cambiaste el modelo de Gemini en .env
#   - Gemini fallo en algunos archivos y quieres reintentarlo
#   - Quieres regenerar TODOS los analisis con la version actual del prompt

# 3. REVISION MANUAL
# Abre los JSON en output/analysis/ y revisa:
#   - Que las preguntas esten bien identificadas
#   - Que las respuestas optimas tengan sentido
#   - Que la informacion de empresa extraida sea correcta
#   - Que la metadata sea correcta

# 4. FLUJO 2: Generar posts para LinkedIn
python flow_format.py --list    # Ver que analisis estan disponibles
python flow_format.py           # Generar posts para todos los pendientes
# Los posts se guardan como .txt en output/linkedin_posts/
# Cada .txt tiene el post completo listo para copiar/pegar en LinkedIn

# 5. PUBLICAR EN LINKEDIN
# Abre cada .txt, copia el contenido y pegalo en LinkedIn
# El archivo incluye el horario sugerido para publicar
```

### Procesar un archivo especifico

```bash
# Si solo quieres procesar una entrevista en particular:
python flow_analyze.py --file "entrevista_ejemplo.mkv"

# O con ruta completa:
python flow_analyze.py --file "/ruta/a/tus/entrevistas/entrevista_ejemplo.mkv"
```

### Reformatear un analisis

```bash
# Si quieres regenerar los posts de un analisis especifico:
python flow_format.py --file "entrevista_ejemplo_20260217_143022.json"
```

---

## 4. Troubleshooting

### "ffmpeg no esta instalado o no esta en el PATH"

Este error (`FileNotFoundError` en `audio_extractor.py`) significa que Windows no
encuentra el ejecutable `ffmpeg.exe`. Causas posibles:

1. **ffmpeg no esta instalado**: necesitas instalarlo.
2. **ffmpeg no esta en el PATH**: esta instalado pero Windows no sabe donde buscarlo.
3. **Terminal no actualizada**: acabas de instalar ffmpeg pero no cerraste/reabriste la terminal.

```bash
# Verificar si ffmpeg esta disponible
ffmpeg -version

# Instalar en Windows (opcion 1: winget)
winget install FFmpeg
# IMPORTANTE: cerrar y reabrir la terminal despues de instalar

# Instalar en Windows (opcion 2: descarga manual)
# 1. Descargar desde https://www.gyan.dev/ffmpeg/builds/ (release essentials)
# 2. Extraer el ZIP en una carpeta, ej: C:\ffmpeg
# 3. Agregar C:\ffmpeg\bin al PATH del sistema:
#    - Buscar "Variables de entorno" en el menu de inicio de Windows
#    - En "Variables del sistema", seleccionar "Path" y clic en "Editar"
#    - Clic en "Nuevo" y agregar: C:\ffmpeg\bin
#    - Aceptar todo y REABRIR la terminal

# Instalar en macOS
brew install ffmpeg

# Instalar en Linux
sudo apt install ffmpeg
```

Despues de instalar, **siempre cerrar y reabrir la terminal** para que el PATH se
actualice. Si sigue fallando, verificar que la carpeta con `ffmpeg.exe` este en el
PATH del sistema (no solo del usuario).

### "Import whisper could not be resolved"

```bash
# Asegurate de estar en el entorno virtual
venv\Scripts\activate

# Reinstalar
pip install openai-whisper
```

### "Error en Gemini: 429 Resource Exhausted"

Llegaste al limite del tier gratuito. Opciones:
1. Esperar al dia siguiente (se resetea)
2. Cambiar a `gemini-2.0-flash` en .env (tiene 1500 req/dia)
3. Reducir la cantidad de entrevistas por dia

### "La transcripcion es de baja calidad"

1. Cambia el modelo de Whisper a uno mas grande en .env:
   `WHISPER_MODEL_SIZE=large` (necesita ~10 GB VRAM)
2. Asegurate de que el audio sea claro. Si la grabacion tiene mucho ruido,
   Whisper puede fallar.
3. El audio se extrae a mono 16kHz, que es optimo para Whisper.

### "El analisis no identifica bien las preguntas"

1. Cambia el modelo de Gemini a `gemini-2.5-pro` en .env (mas inteligente,
   pero solo 25 req/dia gratis)
2. Verifica que la transcripcion sea correcta revisando el output de Whisper

### "Whisper tarda demasiado"

- Sin GPU: es normal que `medium` tarde 10-15 min por cada 30 min de audio
- Opciones:
  - Usa `small` (mas rapido, algo menos preciso)
  - Si tienes GPU NVIDIA, instala PyTorch con CUDA (ver seccion 2) y cambia a `turbo`
  - Procesa las entrevistas durante la noche

### "AssertionError: Torch not compiled with CUDA enabled"

PyTorch esta instalado en version CPU pero el codigo intenta usar CUDA. Soluciones:
1. Reinstalar PyTorch con soporte CUDA (ver seccion 2: "Configurar PyTorch con GPU"):
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   ```
2. Verificar con: `python check_cuda.py`
   - Si dice `2.x.x+cpu` -> es la version CPU, necesitas reinstalar
   - Si dice `2.x.x+cu128` -> es la version CUDA, deberia funcionar

### "torch.cuda.is_available() devuelve False (pero tengo GPU NVIDIA)"

Posibles causas:
1. **PyTorch version CPU**: verifica con `pip list | findstr torch`. Si `torch` no tiene
   sufijo `+cuXXX`, reinstala con CUDA (ver seccion 2).
2. **Driver NVIDIA desactualizado**: ejecuta `nvidia-smi`. Si falla, instala/actualiza
   los drivers desde https://www.nvidia.com/drivers
3. **CUDA toolkit no compatible**: la version de CUDA de tu driver debe ser >= la version
   con la que se compilo PyTorch. Verifica con `nvidia-smi` (CUDA Version) y
   `python check_cuda.py` (CUDA de PyTorch).

### "El modelo de Whisper no se descarga"

- Verifica tu conexion a internet
- Los modelos se cachean en `~/.cache/whisper/`
- Si falla, puedes descargar manualmente desde:
  https://github.com/openai/whisper/blob/main/whisper/__init__.py
  (busca las URLs de los modelos)

---

## 5. Costos reales del proyecto

| Concepto | Costo mensual |
|---|---|
| Whisper local | $0 |
| Gemini API (tier gratuito) | $0 |
| ffmpeg | $0 |
| Python | $0 |
| **Total** | **$0** |

Comparacion con el stack anterior (OpenAI):

| Concepto | Costo anterior | Costo actual |
|---|---|---|
| Whisper API | ~$0.006/min (~$1.80/hr) | $0 (local) |
| GPT-4o API | ~$5-10/1M tokens | $0 (Gemini gratis) |
| Google Sheets API | $0 | Eliminado |
| **Total por 10 entrevistas/mes** | **~$5-15** | **$0** |

---

## 6. Posibles mejoras futuras

- [ ] Agregar diarizacion (identificar quien habla: reclutador vs candidato)
      Herramienta: pyannote-audio o whisperx
- [ ] Automatizar publicacion en LinkedIn con la API oficial
      Requiere: registrar app en LinkedIn Developers + OAuth 2.0
- [ ] Agregar base de datos SQLite para queries mas complejas
- [ ] Dashboard web para visualizar estadisticas de entrevistas
- [ ] Soporte para multiples idiomas (ingles, portugues)
- [ ] Integracion con calendario para programar posts automaticamente
