"""
Módulo de histórico de transcrições do TurboTranscribe.

Armazena metadados de cada transcrição em ~/.turbotranscribe/history.json
e fornece funções para adicionar, listar, consultar, remover e limpar entradas.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Constantes
HISTORY_DIR = Path.home() / ".turbotranscribe"
HISTORY_FILE = HISTORY_DIR / "history.json"


def _ensure_history_dir() -> None:
    """Garante que o diretório de histórico existe."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_history() -> list:
    """Carrega o histórico do arquivo JSON.

    Returns:
        Lista de entradas do histórico. Lista vazia se o arquivo não existir.
    """
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(entries: list) -> None:
    """Salva o histórico no arquivo JSON.

    Args:
        entries: Lista de entradas a serem salvas.
    """
    _ensure_history_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def add_entry(
    filename: str,
    source_language: str,
    target_language: str,
    duration: float,
    word_count: int,
    file_path: str,
) -> dict:
    """Adiciona uma nova entrada ao histórico.

    Args:
        filename: Nome do arquivo de áudio.
        source_language: Idioma de origem da transcrição.
        target_language: Idioma de destino (tradução).
        duration: Duração do áudio em segundos.
        word_count: Quantidade de palavras na transcrição.
        file_path: Caminho completo do arquivo de áudio.

    Returns:
        A entrada criada com id e data preenchidos.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "date": datetime.now().isoformat(),
        "filename": filename,
        "source_language": source_language,
        "target_language": target_language,
        "duration": duration,
        "word_count": word_count,
        "file_path": file_path,
    }

    entries = _load_history()
    entries.append(entry)
    _save_history(entries)

    return entry


def list_entries() -> list:
    """Lista todas as entradas do histórico.

    Returns:
        Lista de entradas, ordenadas da mais recente para a mais antiga.
    """
    entries = _load_history()
    return sorted(entries, key=lambda e: e.get("date", ""), reverse=True)


def get_entry(entry_id: str) -> Optional[dict]:
    """Busca uma entrada pelo ID.

    Args:
        entry_id: Identificador único da entrada.

    Returns:
        A entrada encontrada, ou None se não existir.
    """
    entries = _load_history()
    for entry in entries:
        if entry.get("id") == entry_id:
            return entry
    return None


def delete_entry(entry_id: str) -> bool:
    """Remove uma entrada do histórico.

    Args:
        entry_id: Identificador único da entrada a remover.

    Returns:
        True se a entrada foi removida, False caso contrário.
    """
    entries = _load_history()
    original_len = len(entries)
    entries = [e for e in entries if e.get("id") != entry_id]

    if len(entries) == original_len:
        return False

    _save_history(entries)
    return True


def clear_history() -> int:
    """Remove todas as entradas do histórico.

    Returns:
        Número de entradas removidas.
    """
    entries = _load_history()
    count = len(entries)
    _save_history([])
    return count


def display_history_table(entries: Optional[list] = None) -> None:
    """Exibe o histórico em formato de tabela.

    Args:
        entries: Lista de entradas a exibir. Se None, carrega do arquivo.
    """
    if entries is None:
        entries = list_entries()

    if not entries:
        print("Nenhuma transcrição no histórico.")
        return

    # Cabeçalho
    print()
    print("=" * 100)
    print("  Histórico de Transcrições")
    print("=" * 100)
    print()

    # Colunas
    header = (
        f"{'#':<4} "
        f"{'Data':<20} "
        f"{'Arquivo':<25} "
        f"{'Origem':<8} "
        f"{'Destino':<8} "
        f"{'Duração':<10} "
        f"{'Palavras':<10}"
    )
    print(header)
    print("-" * 100)

    # Linhas
    for i, entry in enumerate(entries, 1):
        date_str = entry.get("date", "N/A")[:19].replace("T", " ")
        filename = entry.get("filename", "N/A")[:24]
        source_lang = entry.get("source_language", "N/A")[:7]
        target_lang = entry.get("target_language", "N/A")[:7]
        duration = entry.get("duration", 0)
        word_count = entry.get("word_count", 0)

        # Formata duração em minutos:segundos
        mins = int(duration // 60)
        secs = int(duration % 60)
        duration_str = f"{mins}:{secs:02d}"

        row = (
            f"{i:<4} "
            f"{date_str:<20} "
            f"{filename:<25} "
            f"{source_lang:<8} "
            f"{target_lang:<8} "
            f"{duration_str:<10} "
            f"{word_count:<10}"
        )
        print(row)

    print("-" * 100)
    print(f"  Total: {len(entries)} transcrições")
    print()
