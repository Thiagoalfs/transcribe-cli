"""Exportador de transcrições para formato SRT.

Converte dados de transcrição com timestamps em arquivos de legenda SRT
(SubRip), amplamente utilizado em players de vídeo e editores.
"""
from pathlib import Path
from typing import TypedDict


class SegmentRequired(TypedDict):
    """Campos obrigatórios de um segmento."""

    start: float
    end: float


class Segment(SegmentRequired, total=False):
    """Representa um segmento de transcrição com timestamps."""

    text: str


OUTPUT_EXTENSION = ".srt"
ENCODING = "utf-8"


def format_srt_time(seconds: float) -> str:
    """Formata segundos em timestamp SRT (HH:MM:SS,mmm).

    Args:
        seconds: Tempo em segundos, com parte decimal opcional.

    Returns:
        String no formato HH:MM:SS,mmm.

    Exemplo:
        >>> format_srt_time(61.5)
        '00:01:01,500'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds % 1) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def validate_segments(segments: list[Segment]) -> None:
    """Valida a lista de segmentos antes da exportação.

    Args:
        segments: Lista de segmentos a validar.

    Raises:
        ValueError: Se a lista estiver vazia ou contiver segmentos inválidos.
    """
    if not segments:
        raise ValueError("A lista de segmentos está vazia")

    for i, segment in enumerate(segments):
        if "start" not in segment or "end" not in segment:
            raise ValueError(f"Segmento {i} não possui campos 'start' ou 'end'")
        if segment["start"] < 0 or segment["end"] < 0:
            raise ValueError(f"Segmento {i} contém timestamps negativos")
        if segment["start"] >= segment["end"]:
            raise ValueError(
                f"Segmento {i}: 'start' ({segment['start']}) "
                f"deve ser menor que 'end' ({segment['end']})"
            )


def generate_srt_content(segments: list[Segment]) -> str:
    """Gera o conteúdo SRT formatado a partir dos segmentos.

    Args:
        segments: Lista de segmentos de transcrição.

    Returns:
        Conteúdo formatado pronto para escrita em arquivo.
    """
    validate_segments(segments)

    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start_time = format_srt_time(segment["start"])
        end_time = format_srt_time(segment["end"])
        text = segment.get("text", "").strip()

        lines.append(str(index))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def export_srt(segments: list[Segment], output_path: str | Path) -> Path:
    """Exporta segmentos de transcrição como arquivo SRT.

    Args:
        segments: Lista de segmentos, cada um com 'start', 'end' e 'text'.
        output_path: Caminho do arquivo de saída.

    Returns:
        Caminho do arquivo criado.

    Raises:
        ValueError: Se os segmentos forem inválidos.
        OSError: Se não for possível escrever o arquivo.

    Exemplo:
        >>> segments = [{"start": 0.0, "end": 1.5, "text": "Olá mundo"}]
        >>> export_srt(segments, "legenda.srt")
        PosixPath('legenda.srt')
    """
    output = Path(output_path)

    if output.suffix != OUTPUT_EXTENSION:
        output = output.with_suffix(OUTPUT_EXTENSION)

    content = generate_srt_content(segments)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding=ENCODING)
    except OSError as e:
        raise OSError(f"Erro ao escrever arquivo '{output}': {e}") from e

    return output
