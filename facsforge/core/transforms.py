def prepare_markers(df, experiment):
    """
    Removes ignored markers from the DataFrame.
    """
    panel = experiment["panel"]
    cols = [c for c in df.columns if not panel.get(c, {}).get("ignore", False)]
    return df[cols]
