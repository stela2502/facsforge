# facsforge/core/pita.py
import pandas as pd
import re

_HAS_LOGICLE = False
_logicle = None

def init_logicle():
    global _HAS_LOGICLE, _logicle

    if _logicle is not None:
        return _HAS_LOGICLE, _logicle   # already initialized

    try:
        from flowutils import logicle_c as mod

        if hasattr(mod, "logicle"):
            _logicle = mod.logicle
        elif hasattr(mod, "logicle_transform"):
            _logicle = mod.logicle_transform
        elif hasattr(mod, "logicle_scale"):
            _logicle = mod.logicle_scale
        else:
            raise ImportError("flowutils.logicle_c has no usable function")

        _HAS_LOGICLE = True
        print("[FACSForge] Logicle loaded")   # optional

    except Exception as e:
        _HAS_LOGICLE = False
        _logicle = None
        print(f"[FACSForge] Logicle unavailable → linear only: {e}")

    return _HAS_LOGICLE, _logicle


def get_logicle():
    """
    Returns (has_logicle, logicle_function)
    Guaranteed to initialize once.
    """
    if _logicle is None:
        init_logicle()
    return _HAS_LOGICLE, _logicle


# ----------------------------------
# Transform helper
# ----------------------------------
def xform(s: pd.Series):
    _HAS_LOGICLE, _logicle = get_logicle()
    if not _HAS_LOGICLE:
        return s

    x = s.to_numpy(dtype=float)
    do_scale, label = scale_info(s.name)

    if not (_logicle and _HAS_LOGICLE and do_scale):
        return s

    T = 262144.0
    W = 0.5
    M = 4.5
    A = 0.0

    try:
        y = _logicle(T, W, M, A, x)
    except TypeError:
        y = _logicle(x, T, W, M, A)

    return pd.Series(y, index=s.index, name=label)

_SCATTER_RE = re.compile(
    r"""
    (
        FSC |
        SSC |
        TIME
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

def scale_info(name: str):
    if _SCATTER_RE.search(name) is not None:
        return False, name         # scatter → linear
    else:
        return True, f"{name} (scaled)"  # fluorescence → logicle