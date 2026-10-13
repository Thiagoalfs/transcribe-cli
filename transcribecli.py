#!/usr/bin/env python3
"""
TranscribeCLI - Sistema de Transcrição de Áudio com Timestamps
Usa Whisper Large V3 Turbo via Groq API.
"""
import os
import sys
from pathlib import Path

# Adicionar diretório atual ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

from transcribe_core import transcribe, TranscriptionError, get_supported_languages, get_supported_formats
from export_srt import export_srt
from export_txt import export_txt
from history import add_entry, list_entries, display_history_table, clear_history

# ─── Constantes ────────────────────────────────────────────────────────────────

TRANSCRIPTS_DIR = Path.home() / "Downloads" / "transcribercli"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

IDIOMAS = {
    "auto": "Detectar automaticamente",
    "pt": "Português",
    "en": "Inglês",
    "es": "Espanhol",
    "fr": "Francês",
    "de": "Alemão",
    "it": "Italiano",
    "zh": "Chinês",
    "ja": "Japonês",
    "ko": "Coreano",
}


# ─── Utilitários ──────────────────────────────────────────────────────────────

def clear_screen():
    """Limpa a tela."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Imprime o cabeçalho."""
    clear_screen()
    print("=" * 60)
    print("  TranscribeCLI - Transcrição de Áudio com Timestamps")
    print("=" * 60)
    print()


def print_menu():
    """Imprime o menu principal."""
    print("Opções:")
    print("  1. Transcrever")
    print("  2. Histórico")
    print("  3. Sair")
    print()


def get_choice(prompt, valid_choices):
    """Obtém uma escolha válida do usuário."""
    while True:
        choice = input(prompt).strip()
        if choice in valid_choices:
            return choice
        print(f"Opção inválida. Escolha uma de: {', '.join(valid_choices)}")


def select_file():
    """Abre o seletor de arquivo."""
    print("\nSelecione um arquivo de áudio...")
    print(f"Formatos suportados: {', '.join(sorted(get_supported_formats()))}")
    print()

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Selecione um arquivo de áudio",
            filetypes=[
                ("Arquivos de áudio", " ".join(f"*{ext}" for ext in get_supported_formats())),
                ("Todos os arquivos", "*.*")
            ]
        )
        root.destroy()
        return file_path if file_path else None
    except ImportError:
        file_path = input("Caminho do arquivo: ").strip()
        return file_path if file_path else None


def select_language(prompt, default="auto"):
    """Seleciona um idioma."""
    print(f"\n{prompt}")
    for code, name in IDIOMAS.items():
        print(f"  {code:<6} - {name}")
    print()

    lang = input(f"Idioma [{default}]: ").strip().lower()
    return lang if lang else default


def display_transcript(result):
    """Exibe o resultado da transcrição."""
    if not result:
        return

    print("\n" + "=" * 60)
    print("  Resultado da Transcrição")
    print("=" * 60)
    print()

    if result.get("segments"):
        for segment in result["segments"]:
            start = segment.get("start", 0)
            text = segment.get("text", "").strip()
            print(f"[{format_time(start)}] {text}")
    else:
        print(result.get("text", ""))

    print()


