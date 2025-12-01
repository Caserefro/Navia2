# ---------------------------------------------------------
# COMMAND DISPATCHER
# ---------------------------------------------------------

def handle_state_pedidos(params):
    print("[INFO] Estado de pedidos solicitado.")
    # placeholder — later plug DB
    print("→ (Aquí iría la consulta del estado de los pedidos)")


def handle_listado_pedidos(params):
    print("[INFO] Listado de pedidos solicitado.")
    print("→ (Aquí iría la lista de pedidos del día)")


def handle_numero_pedidos(params):
    print("[INFO] Cantidad de pedidos solicitada.")
    print("→ (Aquí se retornaría el número total del día)")


def handle_ask_name(params):
    print("Mi nombre es Navia.")


def handle_ask_creator(params):
    print("Fui creada por tu sistema, diseñada para asistir en pedidos y consultas.")


def handle_ask_purpose(params):
    print("Mi propósito es ayudarte a consultar pedidos, estados y realizar tareas relacionadas.")


def handle_ask_about_self(params):
    print("Soy Navia, una asistente diseñada para ayudarte con información y operaciones básicas.")

def handle_remote_control_on(params):
    print("✔ Control remoto activado.")
    # Later: enable RC mode

def handle_remote_control_off(params):
    print("✖ Control remoto desactivado.")
    # Later: disable RC mode

def handle_draw_square(params):
    print("🟦 Dibujando cuadrado…")
    # Later add: robot action, screen drawing, whatever you need.


COMMAND_HANDLERS = {
    "state_pedidos": handle_state_pedidos,
    "listado_pedidos": handle_listado_pedidos,
    "numero_pedidos": handle_numero_pedidos,
    "ask_name": handle_ask_name,
    "ask_creator": handle_ask_creator,
    "ask_purpose": handle_ask_purpose,
    "ask_about_self": handle_ask_about_self,
    "remote_control_on": handle_remote_control_on,
    "remote_control_off": handle_remote_control_off,
    "draw_square": handle_draw_square,

}
