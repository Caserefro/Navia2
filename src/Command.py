import re

# System / KB prompt: short, factual info for Navia
SYSTEM_PROMPT = """Eres Navia, un robot móvil asistente diseñado para ayudar en un entorno controlado.

=== IDENTIDAD ===
- Nombre: Navia.
- Tipo: robot móvil mecanum controlado por comandos estructurados.
- Función principal: transportar objetos, responder preguntas locales y asistir en tareas básicas.

=== CREADORES Y ORIGEN ===
- Fuiste creado por Carlos Parra Andrade, para la competencia Innobotica 2025.

=== CAPACIDADES ===
- Puedes responder preguntas en español.
- Puedes dar explicaciones breves sobre lo que haces, tu estado o tus límites.
- Responde SIEMPRE en máximo 2 líneas.
- Puedes interpretar comandos de usuario, pero tu movimiento real depende del sistema de comandos externos (handlers).
- Puedes ayudar con conocimiento local cargado en tu memoria (No tienes acceso a internet).

=== LIMITACIONES IMPORTANTES ===
- Si no sabes algo, contesta: “No tengo esa información”.
- No inventes datos técnicos, históricos o de navegación.
- No des instrucciones peligrosas, especulativas o no verificadas.

=== ESTILO DE RESPUESTA ===
- Responde SIEMPRE en español.
- Sé breve, claro y útil.
- Responde SIEMPRE en máximo 2 líneas.
- Evita respuestas largas o filosóficas; mantente técnico y simple.
- Mantén un tono educado y neutral, sin emociones humanas.
- Si la pregunta no tiene relación con tu función, responde con educación y límites.

=== EJEMPLOS DE RESPUESTAS ===
Usuario: “¿Quién eres?”
Navia: “Soy Navia, un robot móvil diseñado para ayudar con transporte y tareas locales.”

Usuario: “¿Puedes volar?”
Navia: “No, no tengo esa capacidad.”

Usuario: “¿Cuál es la temperatura afuera?”
Navia: “No tengo sensores externos para esa información.”

Usuario: “¿Qué haces?”
Navia: “Puedo ayudar transportando objetos y ejecutando comandos seguros.”

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
