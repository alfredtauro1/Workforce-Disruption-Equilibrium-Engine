from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _rank_to_unit(s: pd.Series, ascending: bool = True) -> pd.Series:
    """Map values to [-1, 1] using rank-percentiles.

    This is robust to scale differences and keeps forces comparable.
    If the series is constant, returns zeros.
    """
    s = pd.to_numeric(s, errors="coerce")
    if s.nunique(dropna=True) <= 1:
        return pd.Series(0.0, index=s.index)
    r = s.rank(pct=True, method="average")
    if not ascending:
        r = 1.0 - r
    return (2.0 * (r - 0.5)).clip(-1.0, 1.0)


def _education_to_score(series: pd.Series) -> pd.Series:
    """Map Education_Level to an ordinal score in [0, 1]."""
    mapping = {
        "High School": 0.2,
        "Associate": 0.4,
        "Bachelor": 0.6,
        "Master": 0.8,
        "PhD": 1.0,
        "Doctorate": 1.0,
    }
    s = series.astype(str).str.strip()
    score = s.map(mapping)
    # fallback: unknown labels -> median (0.6)
    score = score.fillna(0.6)
    return score.astype(float)


def get_skill_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for i in range(config.SKILL_MIN, config.SKILL_MAX + 1):
        c = f"{config.SKILL_PREFIX}{i}"
        if c in df.columns:
            cols.append(c)
    return cols


