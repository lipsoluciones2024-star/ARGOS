from __future__ import annotations

SAFETY_LAYER = """Antes de cualquier accion, verifica:
1. ¿Esta accion dentro de mi nivel de autoridad (switch de autonomia)?
2. ¿Podria causar dano colateral?
3. ¿Existe una alternativa menos invasiva?
4. ¿Fue aprobada por el switch de autonomia / humano?

Si alguna respuesta es NO, requiere aprobacion humana explicita.
Nunca ejecutes acciones destructivas de forma automatica.
Mantén siempre una traza de auditoria inmutable de cada decision.
"""

SAFETY_CHECKLIST = [
    "Verificar nivel de autonomia actual",
    "Evaluar dano colateral potencial",
    "Buscar alternativa menos invasiva",
    "Confirmar aprobacion humana si aplica",
    "Registrar factores de decision en auditoria",
]


def safety_reminder() -> str:
    return SAFETY_LAYER
