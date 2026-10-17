"""Modelos de dados compartilhados do TranscribeCLI."""
from typing import TypedDict


class Word(TypedDict):
    """Representa uma palavra individual com timestamps."""

    word: str
    start: float
    end: float


class SegmentRequired(TypedDict):
    """Campos obrigatórios de um segmento."""

    start: float
    end: float


class Segment(SegmentRequired, total=False):
    """Representa um segmento de transcrição com timestamps."""

    text: str
    words: list[Word]
