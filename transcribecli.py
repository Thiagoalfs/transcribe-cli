#!/usr/bin/env python3
"""
TranscribeCLI - Audio Transcription with Timestamps
Uses Whisper Large V3 Turbo via Groq API.
"""
import os
import sys
import json
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from transcribe_core import transcribe, TranscriptionError, get_supported_formats
from export_srt import export_srt
from export_txt import export_txt
from history import add_entry, list_entries, display_history_table

TRANSCRIPTS_DIR = Path(__file__).parent / "history"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def header():
    clear()
    print("─" * 50)
    print("  TranscribeCLI")
    print("─" * 50)
    print()


def menu():
    print("1. Transcribe")
    print("2. History")
    print("0. Quit")
    print()


def get_choice(prompt, valid):
    while True:
        c = input(prompt).strip()
        if c in valid:
            return c
        print(f"Invalid. Choose: {', '.join(valid)}")


def select_file():
    print("Select an audio file...")
    print(f"Formats: {', '.join(sorted(get_supported_formats()))}\n")
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio", " ".join(f"*{e}" for e in get_supported_formats())), ("All", "*.*")]
        )
        root.destroy()
        return path if path else None
    except ImportError:
        return input("File path: ").strip() or None


def animate(stop):
    dots = 0
    while not stop.is_set():
        print(f"\rTranscribing{'.' * dots}   ", end="", flush=True)
        dots = (dots + 1) % 4
        time.sleep(0.5)


def fmt_time(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def group_words_from_words(words: list, n: int) -> list:
    """Agrupa palavras individuais com base nos timestamps reais da IA."""
    if not words or n <= 0:
        return []
    grouped = []
    for i in range(0, len(words), n):
        chunk = words[i : i + n]
        if not chunk:
            continue
        start = float(chunk[0]["start"])
        end = float(chunk[-1]["end"])
        if end <= start:
            end = round(start + 0.1, 3)
        text = " ".join(w["word"].strip() for w in chunk).strip()
        grouped.append({"start": start, "end": end, "text": text})
    return grouped


def group_words_fallback(segments: list, n: int) -> list:
    """Interpola o tempo proporcionalmente quando não há timestamps por palavra."""
    if not segments or n <= 0:
        return segments
    grouped = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        words = text.split()
        if not words:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 1.0))
        total_duration = max(0.1, end - start)
        total_words = len(words)

        chunks = [words[i : i + n] for i in range(0, total_words, n)]
        accum = 0
        for chunk in chunks:
            chunk_start = start + (accum / total_words) * total_duration
            accum += len(chunk)
            chunk_end = start + (accum / total_words) * total_duration
            if chunk_end <= chunk_start:
                chunk_end = chunk_start + 0.1
            grouped.append({
                "start": round(chunk_start, 3),
                "end": round(chunk_end, 3),
                "text": " ".join(chunk),
            })
    return grouped


def group_words(data, n: int) -> list:
    """Agrupa palavras em blocos de n palavras garantindo timestamps precisos."""
    if isinstance(data, dict):
        words = data.get("words", [])
        if words:
            return group_words_from_words(words, n)
        return group_words_fallback(data.get("segments", []), n)
    elif isinstance(data, list):
        if data and isinstance(data[0], dict) and "word" in data[0]:
            return group_words_from_words(data, n)
        return group_words_fallback(data, n)
    return []


def save_json(result: dict, file_path: str) -> Path:
    """Salva os dados completos da transcrição (incluindo words) em JSON."""
    base = Path(file_path).stem
    path = TRANSCRIPTS_DIR / f"{base}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path


def save_txt(data, file_path: str, full_text: str | None = None) -> Path:
    base = Path(file_path).stem
    path = TRANSCRIPTS_DIR / f"{base}.txt"
    segments = data.get("segments", []) if isinstance(data, dict) else data
    if full_text is None and isinstance(data, dict):
        full_text = data.get("text")
    export_txt(segments, path, full_text=full_text)
    return path