def compute_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Numeric columns
    for c in [
        config.COL_AVG_SALARY,
        config.COL_YEARS_EXP,
        config.COL_AI_EXPOSURE,
        config.COL_TECH_GROWTH,
        config.COL_AUTOMATION_PROB,
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Education score
    if config.COL_EDU_LEVEL in df.columns:
        df[config.COL_EDU_SCORE] = _education_to_score(df[config.COL_EDU_LEVEL])
    else:
        df[config.COL_EDU_SCORE] = 0.6

    # Skills
    skill_cols = get_skill_columns(df)
    if skill_cols:
        skills = df[skill_cols].apply(pd.to_numeric, errors="coerce")
        df[config.COL_SKILL_MEAN] = skills.mean(axis=1)
        df[config.COL_SKILL_STD] = skills.std(axis=1).fillna(0.0)

        # breadth: how many skills above a small threshold
        df[config.COL_SKILL_BREADTH] = (skills > 0.35).sum(axis=1).astype(float)

        # balance: higher when skills are more evenly distributed (lower std)
        # convert to (0..1) then to a stable numeric measure
        df[config.COL_SKILL_BALANCE] = (1.0 / (1.0 + df[config.COL_SKILL_STD])).clip(0.0, 1.0)
    else:
        df[config.COL_SKILL_MEAN] = np.nan
        df[config.COL_SKILL_STD] = np.nan
        df[config.COL_SKILL_BREADTH] = 0.0
        df[config.COL_SKILL_BALANCE] = 0.5

    # Augmentation proxy: high exposure but lower automation substitution
    exposure = df.get(config.COL_AI_EXPOSURE, pd.Series(0.0, index=df.index)).fillna(0.0)
    auto = df.get(config.COL_AUTOMATION_PROB, pd.Series(0.0, index=df.index)).fillna(0.0)
    df[config.COL_AUGMENTATION_PROXY] = (exposure * (1.0 - auto)).clip(0.0, 1.0)

    return df


def compute_equilibrium(df: pd.DataFrame) -> pd.DataFrame:
    """Compute forces + equilibrium outputs."""
    df = df.copy()

    # --- Forces ---
    # Automation pressure: higher automation probability & exposure => stronger negative pressure
    auto = df[config.COL_AUTOMATION_PROB].fillna(0.0)
    exposure = df[config.COL_AI_EXPOSURE].fillna(0.0)
    automation_pressure_raw = 0.7 * auto + 0.3 * exposure
    df[config.COL_FORCE_AUTOMATION] = _rank_to_unit(automation_pressure_raw, ascending=True)  # high => +1
    # We'll apply it as a negative weight later.

    # Adaptability: education + experience proxy (higher => more adaptable)
    edu = df[config.COL_EDU_SCORE].fillna(0.6)
    exp = df[config.COL_YEARS_EXP].fillna(0.0)
    adaptability_raw = 0.6 * edu + 0.4 * _rank_to_unit(exp, ascending=True).add(1.0).div(2.0)
    df[config.COL_FORCE_ADAPTABILITY] = _rank_to_unit(adaptability_raw, ascending=True)

    # Transferability: skill breadth & balance
    breadth = df[config.COL_SKILL_BREADTH].fillna(0.0)
    balance = df[config.COL_SKILL_BALANCE].fillna(0.5)
    transfer_raw = 0.65 * _rank_to_unit(breadth, ascending=True).add(1.0).div(2.0) + 0.35 * balance
    df[config.COL_FORCE_TRANSFERABILITY] = _rank_to_unit(transfer_raw, ascending=True)

    # Economic demand: tech growth + salary level (salary as a rough demand/complexity proxy)
    tech = df[config.COL_TECH_GROWTH].fillna(1.0)
    salary = df[config.COL_AVG_SALARY].fillna(df[config.COL_AVG_SALARY].median() if config.COL_AVG_SALARY in df.columns else 0.0)
    demand_raw = 0.65 * _rank_to_unit(tech, ascending=True).add(1.0).div(2.0) + 0.35 * _rank_to_unit(salary, ascending=True).add(1.0).div(2.0)
    df[config.COL_FORCE_DEMAND] = _rank_to_unit(demand_raw, ascending=True)

    # AI augmentation: exposure*(1-automation) + skill balance (AI as amplifier)
    aug = df[config.COL_AUGMENTATION_PROXY].fillna(0.0)
    aug_raw = 0.8 * aug + 0.2 * balance
    df[config.COL_FORCE_AUGMENTATION] = _rank_to_unit(aug_raw, ascending=True)

    # --- Equilibrium shift ---
    # Negative weight on automation pressure; positive on others.
    w_auto = 0.45
    w_adapt = 0.20
    w_trans = 0.15
    w_demand = 0.10
    w_aug = 0.10

    raw_shift = (
        -w_auto * df[config.COL_FORCE_AUTOMATION]
        + w_adapt * df[config.COL_FORCE_ADAPTABILITY]
        + w_trans * df[config.COL_FORCE_TRANSFERABILITY]
        + w_demand * df[config.COL_FORCE_DEMAND]
        + w_aug * df[config.COL_FORCE_AUGMENTATION]
    ).clip(-1.0, 1.0)

    # Scale to a human-readable equilibrium shift range (±20%)
    scale = 0.20
    df[config.COL_EQ_SHIFT] = scale * raw_shift

    # Equilibrium center: interpret as "future stability point" around baseline 1.0
    # We keep it in [0.5, 1.5] range to remain readable and not confuse with salary.
    df[config.COL_EQ_CENTER] = (1.0 + df[config.COL_EQ_SHIFT]).clip(0.5, 1.5)

    # Tension: how unstable a role is (automation vs adapt/augment conflict + volatility proxy)
    # Here we treat automation pressure and augmentation as potentially conflicting, plus raw_shift magnitude.
    tension = raw_shift.abs() + (df[config.COL_FORCE_AUTOMATION].abs() * 0.35) + (1.0 - df[config.COL_FORCE_TRANSFERABILITY].add(1.0).div(2.0)) * 0.25
    df[config.COL_TENSION] = tension.clip(0.0, 2.0)

    # Resilience band width increases with tension and automation pressure
    base_width = 0.06
    width = base_width + 0.10 * (df[config.COL_TENSION] / 2.0) + 0.06 * df[config.COL_FORCE_AUTOMATION].abs()
    width = width.clip(0.06, 0.25)

    center = df[config.COL_EQ_CENTER]
    df[config.COL_EQ_LOWER] = (center * (1.0 - width)).clip(0.3, 1.5)
    df[config.COL_EQ_UPPER] = (center * (1.0 + width)).clip(0.3, 1.7)

    return df
