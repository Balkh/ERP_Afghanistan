"""Qt signal connection helpers."""


def connect_unique(signal, slot):
    """Connect a Qt signal to a slot after removing the same slot if present."""
    try:
        signal.disconnect(slot)
    except (TypeError, RuntimeError):
        pass
    signal.connect(slot)
    return slot