def show_segments(segments, full_text: str | None = None):
    if not segments and not full_text:
        return

    import shutil
    import textwrap

    term_width = shutil.get_terminal_size((80, 24)).columns
    max_w = max(40, min(term_width - 4, 100))

    if not full_text and segments:
        full_text = " ".join(s.get("text", "").strip() for s in segments if s.get("text"))

    if full_text:
        print("--- Transcricao ---")
        for line in textwrap.wrap(full_text.strip(), width=max_w):
            print(f"  {line}")
        print()

    if segments:
        print("--- Segmentos (Inline) ---")
        inline_items = []
        for seg in segments:
            t = seg.get("text", "").strip()
            if t:
                inline_items.append(f"[{fmt_time(seg.get('start', 0))}] {t}")

        inline_str = "  ".join(inline_items)
        for line in textwrap.wrap(inline_str, width=max_w):
            print(f"  {line}")
        print()


def post_menu(result, file_path):
    segments = result.get("segments", []) if result else []
    words = result.get("words", []) if result else []
    full_text = result.get("text", "") if result else ""
    base = Path(file_path).stem

    while True:
        clear()
        header()
        show_segments(segments, full_text=full_text)

        print("1. Segment words")
        print("2. Export SRT")
        print("3. Export TXT")
        print("0. Main menu")
        print()

        c = get_choice("> ", ["1", "2", "3", "0"])

        if c == "1":
            clear()
            header()
            show_segments(segments, full_text=full_text)
            while True:
                try:
                    n = int(input("Words per segment: ").strip())
                    if n > 0:
                        break
                    print("Enter a number > 0.")
                except ValueError:
                    print("Enter a valid number.")
            if words:
                segments = group_words_from_words(words, n)
            else:
                base_segs = result.get("segments", segments)
                segments = group_words_fallback(base_segs, n)

            save_txt(segments, file_path, full_text=full_text)
            export_srt(segments, TRANSCRIPTS_DIR / f"{base}.srt")
            print(f"\nLegendas reagrupadas em blocos de {n} palavras!")
            time.sleep(1)
        elif c == "2":
            if segments:
                p = TRANSCRIPTS_DIR / f"{base}.srt"
                export_srt(segments, p)
                print(f"Saved: {p}")
            else:
                print("No data.")
            input("\nPress Enter...")
        elif c == "3":
            if segments:
                p = TRANSCRIPTS_DIR / f"{base}.txt"
                export_txt(segments, p, full_text=full_text)
                print(f"Saved: {p}")
            else:
                print("No data.")
            input("\nPress Enter...")
        elif c == "0":
            break




def show_history():
    clear()
    header()
    entries = list_entries()
    if not entries:
        print("No transcriptions found.")
        input("\nPress Enter...")
        return

    display_history_table(entries)
    print()
    c = input("Select number (Enter to go back): ").strip()
    if not c:
        return
    try:
        idx = int(c) - 1
        if 0 <= idx < len(entries):
            show_detail(entries[idx])
        else:
            print("Invalid number.")
            input("\nPress Enter...")
    except ValueError:
        print("Invalid input.")
        input("\nPress Enter...")


