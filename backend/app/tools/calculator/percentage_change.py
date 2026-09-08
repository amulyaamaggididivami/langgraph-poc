def percentage_change(old: float, new: float) -> float:
    """Percentage change from `old` to `new` (negative if it decreased)."""
    return ((new - old) / old) * 100
