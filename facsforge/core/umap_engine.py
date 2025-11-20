from umap import UMAP
import pandas as pd
import numpy as np

def run_umap(populations, experiment):
    umap_cfg = experiment.get("umap", {})
    if not umap_cfg.get("enabled", False):
        return None

    # collect populations
    celltypes = umap_cfg.get("celltypes", "auto")
    if celltypes == "auto":
        celltypes = experiment.get("celltypes_of_interest", [])

    dfs = []
    for name in celltypes:
        if name not in populations:
            continue
        df = populations[name].copy()
        df["celltype"] = name
        dfs.append(df)

    df_all = pd.concat(dfs, axis=0)

    # choose markers
    markers = umap_cfg.get("markers", "auto")
    if markers == "auto":
        panel = experiment["panel"]
        markers = [m for m, cfg in panel.items() if not cfg.get("ignore")]
        markers = [m for m in markers if m in df_all.columns]

    X = df_all[markers].to_numpy()

    reducer = UMAP(
        n_neighbors=umap_cfg.get("neighbors", 30),
        min_dist=umap_cfg.get("min_dist", 0.2),
        metric=umap_cfg.get("metric", "euclidean")
    )

    emb = reducer.fit_transform(X)

    df_umap = pd.DataFrame({
        "UMAP1": emb[:, 0],
        "UMAP2": emb[:, 1],
        "celltype": df_all["celltype"].values
    })

    return df_umap

