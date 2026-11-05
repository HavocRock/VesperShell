"""Offline read-only Unicode diagnostic. Prints no note contents."""
from __future__ import annotations
import argparse
from pathlib import Path
from vespershell.model import NotesDataError, NotesStore


def main():
    parser = argparse.ArgumentParser(description="Check saved note text for Unicode replacement characters")
    parser.add_argument("notes_json", type=Path, help="Path to the saved notes.json file")
    args = parser.parse_args()
    try:
        notes = NotesStore(args.notes_json).load()
    except NotesDataError as exc:
        print("Unable to inspect notes safely:", exc)
        return 1
    bad = [(i + 1, n["text"].count("\ufffd")) for i, n in enumerate(notes) if "\ufffd" in n["text"]]
    print(f"Checked {len(notes)} notes. The text itself is NOT printed.")
    if bad:
        print(f"Possible character replacement in {len(bad)} note(s):")
        for index, num in bad:
            print(f"  Note {index}: {num} replacement character(s)")
        print("Those characters are already present in saved text. Font changes cannot restore them.")
        return 2
    print("No U+FFFD replacement characters found in saved text.")
    print("If Hindi still appears incorrect on screen, investigate font choice and shaping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