def format_time(seconds):
    """Formata segundos em HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def group_segments_by_words(segments, words_per_group):
    """Agrupa segmentos por quantidade de palavras.
    
    Args:
        segments: Lista de segmentos com start, end, text.
        words_per_group: Quantidade de palavras por grupo.
    
    Returns:
        Lista de segmentos agrupados.
    """
    if not segments or words_per_group <= 0:
        return segments
    
    grouped = []
    current_words = []
    current_start = segments[0]["start"]
    current_end = segments[0]["end"]
    
    for segment in segments:
        text = segment.get("text", "").strip()
        if not text:
            continue
        
        words = text.split()
        for word in words:
            current_words.append(word)
            current_end = segment["end"]
            
            if len(current_words) >= words_per_group:
                grouped.append({
                    "start": current_start,
                    "end": current_end,
                    "text": " ".join(current_words)
                })
                current_words = []
                current_start = current_end
    
    # Adicionar palavras restantes
    if current_words:
        grouped.append({
            "start": current_start,
            "end": current_end,
            "text": " ".join(current_words)
        })
    
    return grouped


def display_grouped_preview(grouped_segments):
    """Exibe preview da transcrição agrupada."""
    print("\n" + "=" * 60)
    print("  Preview da Transcrição Agrupada")
    print("=" * 60)
    print()
    
    for segment in grouped_segments:
        start = segment.get("start", 0)
        text = segment.get("text", "").strip()
        print(f"[{format_time(start)}] {text}")
    
    print()


def post_transcript_menu(result, source_lang, target_lang, file_path):
    """Menu pós-transcrição."""
    grouped_segments = result.get("segments", []) if result else []
    
    while True:
        print("Opções:")
        print("  1. Configurar palavras por timestamp")
        print("  2. Exportar SRT")
        print("  3. Exportar TXT")
        print("  4. Voltar ao menu principal")
        print()

        choice = get_choice("Escolha: ", ["1", "2", "3", "4"])

        if choice == "1":
            words = int(input("Quantas palavras por timestamp? ").strip())
            grouped_segments = group_segments_by_words(result["segments"], words)
            display_grouped_preview(grouped_segments)
            print(f"Configurado: {words} palavras por timestamp")
        elif choice == "2":
            if grouped_segments:
                output_path = TRANSCRIPTS_DIR / "transcript.srt"
                export_srt(grouped_segments, output_path)
                print(f"SRT exportado: {output_path}")
            else:
                print("Erro: sem dados para exportar")
        elif choice == "3":
            if grouped_segments:
                output_path = TRANSCRIPTS_DIR / "transcript.txt"
                export_txt(grouped_segments, output_path)
                print(f"TXT exportado: {output_path}")
            else:
                print("Erro: sem dados para exportar")
        elif choice == "4":
            break


def show_history():
    """Mostra o histórico de transcrições."""
    print("\n" + "=" * 100)
    print("  Histórico de Transcrições")
    print("=" * 100)
    print()

    entries = list_entries()
    if not entries:
        print("Nenhuma transcrição encontrada.")
        return

    display_history_table(entries)
    print()


def do_transcribe():
    """Fluxo de transcrição."""
    # Selecionar arquivo
    file_path = select_file()
    if not file_path:
        print("Nenhum arquivo selecionado.")
        input("\nPressione Enter para continuar...")
        return

    if not os.path.exists(file_path):
        print(f"Arquivo não encontrado: {file_path}")
        input("\nPressione Enter para continuar...")
        return

    # Selecionar idiomas
    source_lang = select_language("Idioma de origem:")
    target_lang = select_language("Idioma de saída (deixe igual para não traduzir):")

    # Transcrever
    print("\nTranscrevendo...")
    try:
        result = transcribe(file_path, source_lang)
    except TranscriptionError as e:
        print(f"Erro: {e}")
        input("\nPressione Enter para continuar...")
        return

    if result:
        display_transcript(result)

        # Adicionar ao histórico
        filename = os.path.basename(file_path)
        duration = result.get("duration", 0)
        word_count = len(result.get("text", "").split())
        add_entry(filename, source_lang, target_lang, duration, word_count, file_path)

        post_transcript_menu(result, source_lang, target_lang, file_path)
    else:
        print("Falha na transcrição.")
        input("\nPressione Enter para continuar...")


def main():
    """Loop principal da CLI."""
    while True:
        print_header()
        print_menu()

        choice = get_choice("Escolha: ", ["1", "2", "3"])

        if choice == "1":
            do_transcribe()
        elif choice == "2":
            show_history()
            input("\nPressione Enter para continuar...")
        elif choice == "3":
            print("\nAté logo!")
            break


if __name__ == "__main__":
    main()
