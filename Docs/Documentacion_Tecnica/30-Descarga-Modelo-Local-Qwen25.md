---
título: 30 - Descarga y Ejecución del Modelo Local (Qwen2.5-0.5B-Instruct-GGUF)
objetivo: Documentar el procedimiento para descargar y ejecutar localmente el modelo Qwen2.5-0.5B-Instruct-GGUF desde HuggingFace, como parte de la arquitectura híbrida (Opción C) decidida por el usuario. Sin escribir código de la aplicación ARGOS.
alcance: Origen `Docs/IA_Local_Descargar.md` (`https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF`). Metadatos del repo consultados en vivo el 2026-07-11 vía API de HuggingFace.
dependencias: 29-Arquitectura-IA-Hibrida.md; 21-Dependencias.md; 10-Configuracion-Local.md.
referencias: 08-API-Gateway.md; 09-Integracion-IA.md.
---

# 30 - Descarga y Ejecución del Modelo Local (Qwen2.5-0.5B-Instruct-GGUF)

> **Contexto.** Este documento acompaña la **Opción C (Híbrida)** del usuario (ver `29-Arquitectura-IA-Hibrida.md`). El modelo local se descarga a la máquina y se ejecuta con un runtime local OpenAI-compatible; **no** reemplaza la API Gateway.

## 1. Origen y metadatos (HuggingFace, consultado 2026-07-11)

| Campo | Valor |
|---|---|
| Repositorio | `Qwen/Qwen2.5-0.5B-Instruct-GGUF` |
| URL | `https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF` |
| Licencia | `apache-2.0` |
| Arquitectura | `qwen2` |
| Context length | `8192` tokens |
| Base model | `Qwen/Qwen2.5-0.5B-Instruct` |
| Gated | `false` (descarga libre) |
| fp16 (tamaño total) | ~1.18 GiB (`1266425696` bytes según `totalFileSize` del card) |
| q8_0 (aprox.) | ~601 MiB (`630167424` bytes según `total` del card) |

> El archivo fp16 completo pesa ~1.18 GiB. Las cuantizaciones reducen el tamaño (ver §2).

## 2. Archivos GGUF disponibles (siblings del repo)

El repositorio publica las siguientes variantes (consulta `siblings` de la API, 2026-07-11):

| Archivo | Cuantización | Uso recomendado |
|---|---|---|
| `qwen2.5-0.5b-instruct-fp16.gguf` | fp16 (sin cuantizar) | Máxima fidelidad; pesado (~1.18 GiB) |
| `qwen2.5-0.5b-instruct-q8_0.gguf` | q8_0 | Alta fidelidad; ~601 MiB |
| `qwen2.5-0.5b-instruct-q6_k.gguf` | q6_k | Muy buena calidad |
| `qwen2.5-0.5b-instruct-q5_k_m.gguf` | q5_k_m | Buena calidad |
| `qwen2.5-0.5b-instruct-q5_0.gguf` | q5_0 | Buena calidad |
| `qwen2.5-0.5b-instruct-q4_k_m.gguf` | q4_k_m | **Balance recomendado para SOC local** |
| `qwen2.5-0.5b-instruct-q4_0.gguf` | q4_0 | Ligero |
| `qwen2.5-0.5b-instruct-q3_k_m.gguf` | q3_k_m | Muy ligero |
| `qwen2.5-0.5b-instruct-q2_k.gguf` | q2_k | Mínimo |

> **Tamaños exactos por archivo no provistos por la API de HuggingFace** en la consulta realizada; los valores aproximados (q4_k_m ≈ 400–500 MB, q8_0 ≈ 601 MiB, fp16 ≈ 1.18 GiB) se derivan del card. Verificar el tamaño real tras la descarga (§5).

## 3. Selección de cuantización

- **Recomendado (por defecto):** `qwen2.5-0.5b-instruct-q4_k_m.gguf` — mejor balance tamaño/calidad para un modelo de 0.5B ejecutado localmente como fallback/privacy-guard.
- **Alternativas:** `q8_0` si hay disco/RAM holgados y se prefiere más fidelidad; `q2_k`/`q3_k_m` solo si el hardware es muy limitado.

## 4. Procedimiento de descarga

### 4.1 Destino en el repo

```
argos/
└── models/
    └── qwen25-0.5b-instruct-gguf/
        └── qwen2.5-0.5b-instruct-q4_k_m.gguf
```

### 4.2 Desde la CDN de HuggingFace

Patrón de URL de descarga directa:

