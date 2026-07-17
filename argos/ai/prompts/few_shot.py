from __future__ import annotations

from typing import Any, Dict, List

FEW_SHOT: List[Dict[str, Any]] = [
    {
        "role": "user",
        "content": "¿Qué hosts tenemos y hay alertas criticas?",
    },
    {
        "role": "assistant",
        "content": "Consulto el inventario y las alertas recientes.",
        "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "get_hosts", "arguments": "{}"}},
            {"id": "c2", "type": "function", "function": {"name": "list_alerts", "arguments": "{\"severity\":\"critical\"}"}},
        ],
    },
    {
        "role": "tool",
        "content": "{\"hosts\":[{\"host\":\"WIN-01\",\"events\":1542}]}",
        "name": "get_hosts",
        "tool_call_id": "c1",
    },
    {
        "role": "tool",
        "content": "[]",
        "name": "list_alerts",
        "tool_call_id": "c2",
    },
    {
        "role": "assistant",
        "content": (
            "Objetivo\nInventariar hosts y detectar alertas criticas.\n\n"
            "Hipotesis\nNo hay incidentes activos de momento.\n\n"
            "Herramientas\nget_hosts, list_alerts.\n\n"
            "Plan\nListar hosts y filtrar alertas criticas.\n\n"
            "Riesgos\nBajo: solo lectura.\n\n"
            "Resultado esperado\n1 host monitorizado, 0 alertas criticas.\n\n"
            "Proximos pasos\nSin accion inmediata; revisar en la proxima ventana de 24h."
        ),
    },
    {
        "role": "user",
        "content": "Una IP externa sospechosa aparece en varios eventos, ¿que hacemos?",
    },
    {
        "role": "assistant",
        "content": "Evaluo la reputacion de la IP y correlaciono los eventos antes de proponer.",
        "tool_calls": [
            {"id": "c3", "type": "function", "function": {"name": "ip_reputation", "arguments": "{\"ip\":\"45.33.32.156\"}"}},  # noqa: E501
            {"id": "c4", "type": "function", "function": {"name": "query_events", "arguments": "{\"filters\":{\"text\":\"45.33.32.156\"}}"}},  # noqa: E501
        ],
    },
    {
        "role": "tool",
        "content": "{\"ip\":\"45.33.32.156\",\"reputation\":\"malicious\",\"reports\":42}",
        "name": "ip_reputation",
        "tool_call_id": "c3",
    },
    {
        "role": "tool",
        "content": "{\"count\":7,\"events\":[{\"host\":\"WIN-01\",\"severity\":\"high\"}]}",
        "name": "query_events",
        "tool_call_id": "c4",
    },
    {
        "role": "assistant",
        "content": (
            "Objetivo\nDeterminar exposicion a IP maliciosa y proponer respuesta.\n\n"
            "Hipotesis\nLa IP esta reportada como maliciosa y genero 7 eventos en WIN-01.\n\n"
            "Herramientas\nip_reputation, query_events, propose_block_ip.\n\n"
            "Plan\nProponer bloqueo de la IP y revisar los eventos asociados en WIN-01.\n\n"
            "Riesgos\nMedio: el bloqueo es reversible y no afecta conectividad interna.\n\n"
            "Resultado esperado\nIP bloqueada en el perimeter virtual y eventos etiquetados.\n\n"
            "Proximos pasos\nEjecutar propose_block_ip y monitorear nuevos eventos de la IP."
        ),
    },
]


def get_few_shot(task: str = "general") -> List[Dict[str, Any]]:
    """Devuelve few-shot examples para la tarea indicada.

    ``task`` puede ser 'general' (todos) o 'correlation' (solo el segundo ejemplo).
    """
    if task == "correlation":
        return FEW_SHOT[5:]
    return FEW_SHOT
