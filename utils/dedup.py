def deduplicate(records):
    """
    Remove duplicate records by ID.
    """

    seen = set()
    unique = []

    for r in records:
        if r.record_id not in seen:
            seen.add(r.record_id)
            unique.append(r)

    return unique