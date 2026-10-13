"""Modelos de dados compartilhados do TranscribeCLI."""
from typing import TypedDict


class SegmentRequired(TypedDict):
    """Campos obrigatórios de um segmento."""

    start: float
    end: float


class Segment(SegmentRequired, total=False):
    """Representa um segmento de transcrição com timestamps."""

    text: str
