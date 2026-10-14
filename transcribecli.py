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


def group_words(segments, n):
    if not segments or n <= 0:
        return segments
    grouped = []
    words = []
    start = segments[0]["start"]
    end = segments[0]["end"]
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        for w in text.split():
            words.append(w)
            end = seg["end"]
            if len(words) >= n:
                grouped.append({"start": start, "end": end, "text": " ".join(words)})
                words = []
                start = end
    if words:
        if end <= start:
            end = start + 0.01
        grouped.append({"start": start, "end": end, "text": " ".join(words)})
    for g in grouped:
        if g["end"] <= g["start"]:
            g["end"] = g["start"] + 0.01
    return grouped


def save_txt(result, file_path):
    base = Path(file_path).stem
    path = TRANSCRIPTS_DIR / f"{base}.txt"
    with open(path, 'w', encoding='utf-8') as f:
        for seg in result.get("segments", []):
            f.write(f"[{fmt_time(seg.get('start', 0))}] {seg.get('text', '').strip()}\n")
    return path


def show_segments(segments):
    for seg in segments:
        print(f"[{fmt_time(seg.get('start', 0))}] {seg.get('text', '').strip()}")
    print()


def post_menu(result, file_path):
    segments = result.get("segments", []) if result else []
    base = Path(file_path).stem

    while True:
        clear()
        header()
        show_segments(segments)

        print("1. Segment words")
        print("2. Export SRT")
        print("3. Export TXT")
        print("0. Main menu")
        print()

        c = get_choice("> ", ["1", "2", "3", "0"])

        if c == "1":
            clear()
            header()
            show_segments(segments)
            while True:
                try:
                    n = int(input("Words per segment: ").strip())
                    if n > 0:
                        break
                    print("Enter a number > 0.")
                except ValueError:
                    print("Enter a valid number.")
            segments = group_words(result["segments"], n)
            with open(TRANSCRIPTS_DIR / f"{base}.txt", 'w', encoding='utf-8') as f:
                for seg in segments:
                    f.write(f"[{fmt_time(seg.get('start', 0))}] {seg.get('text', '').strip()}\n")
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
                export_txt(segments, p)
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

    if not txt_path.exists() and not srt_path.exists():
        clear()
        header()
        print("Files not found. Transcribe again.")
        input("\nPress Enter...")
        return

    segments = []
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and '] ' in line:
                    ts_end = line.index('] ')
                    ts = line[1:ts_end]
                    text = line[ts_end + 2:]
                    parts = ts.split(':')
                    secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    segments.append({"start": secs, "end": secs + 1, "text": text})

    while True:
        clear()
        header()
        show_segments(segments)

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
            segments = group_words(segments, n)
            with open(txt_path, 'w', encoding='utf-8') as f:
                for seg in segments:
                    f.write(f"[{fmt_time(seg.get('start', 0))}] {seg.get('text', '').strip()}\n")
        elif c == "2":
            if segments:
                export_srt(segments, srt_path)
                print(f"Saved: {srt_path}")
            else:
                print("No data.")
            input("\nPress Enter...")
        elif c == "3":
            if segments:
                export_txt(segments, txt_path)
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
        save_txt(result, file_path)
        filename = os.path.basename(file_path)
        duration = result.get("duration", 0)
        word_count = len(result.get("text", "").split())
        lang = result.get("language", "auto")
        add_entry(filename, lang, lang, duration, word_count, file_path)

        clear()
        header()
        if result.get("segments"):
            show_segments(result["segments"])
        else:
            print(result.get("text", ""))
            print()

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
