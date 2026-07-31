"""Narración: the LLM writes the voice, never the numbers.

Every slide and play arrives here already composed — amounts, percentages and
dates are baked into the payload the client will render. The narrator adds one
human line per item and is FORBIDDEN from writing figures, so a hallucinated
number cannot exist. If the model fails or skips an item, a static template
takes its place: the Corte always ships.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from src.modules.assistant.application.services.narration_tools import MAX_NARRATION_TEXT

MONTHLY = "monthly_summary"
WEEKLY = "weekly_review"

_SYSTEM_MONTHLY_ES: Final[str] = """\
Eres la voz de Deshka narrando El Corte: el resumen del mes de un usuario, contado en \
historias. Recibes items con datos ya calculados por la app y tu ÚNICA salida es la \
herramienta narrate, con una línea por item_id.

REGLAS:
- JAMÁS escribas cifras: ni montos, ni porcentajes, ni conteos, ni fechas numéricas. La \
pantalla ya muestra los números en grande; tu línea acompaña, no repite.
- Sí puedes nombrar categorías, comercios, metas y días de la semana ("un sábado").
- Una sola frase por item, máximo 180 caracteres, en español de tú.
- Tono cercano y curioso, sin culpa, sin celebraciones infladas, sin emojis.
- Cubre todos los item_id que recibas, exactamente una vez.\
"""

_SYSTEM_MONTHLY_EN: Final[str] = """\
You are Deshka's voice narrating El Corte: a user's month told as stories. You receive \
items whose data the app already computed, and your ONLY output is the narrate tool, \
one line per item_id.

RULES:
- NEVER write figures: no amounts, no percentages, no counts, no numeric dates. The \
screen already shows the numbers big; your line accompanies them, it does not repeat them.
- You may name categories, merchants, goals and weekdays ("a Saturday").
- One sentence per item, 180 characters max.
- Warm and curious tone, no guilt, no inflated celebration, no emojis.
- Cover every item_id you receive, exactly once.\
"""

_SYSTEM_WEEKLY_ES: Final[str] = """\
Eres el coach financiero de Deshka escribiendo la revisión semanal de un usuario. Recibes \
el diagnóstico ya calculado (totales, comparación, categoría top, jugadas propuestas) y tu \
ÚNICA salida es la herramienta narrate, con una línea por item_id.

REGLAS:
- JAMÁS escribas cifras: ni montos, ni porcentajes, ni conteos. La tarjeta ya muestra los \
números; tu línea interpreta y acompaña.
- Sí puedes nombrar categorías, comercios y metas.
- El diagnóstico es honesto y accionable: si la semana fue dura, dilo sin culpa y apunta a \
la jugada; si fue buena, reconócelo sin inflar.
- Una sola frase por item, máximo 180 caracteres, en español de tú, sin emojis.
- Cubre todos los item_id que recibas, exactamente una vez.\
"""

_SYSTEM_WEEKLY_EN: Final[str] = """\
You are Deshka's financial coach writing a user's weekly review. You receive the \
already-computed diagnosis (totals, comparison, top category, proposed plays) and your \
ONLY output is the narrate tool, one line per item_id.

