def count_values(items: list) -> int:
    """Count of items in a list. Unlike the other tools, this one doesn't
    require numbers — "how many appointments/rows/orders" needs to count
    raw_rows (a list of record dicts from the Query Tool), not a list of
    already-extracted numeric values."""
    return len(items)
