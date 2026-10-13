"""
TurboTranscribe - Núcleo de Transcrição
Módulo responsável pela transcrição de áudio via API do Groq (Whisper Large V3 Turbo).
"""

import os
from pathlib import Path
from typing import Optional

import requests

# ─── Constantes ────────────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
RESPONSE_FORMAT = "verbose_json"
DEFAULT_LANGUAGE = "auto"
SUPPORTED_LANGUAGES = {"auto", "pt", "en", "es", "fr", "de", "it", "zh", "ja", "ko"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".opus", ".flac"}
ENV_FILE_PATH = Path("/opt/data/.env")
REQUEST_TIMEOUT = 120  # segundos


# ─── Exceções ─────────────────────────────────────────────────────────────────


class TranscriptionError(Exception):
    """Erro personalizado para falhas na transcrição."""


# ─── Funções de Validação ─────────────────────────────────────────────────────


def validate_audio_file(file_path: str) -> Path:
    """
    Valida se o arquivo de áudio existe e tem formato suportado.

    Args:
        file_path: Caminho do arquivo de áudio.

    Returns:
        Path validado.

    Raises:
        TranscriptionError: Se o arquivo não existir ou tiver formato inválido.
    """
    path = Path(file_path)

    if not path.exists():
        raise TranscriptionError(f"Arquivo não encontrado: {file_path}")

    if not path.is_file():
        raise TranscriptionError(f"Caminho não é um arquivo: {file_path}")

    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        formats = ", ".join(sorted(AUDIO_EXTENSIONS))
        raise TranscriptionError(
            f"Formato não suportado: '{path.suffix}'. Formatos aceitos: {formats}"
        )

    return path


def validate_language(language: str) -> str:
    """
    Valida e normaliza o código de idioma.

    Args:
        language: Código do idioma (ex: 'pt', 'en', 'auto').

    Returns:
        Código do idioma normalizado (minúsculas).

    Raises:
        TranscriptionError: Se o idioma não for suportado.
    """
    lang = language.strip().lower()

    if lang not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise TranscriptionError(
            f"Idioma não suportado: '{language}'. Idiomas aceitos: {supported}"
        )

    return lang


# ─── Funções de API ───────────────────────────────────────────────────────────


def load_api_key() -> str:
    """
    Carrega a chave da API do Groq do arquivo .env.

    Returns:
        Chave da API.

    Raises:
        TranscriptionError: Se a chave não for encontrada.
    """
    # Tenta variável de ambiente primeiro
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if api_key:
        return api_key

    # Tenta arquivo .env
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key:
                        return key

    raise TranscriptionError(
        "GROQ_API_KEY não configurada. Defina a variável de ambiente "
        "ou adicione GROQ_API_KEY ao arquivo /opt/data/.env"
    )


def build_request_data(language: str) -> dict:
    """
    Constrói os dados da requisição para a API do Groq.

    Args:
        language: Código do idioma (ou 'auto' para detecção automática).

    Returns:
        Dicionário com os dados da requisição.
    """
    data = {
        "model": GROQ_MODEL,
        "response_format": RESPONSE_FORMAT,
    }

    if language != DEFAULT_LANGUAGE:
        data["language"] = language

    return data