RULES:
- NEVER write figures: no amounts, no percentages, no counts. The card already shows the \
numbers; your line interprets and accompanies.
- You may name categories, merchants and goals.
- The diagnosis is honest and actionable: a rough week is said without guilt and points \
to the play; a good week is acknowledged without inflation.
- One sentence per item, 180 characters max, no emojis.
- Cover every item_id you receive, exactly once.\
"""

_SYSTEMS: Final[Mapping[tuple[str, str], str]] = {
    (MONTHLY, "es"): _SYSTEM_MONTHLY_ES,
    (MONTHLY, "en"): _SYSTEM_MONTHLY_EN,
    (WEEKLY, "es"): _SYSTEM_WEEKLY_ES,
    (WEEKLY, "en"): _SYSTEM_WEEKLY_EN,
}

_FALLBACKS_ES: Final[Mapping[str, str]] = {
    "cover": "Tu mes, en corto.",
    "weekly_diagnosis": "Tu semana, leída por tu agente.",
    "big_number": "Así se movió tu plata este mes.",
    "category_bars": "Aquí es donde más se fue.",
    "fun_fact": "Hubo un día que se llevó el show.",
    "pulse": "Así se compara con tu mes anterior.",
    "goal": "Tu meta sigue en camino.",
    "first_month": "Tu primer mes registrado. Desde aquí, todo se compara.",
    "play": "Una jugada para el mes que empieza.",
    "set_category_cap": "Ponerle un techo a esta categoría te da control sin dejar de vivir.",
    "raise_category_cap": "Este tope quedó corto frente a tu realidad: ajústalo y que mande.",
    "set_month_cap": "Un techo para todo el mes: una sola cifra que cuida el resto.",
    "contribute_goal": "Un aporte ahora acerca la meta más de lo que pesa en el bolsillo.",
    "treat": "Vas bien y los números lo saben: date un gusto sin remordimiento.",
}

_FALLBACKS_EN: Final[Mapping[str, str]] = {
    "cover": "Your month, in short.",
    "weekly_diagnosis": "Your week, read by your agent.",
    "big_number": "This is how your money moved this month.",
    "category_bars": "This is where most of it went.",
    "fun_fact": "One day stole the show.",
    "pulse": "Here is how it compares to last month.",
    "goal": "Your goal is still on its way.",
    "first_month": "Your first recorded month. Everything compares from here.",
    "play": "One move for the month ahead.",
    "set_category_cap": "A cap on this category buys control without giving up living.",
    "raise_category_cap": "This cap fell short of reality — adjust it and let it rule.",
    "set_month_cap": "One ceiling for the whole month: a single number guarding the rest.",
    "contribute_goal": "A contribution now moves the goal more than it weighs in the pocket.",
    "treat": "You are doing well and the numbers know it: treat yourself, guilt-free.",
}


@dataclass(frozen=True)
class NarrationItem:
    """One thing to narrate. `kind` picks the fallback template; `data` is the
    already-composed payload the model reads (and must not recompute)."""

    item_id: str
    kind: str
    data: Mapping[str, Any]


def narration_system_for(language: str, kind: str = MONTHLY) -> str:
    """Static per (kind, language) — the cacheable prefix of the whole sweep."""
    return _SYSTEMS.get((kind, language)) or _SYSTEMS[(kind, "es")]


def narration_request(items: Sequence[NarrationItem]) -> str:
    """The volatile user message: everything per-user rides here, never in the
    system prompt, so the cache prefix survives the sweep."""
    payload = [{"item_id": i.item_id, "kind": i.kind, "data": dict(i.data)} for i in items]
    return json.dumps({"items": payload}, ensure_ascii=False)


def fallback_text(kind: str, language: str) -> str:
    table = _FALLBACKS_EN if language == "en" else _FALLBACKS_ES
    return table.get(kind, table["cover"])


def apply_narration(
    arguments: Mapping[str, Any] | None,
    items: Sequence[NarrationItem],
    language: str,
) -> dict[str, str]:
    """item_id → line. Anything missing, duplicated, empty or over-long falls
    back to the template — a bad model turn degrades the prose, never the Corte."""
    narrated: dict[str, str] = {}
    raw = arguments.get("items") if isinstance(arguments, Mapping) else None
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, Mapping):
                continue
            item_id, text = entry.get("item_id"), entry.get("text")
            if not isinstance(item_id, str) or not isinstance(text, str):
                continue
            line = text.strip()
            if line and len(line) <= MAX_NARRATION_TEXT and item_id not in narrated:
                narrated[item_id] = line
    return {
        item.item_id: narrated.get(item.item_id, fallback_text(item.kind, language))
        for item in items
    }
