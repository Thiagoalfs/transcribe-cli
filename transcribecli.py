#!/usr/bin/env python3
"""
TranscribeCLI - Audio Transcription with Timestamps
Uses Whisper Large V3 Turbo via Groq API.
"""
import os
import sys
import time
import threading
from pathlib import Path

# Adicionar diretório atual ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

from transcribe_core import transcribe, TranscriptionError, get_supported_formats
from export_srt import export_srt
from export_txt import export_txt
from history import add_entry, list_entries, display_history_table

# ─── Constants ─────────────────────────────────────────────────────────────────

TRANSCRIPTS_DIR = Path(__file__).parent / "history"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


# ─── Utilities ────────────────────────────────────────────────────────────────

def clear_screen():
    """Clear the screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the header."""
    clear_screen()
    print("=" * 60)
    print("  TranscribeCLI - Audio Transcription with Timestamps")
    print("=" * 60)
    print()


def print_menu():
    """Print the main menu."""
    print("Options:")
    print("  1. Transcribe")
    print("  2. History")
    print("  0. Quit")
    print()


def get_choice(prompt, valid_choices):
    """Get a valid choice from the user."""
    while True:
        choice = input(prompt).strip()
        if choice in valid_choices:
            return choice
        print(f"Invalid option. Choose one of: {', '.join(valid_choices)}")


def select_file() -> str | None:
    """Open the file selector.
    
    Returns:
        Selected file path or None.
    """
    print("\nSelect an audio file...")
    print(f"Supported formats: {', '.join(sorted(get_supported_formats()))}")
    print()

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[
                ("Audio files", " ".join(f"*{ext}" for ext in get_supported_formats())),
                ("All files", "*.*")
            ]
        )
        root.destroy()
        return file_path if file_path else None
    except ImportError:
        file_path = input("File path: ").strip()
        return file_path if file_path else None


def animate_dots(stop_event):
    """Animate dots during transcription."""
    dots = 0
    while not stop_event.is_set():
        print(f"\rTranscribing{'.' * dots}   ", end="", flush=True)
        dots = (dots + 1) % 4
        time.sleep(0.5)


def format_time(seconds):
    """Format seconds to HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def group_segments_by_words(segments, words_per_group):
    """Group segments by word count.
    
    Args:
        segments: List of segments with start, end, text.
        words_per_group: Number of words per group.
    
    Returns:
        List of grouped segments.
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
    
    # Add remaining words
    if current_words:
        if current_end <= current_start:
            current_end = current_start + 0.01
        grouped.append({
            "start": current_start,
            "end": current_end,
            "text": " ".join(current_words)
        })
    
    # Fix all segments where start == end
    for seg in grouped:
        if seg["end"] <= seg["start"]:
            seg["end"] = seg["start"] + 0.01
    
    return grouped


def save_history_txt(result, file_path):
    """Save TXT to the history folder in the script directory."""
    base_name = Path(file_path).stem
    output_path = TRANSCRIPTS_DIR / f"{base_name}.txt"
    
    segments = result.get("segments", [])
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in segments:
            start = segment.get("start", 0)
            text = segment.get("text", "").strip()
            f.write(f"[{format_time(start)}] {text}\n")
    
    return output_path


def post_transcript_menu(result, file_path):
    """Post-transcription menu."""
    grouped_segments = result.get("segments", []) if result else []
    base_name = Path(file_path).stem
    
    while True:
        print("Options:")
        print("  1. Segment words")
        print("  2. Export SRT")
        print("  3. Export TXT")
        print("  0. Go to main menu")
        print()

        choice = get_choice("Choice: ", ["1", "2", "3", "0"])

        if choice == "1":
            # Segment words - SAME SCREEN
            clear_screen()
            print_header()
            print("Segment Words")
            print("=" * 60)
            print()
            
            # Show current preview
            if grouped_segments:
                print("Current segmentation:")
                for segment in grouped_segments:
                    start = segment.get("start", 0)
                    text = segment.get("text", "").strip()
                    print(f"[{format_time(start)}] {text}")
                print()
            
            while True:
                try:
                    words = int(input("Words per segment: ").strip())
                    if words <= 0:
                        print("Enter a number greater than zero.")
                        continue
                    break
                except ValueError:
                    print("Enter a valid number.")
            
            grouped_segments = group_segments_by_words(result["segments"], words)
            
            # Save updated TXT
            txt_path = TRANSCRIPTS_DIR / f"{base_name}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                for segment in grouped_segments:
                    start = segment.get("start", 0)
                    text = segment.get("text", "").strip()
                    f.write(f"[{format_time(start)}] {text}\n")
            
            # Return to point 3 (preview + options)
            clear_screen()
            print_header()
            print("Transcription Result")
            print("=" * 60)
            print()
            
            for segment in grouped_segments:
                start = segment.get("start", 0)
                text = segment.get("text", "").strip()
                print(f"[{format_time(start)}] {text}")
            
            print()
            continue
            
        elif choice == "2":
            if grouped_segments:
                output_path = TRANSCRIPTS_DIR / f"{base_name}.srt"
                export_srt(grouped_segments, output_path)
                print(f"SRT exported: {output_path}")
            else:
                print("Error: no data to export")
            input("\nPress Enter to continue...")
        elif choice == "3":
            if grouped_segments:
                output_path = TRANSCRIPTS_DIR / f"{base_name}.txt"
                export_txt(grouped_segments, output_path)
                print(f"TXT exported: {output_path}")
            else:
                print("Error: no data to export")
            input("\nPress Enter to continue...")
        elif choice == "0":
            break


