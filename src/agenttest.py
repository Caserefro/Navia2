import subprocess
import threading
import queue
import re

def agent_reply(text):
    return f"[AGENT] -> {text}"

q = queue.Queue()

# Matches bracket-only content like [Música]
BRACKET_ONLY = re.compile(r"^\[(.*?)\]$")

# Remove all ANSI escape sequences
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def reader_thread(proc):
    for raw_line in proc.stdout:

        # 1. Remove ANSI sequences
        line = ANSI_RE.sub("", raw_line).strip()

        # 2. Skip completely empty lines
        if not line:
            continue

        # 3. Skip whisper cursor-update noise (sometimes prints just "\r")
        if line in ("\r", "\n"):
            continue

        # 4. Check bracket-only form
        m = BRACKET_ONLY.match(line)
        if m:
            text = m.group(1).strip()
            if text:
                q.put(text)
            continue

        # 5. Otherwise it's normal spoken text
        q.put(line)


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
        bufsize=1
    )

    threading.Thread(target=reader_thread, args=(proc,), daemon=True).start()

    print("Agente listo. Escuchando...\n")

    while True:
        text = q.get()
        print("WHISPER:", text)
        print(agent_reply(text))


if __name__ == "__main__":
    main()

