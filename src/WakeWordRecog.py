#!/usr/bin/env python3
import queue
import re
import subprocess
import threading
import time

from fuzzywuzzy import fuzz

# ---------- CONFIG ----------
WAKE = "navia"
WAKE_FUZZ_THRESHOLD = 72
WAKE_COOLDOWN_S = 1.0

# ---------------------------------------------------------
# FUZZY COMMAND PHRASES
# ---------------------------------------------------------
COMMAND_PHRASES = {
    # --- LISTADO DE PEDIDOS ---
    "pedidos_listado": [
        "listado de los pedidos de hoy",
        "lista de pedidos de hoy",
        "qué pedidos hay hoy",
        "muestrame los pedidos de hoy",
        "enséñame los pedidos de hoy",
        "dame los pedidos de hoy",
        "consulta los pedidos de hoy",
        "pedidos de hoy",
        "quiero ver los pedidos de hoy",
        "mostrar pedidos del día",
    ],

    # --- ESTADO DE PEDIDOS ---
    "pedidos_estado": [
        "cuál es el estado de los pedidos",
        "estado de los pedidos",
        "cómo van los pedidos",
        "dime dónde se encuentra el pedido",
        "dónde está mi pedido",
        "dónde se encuentra el pedido",
        "localización de un pedido",
        "ubicación del pedido",
        "en qué estado está el pedido",
        "seguimiento de pedido",
        "status del pedido",
        "seguimiento pedidos",
    ],

    # --- NÚMERO DE PEDIDOS ---
    "pedidos_numero": [
        "cuántos pedidos son hoy",
        "número de pedidos de hoy",
        "cuántos pedidos hay hoy",
        "cantidad de pedidos hoy",
        "total de pedidos del día",
        "cuántos pedidos tenemos",
        "dime el número de pedidos",
        "pedidos totales hoy",
    ],

    # --- IDENTIDAD / NOMBRE ---
    "ask_name": [
        "nombre",
        "cómo te llamas",
        "cual es tu nombre",
        "cuál es tu nombre",
        "dime tu nombre",
        "como te llamas",
        "tu nombre",
    ],

    # --- ORIGEN / CREADOR ---
    "ask_creator": [
        "quien te creó",
        "quien te hizo",
        "quien te programó",
        "quien te construyó",
        "quién te creó",
        "quién te hizo",
        "quién te programó",
        "quién te construyó",
        "de dónde vienes",
        "quién es tu creador",
    ],

    # --- PROPÓSITO ---
    "ask_purpose": [
        "proposito",
        "propósito",
        "para qué sirves",
        "para que sirves",
        "qué puedes hacer",
        "que puedes hacer",
        "cuál es tu función",
        "cual es tu funcion",
        "qué haces",
    ],

    # --- INFORMACIÓN GENERAL DEL ASISTENTE ---
    "ask_about_self": [
        "háblame de ti",
        "quién eres",
        "dime sobre ti",
        "que eres",
        "que tipo de asistente eres",
    ]
}

# ---------------------------------------------------------
# MOVEMENT / PARAMETRIC COMMAND REGEX
# ---------------------------------------------------------
PATTERN_COMMANDS = [
    (r'\b(det(e|én)|pare|para|alto|detente|stop)\b',
     "stop", {}),

    (r'\b(avanz(?:a|ar)|adelante|sigue)\b(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?'
     r'\s*(?P<unit>m|metros|metro|cm|centimetros|centímetros)?\b',
     "forward", {"default_m": 1.0}),

    (r'\b(retrocede|retroceder|atrás|atras|volver atrás)\b(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?'
     r'\s*(?P<unit>m|metros|metro|cm|centimetros|centímetros)?\b',
     "backward", {"default_m": 1.0}),

    (r'\b(strafe|strafeo|desplazate|desplazarse|muevete a la|mueve a la|izquierda)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>m|metros|cm)?\b',
     "strafe_left", {"default_m": 0.5}),

    (r'\b(derecha|a la derecha|mueve a la derecha|desplazate a la derecha)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>m|metros|cm)?\b',
     "strafe_right", {"default_m": 0.5}),

    (r'\b(gira|rota|gírate|gire)\b(?:\s+(?P<sign>izquierda|derecha|izq|der))?'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>grados|grado|deg|°)?\b',
     "rotate", {"default_deg": 90}),

    (r'\b(gira a la izquierda|gira izquierda|rota izquierda|girar izquierda)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>grados|grado|deg|°)?\b',
     "rotate_ccw", {"default_deg": 90}),

    (r'\b(gira a la derecha|gira derecha|rota derecha|girar derecha)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>grados|grado|deg|°)?\b',
     "rotate_cw", {"default_deg": 90}),

    (r'\b(diagonal (del )?frente izquierda|diagonal frente izquierda|diagonal adelante izquierda|'
     r'adelante izquierda|frente izquierda)\b(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?'
     r'\s*(?P<unit>m|metros)?\b',
     "diagonal_front_left", {"default_m": 1.0}),

    (r'\b(diagonal (del )?frente derecha|diagonal frente derecha|diagonal adelante derecha|'
     r'adelante derecha|frente derecha)\b(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?'
     r'\s*(?P<unit>m|metros)?\b',
     "diagonal_front_right", {"default_m": 1.0}),

    (r'\b(diagonal atras izquierda|diagonal atrás izquierda|atras izquierda)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>m|metros)?\b',
     "diagonal_back_left", {"default_m": 1.0}),

    (r'\b(diagonal atras derecha|diagonal atrás derecha|atras derecha)\b'
     r'(?:\s+(?P<value>[-+]?\d+[.,]?\d*))?\s*(?P<unit>m|metros)?\b',
     "diagonal_back_right", {"default_m": 1.0}),

    (r'\b(avanza|muevete|mueve)\b(?:\s+por)?\s+(?P<value>[-+]?\d+[.,]?\d*)'
     r'\s*(?P<unit>s|segundos|seg)\b',
     "forward_time", {"default_s": 1.0}),

    (r'\b(velocidad|velocida|vel|max speed|set speed|pon velocidad)\b.*?'
     r'(?P<value>[-+]?\d+[.,]?\d*)\s*(?P<unit>%|porc|por ciento)?\b',
     "set_speed", {"default_pct": 50}),

    (r'\b(ir a|goto|ve a|ve al)\b.*?(?P<value>[-+]?\d+)\b',
     "goto_waypoint", {"default_id": None}),
]

PATTERNS = [(re.compile(p, re.IGNORECASE), cmd, opts)
            for (p, cmd, opts) in PATTERN_COMMANDS]


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

# Words Whisper outputs that are NOT commands
NOISE_WORDS = {
    "musica",
    "música",
    "risa",
    "risas",
    "aplausos",
    "ruido",
    "sonido",
    "golpes",
    "silencio",
    "silencio.",
}


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
