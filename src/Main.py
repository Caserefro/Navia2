import queue
import subprocess
import threading
import time
import re
import signal  # <--- Added for sending Ctrl+C signal
from llama_cpp import Llama
from fuzzywuzzy import fuzz

# Assuming these exist in your local files
from Command import *
from Handlers import *

# ---------- CONFIG ----------
WAKE = "navia"
WAKE_FUZZ_THRESHOLD = 72
WAKE_COOLDOWN_S = 1.0

MODEL_PATH = "/home/pi/Navia1/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"

# Global variable to track the subprocess
current_whisper_proc = None

# ---------------------------------------------------------
# LOAD LLM
# ---------------------------------------------------------

print("⏳ Cargando modelo LLM Qwen2.5-1.5B-Instruct…")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=4,
)
print("✓ LLM cargado\n")


# ---------------------------------------------------------
# WHISPER MANAGEMENT (NEW)
# ---------------------------------------------------------

def start_whisper(audio_q):
    """Starts the Whisper subprocess and its reader thread."""
    global current_whisper_proc

    # Prevent starting if already running
    if current_whisper_proc is not None:
        return

    whisper_cmd = [
        "/home/pi/Downloads/whisper.cpp/build/bin/whisper-stream",
        "-m", "/home/pi/Downloads/whisper.cpp/models/ggml-base-q5_1.bin",
        "--language", "es",
        "-t", "6",  # Uses 6 threads
        "-ac", "512",
    ]

    print(">> STARTING WHISPER (Listening)...")

    current_whisper_proc = subprocess.Popen(
        whisper_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Start a new thread for this specific process instance
    t = threading.Thread(target=reader_thread, args=(current_whisper_proc, audio_q), daemon=True)
    t.start()


def stop_whisper():
    """Stops Whisper gracefully to free up RAM/CPU for the LLM."""
    global current_whisper_proc

    if current_whisper_proc:
        print(">> PAUSING WHISPER (Freeing resources for LLM)...")

        # Send SIGINT (Ctrl+C) to trigger the 'is_running = false' loop in C++
        current_whisper_proc.send_signal(signal.SIGINT)

        try:
            # Give it 2 seconds to close files and free memory
            current_whisper_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            print("!! Whisper stuck, forcing kill...")
            current_whisper_proc.kill()

        current_whisper_proc = None


# ---------------------------------------------------------
# WHISPER READER
# ---------------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
BRACKET_ONLY = re.compile(r"^\[(.*?)\]$")


def is_noise(text):
    if not text: return True
    clean = (
        text.lower()
        .replace(".", "")
        .replace("!", "")
        .replace("?", "")
        .strip()
    )
    # Ensure NOISE_WORDS is defined in your Command/Handlers file,
    # otherwise define it here: NOISE_WORDS = {"música", "risa", "pasos", ...}
    return clean in NOISE_WORDS


def reader_thread(proc, q):
    """Reads from the specific process provided in args."""
    try:
        # Loop over stdout. When proc dies, stdout closes and loop breaks.
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
                continue

            # Deliver clean line to main thread
            q.put(line)
    except Exception as e:
        # This might happen if we kill the process while reading
        pass


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def ask_llm(prompt: str) -> str:
    """Send Spanish prompt to LLM and return answer."""
    print("### LLM INPUT:", prompt)

    # Note: Ensure SYSTEM_PROMPT is defined in your imports
    chat_prompt = (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"<|user|>\n{prompt}\n"
        f"<|assistant|>\n"
    )

    completion = llm(
        prompt=chat_prompt,
        max_tokens=60,
        temperature=0.6,
        stop=["<|user|>", "<|system|>"],
    )

    answer = completion["choices"][0]["text"].strip()
    print("### LLM OUTPUT:", answer)
    return answer


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
# MAIN
# ---------------------------------------------------------
def main():
    audio_q = queue.Queue()
    start_whisper(audio_q)  # 1. Iniciar Whisper

    print("✓ NAVIA LISTA (MODO ALMACÉN). Escuchando...\n")

    last_wake = 0
    listening_for_command = False

    while True:
        try:
            text = audio_q.get(timeout=1)
        except queue.Empty:
            continue

        print(f"WHISPER: {text}")

        # ---- Wake word detection ----
        score = fuzz.partial_ratio(text.lower(), WAKE)
        now = time.time()

        if score >= WAKE_FUZZ_THRESHOLD and (now - last_wake) > WAKE_COOLDOWN_S:
            print(">> WAKE WORD DETECTED <<")
            last_wake = now
            listening_for_command = True
            continue  # Vuelve al inicio para escuchar el comando real

        if not listening_for_command:
            continue

        # Ya tenemos el comando del usuario, detenemos Whisper AHORA
        # para liberar recursos antes de procesar nada complejo.
        stop_whisper()

        # ---- 1. Identificar si hay datos del sistema necesarios ----
        cmd, params = recognize_command(text)
        system_context = ""

        if cmd:
            print(f"[SISTEMA] Ejecutando consulta interna: {cmd}")
            handler = COMMAND_HANDLERS.get(cmd)
            if handler:
                # Obtenemos los datos del almacén (strings)
                system_context = handler(params)

        # ---- 2. Preparar Prompt para el LLM ----
        # Si hubo comando, le damos los datos al LLM y le decimos que los use.
        # Si no hubo comando, es solo charla normal.
        if system_context:
            prompt_final = (
                f"Información del sistema: {system_context}\n"
                f"Pregunta del usuario: {text}\n"
                f"Instrucción: Responde al usuario usando la información del sistema de forma natural y profesional."
            )
        else:
            prompt_final = text

        # ---- 3. Ejecutar LLM ----
        try:
            print("[LLM] Generando respuesta...")
            response = ask_llm(prompt_final)
            print("NAVIA:", response)

        except Exception as e:
            print(f"Error LLM: {e}")

        # ---- 4. Reiniciar Whisper ----
        start_whisper(audio_q)
        listening_for_command = False

if __name__ == "__main__":
    main()