import numpy as np

def _compute_threshold(values):
    """
    Compute auto threshold by valley finding.
    """
    hist, bins = np.histogram(values, bins=200)
    cutoff = np.percentile(hist, 20)
    idxs = np.where(hist < cutoff)[0]
    if len(idxs) == 0:
        return np.percentile(values, 95)
    return bins[idxs[0]]


def compute_auto_thresholds(df, experiment):
    """
    Compute thresholds for all marker channels (except ignored ones).
    """
    panel = experiment["panel"]

    thresholds = {}
    for marker in df.columns:
        pinfo = panel.get(marker)
        if pinfo is None:
            continue
        if pinfo.get("ignore"):
            continue
        # FSC/SSC typically should not get auto thresholds
        if marker.startswith("FSC") or marker.startswith("SSC"):
            continue

        thresholds[marker] = _compute_threshold(df[marker])

    return thresholds

