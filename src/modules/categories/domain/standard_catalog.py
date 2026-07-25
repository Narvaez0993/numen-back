from src.modules.categories.domain.entities.category import Category, CategoryFlow


def _standard(id: str, name: str, icon: str, color: str, flow: CategoryFlow) -> Category:
    return Category(
        id=id,
        user_id=None,
        name=name,
        icon=icon,
        color=color,
        flow=flow,
        is_standard=True,
    )


# Global catalog (source of truth). Kept in code — not seeded in the DB — so it
# is versioned with deploys and costs zero queries. Slugs are stable ids that
# movements/analytics reference. Icons/colors mirror the front catalog.
STANDARD_CATEGORIES: tuple[Category, ...] = (
    _standard("mercado", "Mercado", "shopping-cart", "mint", "expense"),
    _standard("domi", "Domicilios", "truck", "coral", "expense"),
    _standard("transporte", "Transporte", "car", "purple", "expense"),
    _standard("comida", "Comida fuera", "tools-kitchen-2", "pink", "expense"),
    _standard("cafe", "Café", "coffee", "amber", "expense"),
    _standard("entret", "Entretenimiento", "movie", "purple", "expense"),
    _standard("subs", "Suscripciones", "refresh", "amber", "expense"),
    _standard("servicios", "Servicios", "bolt", "amber", "expense"),
    _standard("salud", "Salud", "heart", "mint", "expense"),
    _standard("educacion", "Educación", "school", "purple", "expense"),
    _standard("hogar", "Hogar", "home-2", "mint", "expense"),
    _standard("otros", "Otros", "dots", "neutral", "expense"),
    _standard("salario", "Salario", "cash", "mint", "income"),
    _standard("freelance", "Freelance", "building-bank", "purple", "income"),
    _standard("otro_ingreso", "Otro", "dots", "neutral", "income"),
)


def standard_name_exists(name: str, flow: CategoryFlow) -> bool:
    """True if a standard category with this name (case-insensitive) and flow exists."""
    lowered = name.casefold()
    return any(c.flow == flow and c.name.casefold() == lowered for c in STANDARD_CATEGORIES)