def show_detail(entry):
    fp = entry.get('file_path', '')
    base = Path(fp).stem if fp else ''
    txt_path = TRANSCRIPTS_DIR / f"{base}.txt"
    srt_path = TRANSCRIPTS_DIR / f"{base}.srt"
    json_path = TRANSCRIPTS_DIR / f"{base}.json"

    if not txt_path.exists() and not srt_path.exists() and not json_path.exists():
        clear()
        header()
        print("Files not found. Transcribe again.")
        input("\nPress Enter...")
        return

    result = {}
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
        except Exception:
            result = {}

    words = result.get("words", [])
    segments = result.get("segments", [])
    full_text = result.get("text", "")

    if not segments:
        if srt_path.exists():
            try:
                with open(srt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                blocks = content.strip().split('\n\n')
                for block in blocks:
                    lines = block.strip().split('\n')
                    if len(lines) >= 3 and ' --> ' in lines[1]:
                        times = lines[1].split(' --> ')
                        def parse_srt_ts(t):
                            t = t.strip().replace(',', '.')
                            p = t.split(':')
                            return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
                        start_sec = parse_srt_ts(times[0])
                        end_sec = parse_srt_ts(times[1])
                        txt = "\n".join(lines[2:])
                        segments.append({"start": start_sec, "end": end_sec, "text": txt})
            except Exception:
                segments = []

        if not segments and txt_path.exists():
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    raw_txt = f.read()
                import re
                matches = re.findall(r'\[(\d{2}:\d{2}:\d{2})\]\s*([^\[\n\r]+)', raw_txt)
                for ts, text in matches:
                    parts = ts.split(':')
                    secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    segments.append({"start": float(secs), "end": float(secs + 2), "text": text.strip()})
            except Exception:
                segments = []

    if not full_text and segments:
        full_text = " ".join(s.get("text", "").strip() for s in segments if s.get("text"))

    while True:
        clear()
        header()
        show_segments(segments, full_text=full_text)

        print("1. Segment words")
        print("2. Export SRT")
        print("3. Export TXT")
        print("0. Go back")
        print()

        c = get_choice("> ", ["1", "2", "3", "0"])

        if c == "1":
            while True:
                try:
                    n = int(input("Words per segment: ").strip())
                    if n > 0:
                        break
                    print("Enter a number > 0.")
                except ValueError:
                    print("Enter a valid number.")
            if words:
                segments = group_words_from_words(words, n)
            else:
                base_segs = result.get("segments", segments)
                segments = group_words_fallback(base_segs, n)

            save_txt(segments, fp, full_text=full_text)
            if segments:
                export_srt(segments, srt_path)
            print(f"\nLegendas reagrupadas em blocos de {n} palavras!")
            time.sleep(1)
        elif c == "2":
            if segments:
                export_srt(segments, srt_path)
                print(f"Saved: {srt_path}")
            else:
                print("No data.")
            input("\nPress Enter...")
        elif c == "3":
            if segments:
                export_txt(segments, txt_path, full_text=full_text)
                print(f"Saved: {txt_path}")
            else:
                print("No data.")
            input("\nPress Enter...")
        elif c == "0":
            return


def do_transcribe():
    clear()
    header()
    file_path = select_file()
    if not file_path:
        print("No file selected.")
        input("\nPress Enter...")
        return

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        input("\nPress Enter...")
        return

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in get_supported_formats():
        print(f"Unsupported: {ext}")
        print(f"Accepted: {', '.join(sorted(get_supported_formats()))}")
        input("\nPress Enter...")
        return

    clear()
    header()
    print(f"File: {os.path.basename(file_path)}\n")

    stop = threading.Event()
    t = threading.Thread(target=animate, args=(stop,))
    t.start()

    try:
        result = transcribe(file_path)
        stop.set()
        t.join()
        print("\rTranscribing... Done!    ")
    except TranscriptionError as e:
        stop.set()
        t.join()
        print(f"\nError: {e}")
        input("\nPress Enter...")
        return

    if result:
        save_json(result, file_path)
        save_txt(result, file_path)
        base = Path(file_path).stem
        if result.get("segments"):
            export_srt(result["segments"], TRANSCRIPTS_DIR / f"{base}.srt")
        filename = os.path.basename(file_path)
        duration = result.get("duration", 0)
        word_count = len(result.get("text", "").split())
        lang = result.get("language", "auto")
        add_entry(filename, lang, lang, duration, word_count, file_path)

        post_menu(result, file_path)

    else:
        print("Transcription failed.")
        input("\nPress Enter...")


def main():
    while True:
        clear()
        header()
        menu()
        c = get_choice("> ", ["1", "2", "0"])
        if c == "1":
            do_transcribe()
        elif c == "2":
            show_history()
        elif c == "0":
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()
