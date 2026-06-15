"""Qt signal connection helpers."""
import warnings


def connect_unique(signal, slot):
    """Connect a Qt signal to a slot after removing the same slot if present."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            pass
    signal.connect(slot)
    return slot
