def calculate_trust_level(created: int, updated: int, invalid: int) -> str:
    total = created + updated + invalid

    if total == 0:
        return "YELLOW"

    invalid_ratio = invalid / total

    if invalid_ratio > 0.2:
        return "YELLOW"

    return "GREEN"
