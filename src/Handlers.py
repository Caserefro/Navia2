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

def handle_draw_square(params):
    print("🟦 Dibujando cuadrado…")
    # Later add: robot action, screen drawing, whatever you need.


COMMAND_HANDLERS = {
    "state_pedidos": handle_state_pedidos,
    "listado_pedidos": handle_listado_pedidos,
    "numero_pedidos": handle_numero_pedidos,
    "draw_square": handle_draw_square,
}
