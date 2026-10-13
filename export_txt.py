"""Exportador de transcrições para formato TXT.

Converte dados de transcrição com timestamps em arquivo de texto simples,
com cada linha contendo o timestamp de início entre colchetes seguido do texto.
"""
from pathlib import Path
from models import Segment


OUTPUT_EXTENSION = ".txt"
ENCODING = "utf-8"
TIMESTAMP_FORMAT = "[{timestamp}] {text}"


def format_txt_time(seconds: float) -> str:
    """Formata segundos em timestamp TXT (HH:MM:SS).

    Args:
        seconds: Tempo em segundos, com parte decimal opcional.

    Returns:
        String no formato HH:MM:SS.

    Exemplo:
        >>> format_txt_time(61.5)
        '00:01:01'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


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
        if "start" not in segment:
            raise ValueError(f"Segmento {i} não possui campo 'start'")
        if segment["start"] < 0:
            raise ValueError(f"Segmento {i} contém timestamp negativo")


def generate_txt_content(segments: list[Segment]) -> str:
    """Gera o conteúdo TXT formatado a partir dos segmentos.

    Args:
        segments: Lista de segmentos de transcrição.

    Returns:
        Conteúdo formatado pronto para escrita em arquivo.
    """
    validate_segments(segments)

    lines: list[str] = []
    for segment in segments:
        timestamp = format_txt_time(segment["start"])
        text = segment.get("text", "").strip()
        lines.append(TIMESTAMP_FORMAT.format(timestamp=timestamp, text=text))

    return "\n".join(lines) + "\n"


def export_txt(segments: list[Segment], output_path: str | Path) -> Path:
    """Exporta segmentos de transcrição como arquivo TXT.

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
        >>> export_txt(segments, "transcricao.txt")
        PosixPath('transcricao.txt')
    """
    output = Path(output_path)

    if output.suffix != OUTPUT_EXTENSION:
        output = output.with_suffix(OUTPUT_EXTENSION)

    content = generate_txt_content(segments)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding=ENCODING)
    except OSError as e:
        raise OSError(f"Erro ao escrever arquivo '{output}': {e}") from e

    return output
