def bool_of_str(s: str) -> bool:
    s = s.strip().lower()
    if s not in {'true', 'false'}:
        raise ValueError(f"Invalid boolean string: {s}")
    return s == 'true'
