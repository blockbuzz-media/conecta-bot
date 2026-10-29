"""Reglas puras de compatibilidad. Sin acceso a Telegram ni a la base."""


def _as_set(value):
    if not value:
        return set()
    return {x.strip() for x in str(value).split(",") if x.strip()}


def gender_compatible(seeker_seeking, candidate_gender):
    """True si el género del candidato está en lo que busca el otro."""
    seeking = _as_set(seeker_seeking)
    if not seeking or "any" in seeking:
        return True
    return candidate_gender in seeking


def age_compatible(age, age_min, age_max):
    if age_min is not None and age < age_min:
        return False
    if age_max is not None and age > age_max:
        return False
    return True


def mutually_compatible(a, b):
    """a y b son dicts con age, gender, seeking, age_min, age_max."""
    return (
        gender_compatible(a.get("seeking"), b.get("gender"))
        and gender_compatible(b.get("seeking"), a.get("gender"))
        and age_compatible(b["age"], a.get("age_min"), a.get("age_max"))
        and age_compatible(a["age"], b.get("age_min"), b.get("age_max"))
    )
