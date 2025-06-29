import re

def pascal_to_snake(name: str) -> str:
    """
    Convert PascalCase or camelCase to snake_case.
    """
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def truncate(s: str, limit: int) -> str:
    if len(s) > limit:
        return (
            s[:limit] +
            f"… (truncated, {len(s) - limit} chars more)"
        )

    return s