```
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/<archivo>
```

Ejemplo (PowerShell):

```powershell
$dir = "C:\REPOSITORIOS\ARGOS\models\qwen25-0.5b-instruct-gguf"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$url = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
Invoke-WebRequest -Uri $url -OutFile "$dir\qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

> Alternativa con `curl.exe` (si está en PATH):
> `curl.exe -L -o models/qwen25-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"`

## 5. Verificación de integridad

- Comprobar tamaño del archivo descargado contra el esperado (~400–500 MB para q4_k_m).
- Calcular hash SHA256 y registrarlo para detectar corrupción:

```powershell
Get-FileHash -Algorithm SHA256 "models\qwen25-0.5b-instruct-gguf\qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

### 5.1 Registro de la descarga realizada (2026-07-11)

| Campo | Valor |
|---|---|
| Archivo | `qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Ruta | `models/qwen25-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Tamaño | `491400032` bytes (~468.6 MiB) |
| SHA256 | `74A4DA8C9FDBCD15BD1F6D01D621410D31C6FC00986F5EB687824E7B93D7A9DB` |
| Método | `curl.exe -L -C -` sobre CDN de HuggingFace (reanudado desde 182 MB parciales) |

> **Información no especificada en la documentación original.** HuggingFace no publica un hash SHA256 de referencia por archivo en la API consultada; la verificación se limita a tamaño y a re-descarga en caso de duda. No se documenta firma ni checksum oficial del GGUF. El SHA256 anterior es del archivo efectivamente descargado, no un valor de referencia del proveedor.

## 6. Ejecución local (runtime OpenAI-compatible)

> **Decisión de implementación híbrida (no en doc base).** El runtime local no figura en el documento maestro. Opciones compatibles con GGUF y servidor OpenAI-compatible:

| Runtime | Forma de servir |
|---|---|
| **llama.cpp** (`server`/`llama-server`) | binario `llama-server --model <ruta> --host 127.0.0.1 --port 8080` |
| **llama-cpp-python** (`server`) | `python -m llama_cpp.server --model <ruta> --host 127.0.0.1 --port 8080` |
| **Ollama** | `ollama create qwen25-0.5b -f Modelfile` + `ollama serve` (expone `/v1`) |
| **LM Studio** | GUI; servidor local OpenAI-compatible |

Esqueleto de arranque (llama.cpp):

```bash
llama-server \
  --model models/qwen25-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 --port 8080 --ctx-size 8192
```

El cliente ARGOS apunta a `base_url = http://127.0.0.1:8080/v1` (sin `Authorization`) para el canal local, reutilizando el SDK OpenAI del doc `09-Integracion-IA.md`.

## 7. Integración con el Router híbrido

- Mismo SDK OpenAI; solo cambia `base_url`.
- El **Router híbrido** (F3 en `29-Arquitectura-IA-Hibrida.md`) conmuta a `http://127.0.0.1:8080/v1` cuando el canal API Gateway falla o cuando la política de privacidad lo exige.
- El servidor local debe escuchar **exclusivamente en loopback** (`127.0.0.1`); no exponer el puerto a la red.

## 8. Variables de entorno sugeridas

| Variable | Valor sugerido | Propósito |
|---|---|---|
| `ARGOS_LLM_MODE` | `hybrid` (default) / `remote` / `local` | Selecciona canal |
| `ARGOS_LOCAL_MODEL_PATH` | `models/qwen25-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf` | Ruta al GGUF |
| `ARGOS_LOCAL_BASE_URL` | `http://127.0.0.1:8080/v1` | Endpoint local OpenAI-compatible |
| `KILO_API_KEY` | (existente) | API Gateway remoto |

> **Información no especificada en la documentación original.** Estos nombres de variables son propuesta de implementación híbrida; el doc base no define variables para modelo local.

## 9. Repositorio y `.gitignore`

- El GGUF es un binario grande; **no se commitea** salvo intención explícita.
- Añadir al `.gitignore` del repo:

```
models/**/*.gguf
```

- El repo `Docs/IA_Local_Descargar.md` conserva la URL origen como única fuente de descarga.

## 10. Información no especificada / decisión de implementación

- **Decisión de implementación (Opción C):** descarga y ejecución local del GGUF es extensión del usuario; no está en el documento maestro.
- **Información no especificada en la documentación original:** no se especifica runtime local concreto, puerto, umbrales de failover, ni hash oficial del GGUF. Todo lo anterior es propuesta documentada para la fase de implementación.
