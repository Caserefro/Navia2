#!/usr/bin/env python3
import queue
import re
import subprocess
import threading
import time
from Command import *
from fuzzywuzzy import fuzz

# ---------- CONFIG ----------
WAKE = "navia"
WAKE_FUZZ_THRESHOLD = 72
WAKE_COOLDOWN_S = 1.0

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def parse_number(txt: str):
    if not txt:
        return None
    txt = txt.replace(",", ".")
    try:
        return float(txt) if "." in txt else int(txt)
    except:
        return None


# ---------------------------------------------------------
# REGEX COMMAND MATCHER
# ---------------------------------------------------------
def match_pattern_command(text):
    t = text.lower()
    for (pattern, cmd, opts) in PATTERNS:
        m = pattern.search(t)
        if not m:
            continue

        g = m.groupdict()

        value = parse_number(g.get("value"))
        unit = g.get("unit")
        sign = g.get("sign")

        params = {}

        # Distance commands
        if "default_m" in opts:
            params["meters"] = value if value is not None else opts["default_m"]

        # Rotation commands
        if "default_deg" in opts:
            deg = value if value is not None else opts["default_deg"]
            if sign in ("izquierda", "izq"):
                deg = +abs(deg)
            elif sign in ("derecha", "der"):
                deg = -abs(deg)
            params["degrees"] = deg

        # Time-based commands
        if "default_s" in opts:
            params["seconds"] = value if value is not None else opts["default_s"]

        # Speed setting
        if "default_pct" in opts:
            params["percent"] = value if value is not None else opts["default_pct"]

        # Waypoint
        if "default_id" in opts:
            params["id"] = value

        return cmd, params

    return None, None

# ---------------------------------------------------------
# FUZZY MATCHING
# ---------------------------------------------------------
def fuzzy_match_command(text, threshold=70):
    text = text.lower()
    best_cmd = None
    best_score = 0

    for cmd, phrases in COMMAND_PHRASES.items():
        for p in phrases:
            score = fuzz.partial_ratio(text, p.lower())
            if score > best_score:
                best_score = score
                best_cmd = cmd

    if best_score >= threshold:
        return best_cmd
    return None


# ---------------------------------------------------------
# COMBINED COMMAND RECOGNIZER
# ---------------------------------------------------------
def recognize_command(text):
    text = normalize_text(text)

    # 1) Structured pattern rules
    cmd, params = match_pattern_command(text)
    if cmd:
        return cmd, params

    # 2) Fuzzy matching
    cmd = fuzzy_match_command(text)
    if cmd:
        return cmd, {}

    return None, None


# ---------------------------------------------------------
# WHISPER READER
# ---------------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
BRACKET_ONLY = re.compile(r"^\[(.*?)\]$")

def is_noise(text):
    clean = (
        text.lower()
        .replace(".", "")
        .replace("!", "")
        .replace("?", "")
        .strip()
    )
    return clean in NOISE_WORDS


def reader_thread(proc, q):
    for raw in proc.stdout:
        # Remove ANSI escape codes
        line = ANSI_RE.sub("", raw).strip()

        if not line or line in ("\r", "\n"):
            continue

        # Extract inner content from [ ... ]
        m = BRACKET_ONLY.match(line)
        if m:
            line = m.group(1).strip()

        # Skip noise words like "Música", "Risa", etc.
        if is_noise(line):
            # print for debug (optional)
            # print(f"[WHISPER-IGNORED NOISE]: {line}")
            continue

        # Deliver clean line to main thread
        q.put(line)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    whisper_cmd = [
        "/home/pi/Downloads/whisper.cpp/build/bin/whisper-stream",
        "-m", "/home/pi/Downloads/whisper.cpp/models/ggml-base-q5_1.bin",
        "--language", "es",
        "-t", "6",
        "-ac", "512",
    ]

    proc = subprocess.Popen(
        whisper_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    audio_q = queue.Queue()
    threading.Thread(target=reader_thread, args=(proc, audio_q), daemon=True).start()

    print("✓ NAVIA LISTA. Escuchando...\n")

    last_wake = 0

    while True:
        text = audio_q.get()
        print("WHISPER:", text)

        # ---- Wake word detection ----
        score = fuzz.partial_ratio(text.lower(), WAKE)
        now = time.time()

        if score >= WAKE_FUZZ_THRESHOLD and (now - last_wake) > WAKE_COOLDOWN_S:
            print(">> WAKE WORD DETECTED <<")
            last_wake = now
            continue  # next message will be the command

        # ---- Command detection ----
        cmd, params = recognize_command(text)
        if cmd:
            print(f"[COMMAND] {cmd} {params}")
        else:
            print("[NO MATCH]")


if __name__ == "__main__":
    main()
