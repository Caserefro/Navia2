import re

# System / KB prompt: short, factual info for Navia
SYSTEM_PROMPT = """Eres Navia, un asistente local en una Raspberry Pi.
- Nombre: Navia.
- Propósito: ayudar con pedidos, consultar estado, controlar el robot mecanum, ejecutar acciones seguras.
- Limitaciones: sin internet, responde solo con información local o con "No tengo esa información" si no lo sabe.
Responde en español de forma breve y útil.
"""

# Words Whisper outputs that are NOT commands
NOISE_WORDS = {
    "musica",
    "música",
    "música.",
    "musica.",
    "risa",
    "risas",
    "aplausos",
    "ruido",
    "sonido",
    "golpes",
    "silencio",
    "silencio.",
    "Música de cierre",
}
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
    ],
    "remote_control_on": [
        "activar control remoto",
        "activa el control remoto",
        "enciende el control remoto",
        "habilita el control remoto",
        "pon modo control remoto",
        "modo remoto",
        "quiero control remoto",
    ],

    "remote_control_off": [
        "desactivar control remoto",
        "apaga el control remoto",
        "deshabilita el control remoto",
        "salir de control remoto",
        "quita modo remoto",
        "finaliza control remoto",
        "terminar control remoto",
    ],
    "draw_square": [
        "dibuja un cuadrado",
        "haz un cuadrado",
        "traza un cuadrado",
        "quiero un cuadrado",
        "puedes dibujar un cuadrado",
        "crea un cuadrado",
        "marca un cuadrado",
    ],
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