def show_history() -> None:
    """Show transcription history."""
    clear_screen()
    print_header()
    print("Transcription History")
    print("=" * 60)
    print()

    entries = list_entries()
    if not entries:
        print("No transcriptions found.")
        input("\nPress Enter to continue...")
        return

    display_history_table(entries)
    print()

    # Allow selecting an item
    choice = input("Select a number to view details (or Enter to go back): ").strip()
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(entries):
            show_history_detail(entries[idx])
        else:
            print("Invalid number.")
            input("\nPress Enter to continue...")
    except ValueError:
        print("Invalid input.")
        input("\nPress Enter to continue...")


def show_history_detail(entry: dict) -> None:
    """Show transcription preview and options directly."""
    file_path = entry.get('file_path', '')
    base_name = Path(file_path).stem if file_path else ''
    txt_path = TRANSCRIPTS_DIR / f"{base_name}.txt"
    srt_path = TRANSCRIPTS_DIR / f"{base_name}.srt"

    if not txt_path.exists() and not srt_path.exists():
        clear_screen()
        print_header()
        print("Transcription files not found.")
        print("Transcribe again to generate the files.")
        input("\nPress Enter to continue...")
        return

    # Load segments from TXT or SRT
    segments = []
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and '] ' in line:
                    timestamp_end = line.index('] ')
                    timestamp = line[1:timestamp_end]
                    text = line[timestamp_end + 2:]
                    # Parse HH:MM:SS to seconds
                    parts = timestamp.split(':')
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    segments.append({"start": seconds, "end": seconds + 1, "text": text})

    while True:
        clear_screen()
        print_header()
        print("Transcription Preview")
        print("=" * 60)
        print()

        if segments:
            for segment in segments:
                start = segment.get("start", 0)
                text = segment.get("text", "").strip()
                print(f"[{format_time(start)}] {text}")
        else:
            print("No preview available.")

        print()
        print("Options:")
        print("  1. Segment words")
        print("  2. Export SRT")
        print("  3. Export TXT")
        print("  0. Go back")
        print()

        choice = get_choice("Choice: ", ["1", "2", "3", "0"])

        if choice == "1":
            while True:
                try:
                    words = int(input("Words per segment: ").strip())
                    if words <= 0:
                        print("Enter a number greater than zero.")
                        continue
                    break
                except ValueError:
                    print("Enter a valid number.")

            segments = group_segments_by_words(segments, words)

            # Save updated TXT
            with open(txt_path, 'w', encoding='utf-8') as f:
                for segment in segments:
                    start = segment.get("start", 0)
                    text = segment.get("text", "").strip()
                    f.write(f"[{format_time(start)}] {text}\n")
        elif choice == "2":
            if segments:
                export_srt(segments, srt_path)
                print(f"SRT exported: {srt_path}")
            else:
                print("Error: no data to export")
            input("\nPress Enter to continue...")
        elif choice == "3":
            if segments:
                export_txt(segments, txt_path)
                print(f"TXT exported: {txt_path}")
            else:
                print("Error: no data to export")
            input("\nPress Enter to continue...")
        elif choice == "0":
            return


def do_transcribe() -> None:
    """Transcription flow."""
    clear_screen()
    print_header()
    
    # Select file
    file_path = select_file()
    if not file_path:
        print("No file selected.")
        input("\nPress Enter to continue...")
        return

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        input("\nPress Enter to continue...")
        return

    # Validate file extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in get_supported_formats():
        print(f"Unsupported format: {ext}")
        print(f"Accepted formats: {', '.join(sorted(get_supported_formats()))}")
        input("\nPress Enter to continue...")
        return

    # Show selected file
    clear_screen()
    print_header()
    print(f"Selected file: {os.path.basename(file_path)}")
    print(f"Path: {file_path}")
    print()

    # Transcribe with animation
    print("Transcribing", end="", flush=True)
    stop_event = threading.Event()
    anim_thread = threading.Thread(target=animate_dots, args=(stop_event,))
    anim_thread.start()
    
    try:
        result = transcribe(file_path)
        stop_event.set()
        anim_thread.join()
        print("\rTranscribing... Done!    ")
    except TranscriptionError as e:
        stop_event.set()
        anim_thread.join()
        print(f"\nError: {e}")
        input("\nPress Enter to continue...")
        return

    if result:
        # Save TXT to history folder
        txt_path = save_history_txt(result, file_path)
        
        # Add to history
        filename = os.path.basename(file_path)
        duration = result.get("duration", 0)
        word_count = len(result.get("text", "").split())
        detected_lang = result.get("language", "auto")
        add_entry(filename, detected_lang, detected_lang, duration, word_count, file_path)

        # Show result + post-transcription menu
        clear_screen()
        print_header()
        print("Transcription Result")
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
        
        post_transcript_menu(result, file_path)
    else:
        print("Transcription failed.")
        input("\nPress Enter to continue...")


def main() -> None:
    """Main CLI loop."""
    while True:
        print_header()
        print_menu()

        choice = get_choice("Choice: ", ["1", "2", "0"])

        if choice == "1":
            do_transcribe()
        elif choice == "2":
            show_history()
        elif choice == "0":
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
