# ---------------------------------------------------------
# COMMAND DISPATCHER
# ---------------------------------------------------------
import random
import time

# --- DATOS DE ALMACÉN ---
ITEMS_ALMACEN = [
    "Cajas de Cartón 40x40",
    "Cinta de Embalaje Industrial",
    "Palets de Madera Estándar",
    "Bobinas de Plástico Stretch",
    "Cascos de Seguridad (Amarillos)",
    "Tornillos Hexagonales 5mm",
    "Chalecos Reflectantes"
]

ESTADOS_LOGISTICA = [
    "En muelle de carga",
    "En tránsito (Camión 4)",
    "Almacenado en Pasillo B",
    "Pendiente de picking"
]


def handle_listado_pedidos(params):
    # Simula consultar la DB del almacén
    num_items = random.randint(3, 5)
    items = random.sample(ITEMS_ALMACEN, num_items)

    # Construimos un texto con los datos crudos para el LLM
    data = "LISTADO ACTUAL DE PEDIDOS EN ALMACÉN:\n"
    for item in items:
        qty = random.randint(10, 500)
        data += f"- {qty} unidades de {item}\n"

    return data


def handle_state_pedidos(params):
    # Simula buscar un pedido específico
    estado = random.choice(ESTADOS_LOGISTICA)
    ubicacion = f"Estante {random.randint(1, 20)}, Altura {random.randint(1, 5)}"

    return f"DATOS DEL SISTEMA: El pedido solicitado se encuentra: {estado}. Ubicación física: {ubicacion}."


def handle_numero_pedidos(params):
    total = random.randint(150, 300)
    urgentes = random.randint(5, 20)
    return f"METRICAS ALMACÉN: Hay un total de {total} pedidos procesados hoy. De ellos, {urgentes} están marcados como URGENTES."


def handle_draw_square(params):
    # Este es una acción física, quizás aquí sí quieras imprimir o ejecutar motor
    # Pero devolvemos texto para que el LLM confirme.
    return "ACCIÓN ROBOT: Secuencia de movimiento 'Cuadrado' ejecutada con éxito."


# Actualiza el diccionario
COMMAND_HANDLERS = {
    "pedidos_listado": handle_listado_pedidos,
    "pedidos_estado": handle_state_pedidos,
    "pedidos_numero": handle_numero_pedidos,
    "draw_square": handle_draw_square,
}
