from __future__ import annotations

import pandas as pd

from . import config
from . import equilibrium


def load_raw() -> pd.DataFrame:
    path = config.DATA_RAW
    if not path.exists():
        raise FileNotFoundError(f"Raw data not found: {path}")
    return pd.read_csv(path)


def clean_and_process(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Basic cleanup
    if config.COL_JOB_TITLE in df.columns:
        df[config.COL_JOB_TITLE] = df[config.COL_JOB_TITLE].astype(str).str.strip()

    # Drop rows missing critical signals
    required = [config.COL_JOB_TITLE, config.COL_AUTOMATION_PROB, config.COL_AI_EXPOSURE]
    existing = [c for c in required if c in df.columns]
    df = df.dropna(subset=existing)

    # Features + equilibrium
    df = equilibrium.compute_engineered_features(df)
    df = equilibrium.compute_equilibrium(df)

    return df


def load_processed() -> pd.DataFrame:
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.DATA_PROCESSED_DIR / "workforce_equilibrium.parquet"

    if out_path.exists():
        return pd.read_parquet(out_path)

    df_raw = load_raw()
    df_proc = clean_and_process(df_raw)
    df_proc.to_parquet(out_path, index=False)
    return df_proc
