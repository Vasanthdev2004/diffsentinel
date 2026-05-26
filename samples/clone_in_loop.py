def normalize_events(events):
    normalized = []
    for event in events:
        copied = event.copy()
        copied["name"] = copied["name"].strip().lower()
        normalized.append(copied)
    return normalized