def send_transcription_request(
    file_path: Path,
    api_key: str,
    language: str,
) -> dict:
    """
    Envia o arquivo de áudio para a API do Groq.

    Args:
        file_path: Caminho do arquivo de áudio.
        api_key: Chave da API do Groq.
        language: Código do idioma.

    Returns:
        Resposta da API como dicionário.

    Raises:
        TranscriptionError: Se a requisição falhar.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    data = build_request_data(language)

    try:
        with open(file_path, "rb") as audio_file:
            files = {"file": (file_path.name, audio_file, "audio/mpeg")}
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=REQUEST_TIMEOUT,
            )
    except requests.exceptions.ConnectionError as e:
        raise TranscriptionError(
            f"Erro de conexão com a API do Groq: {e}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise TranscriptionError(
            f"Tempo limite excedido ({REQUEST_TIMEOUT}s) ao comunicar com a API"
        ) from e
    except OSError as e:
        raise TranscriptionError(
            f"Erro ao ler o arquivo de áudio: {e}"
        ) from e

    if response.status_code != 200:
        error_detail = ""
        try:
            error_json = response.json()
            error_detail = f" — {error_json.get('error', {}).get('message', '')}"
        except Exception:
            error_detail = f" — {response.text[:200]}"

        raise TranscriptionError(
            f"Erro na API do Groq (HTTP {response.status_code}){error_detail}"
        )

    try:
        return response.json()
    except ValueError as e:
        raise TranscriptionError(
            f"Resposta inválida da API: {e}"
        ) from e


# ─── Funções de Processamento ─────────────────────────────────────────────────


def parse_transcription_response(response: dict) -> dict:
    """
    Processa e valida a resposta da API, extraindo segmentos com timestamps.

    Args:
        response: Resposta JSON da API do Groq.

    Returns:
        Dicionário com 'text' (texto completo) e 'segments' (lista de segmentos
        com 'start', 'end' e 'text').

    Raises:
        TranscriptionError: Se a resposta não contiver dados válidos.
    """
    if not isinstance(response, dict):
        raise TranscriptionError("Resposta da API não é um dicionário válido")

    # Resposta sem segmentos (apenas texto)
    if "segments" not in response:
        text = response.get("text", "").strip()
        if not text:
            raise TranscriptionError("Resposta da API não contém texto transcrito")
        return {"text": text, "segments": []}

    # Resposta com segmentos
    raw_segments = response.get("segments", [])
    if not isinstance(raw_segments, list):
        raise TranscriptionError("Formato inválido: 'segments' não é uma lista")

    segments = []
    for i, seg in enumerate(raw_segments):
        if not isinstance(seg, dict):
            continue

        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        text = seg.get("text", "").strip()

        if text:
            segments.append({
                "start": float(start),
                "end": float(end),
                "text": text,
            })

    full_text = " ".join(s["text"] for s in segments)

    return {
        "text": full_text,
        "segments": segments,
        "language": response.get("language"),
        "duration": response.get("duration"),
    }


# ─── Função Principal ────────────────────────────────────────────────────────


def transcribe(
    file_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    """
    Transcreve um arquivo de áudio usando a API do Groq.

    Esta é a função principal do módulo. Ela valida o arquivo, carrega a
    chave da API, envia o áudio para transcrição e retorna os dados
    estruturados com timestamps.

    Args:
        file_path: Caminho do arquivo de áudio (mp3, wav, m4a, ogg, webm, opus, flac).
        language: Código do idioma ('pt', 'en', 'es', etc.) ou 'auto' para
                  detecção automática. Padrão: 'auto'.

    Returns:
        Dicionário com:
            - 'text': Texto completo da transcrição.
            - 'segments': Lista de segmentos, cada um com 'start', 'end' e 'text'.
            - 'language': Idioma detectado (se disponível).
            - 'duration': Duração do áudio em segundos (se disponível).

    Raises:
        TranscriptionError: Se qualquer etapa da transcrição falhar.

    Example:
        >>> resultado = transcribe("audio.mp3", language="pt")
        >>> print(resultado["text"])
        >>> for seg in resultado["segments"]:
        ...     print(f"[{seg['start']:.1f}s] {seg['text']}")
    """
    # Validações
    path = validate_audio_file(file_path)
    lang = validate_language(language)

    # Carrega chave da API
    api_key = load_api_key()

    # Envia requisição
    response = send_transcription_request(path, api_key, lang)

    # Processa resposta
    return parse_transcription_response(response)


# ─── Utilitários ──────────────────────────────────────────────────────────────


def format_timestamp(seconds: float, format: str = "srt") -> str:
    """
    Formata segundos em timestamp legível.

    Args:
        seconds: Tempo em segundos.
        format: Formato desejado — 'srt' (HH:MM:SS,mmm) ou 'txt' (HH:MM:SS).

    Returns:
        String formatada.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if format == "srt":
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_supported_languages() -> set:
    """
    Retorna o conjunto de idiomas suportados.

    Returns:
        Set com códigos de idioma (inclui 'auto').
    """
    return SUPPORTED_LANGUAGES.copy()


def get_supported_formats() -> set:
    """
    Retorna o conjunto de formatos de áudio suportados.

    Returns:
        Set com extensões de arquivo (inclui o ponto, ex: '.mp3').
    """
    return AUDIO_EXTENSIONS.copy()
