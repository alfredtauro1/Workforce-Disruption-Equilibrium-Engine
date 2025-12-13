import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src import config, data_prep, equilibrium


@st.cache_data
def load_data() -> pd.DataFrame:
    return data_prep.load_processed()


def _make_job_options(df: pd.DataFrame) -> list[str]:
    # Create stable, readable options even when titles repeat
    options = []
    for i, r in df.reset_index(drop=True).iterrows():
        title = str(r.get(config.COL_JOB_TITLE, "Unknown"))
        risk = str(r.get(config.COL_RISK_CATEGORY, ""))
        edu = str(r.get(config.COL_EDU_LEVEL, ""))
        options.append(f"[{i}] {title} | Risk: {risk} | Edu: {edu}")
    return options


def main() -> None:
    st.set_page_config(page_title="Workforce Disruption Equilibrium Engine", layout="wide")
    st.title("Workforce Disruption Equilibrium Engine (2030)")
    st.caption("Interpret jobs as equilibrium outcomes shaped by automation pressure, adaptability, skill transferability, demand, and AI augmentation.")

    df = load_data()
    if df.empty:
        st.error("Processed dataset is empty.")
        return

    force_cols = [
        config.COL_FORCE_AUTOMATION,
        config.COL_FORCE_ADAPTABILITY,
        config.COL_FORCE_TRANSFERABILITY,
        config.COL_FORCE_DEMAND,
        config.COL_FORCE_AUGMENTATION,
    ]
    force_labels = [
        "Automation Pressure",
        "Adaptability",
        "Skill Transferability",
        "Economic Demand",
        "AI Augmentation",
    ]

    tab_single, tab_scenario, tab_map = st.tabs(["Single Job", "Scenario Simulator", "Tension Map"])

    # ---------------- Single Job ----------------
    with tab_single:
        st.subheader("Single Job View")

        colA, colB = st.columns([2, 1])
        with colA:
            options = _make_job_options(df.head(1500))  # keep UI snappy
            choice = st.selectbox("Choose a job (first 1500 rows)", options, index=0)
            idx = int(choice.split(']')[0].replace('[', '').strip())
        with colB:
            st.info("Tip: Use the CLI to search the full dataset by title substring.")

        row = df.iloc[idx]

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Equilibrium Center", f"{row[config.COL_EQ_CENTER]:.3f}")
        with m2:
            st.metric("Equilibrium Shift", f"{row[config.COL_EQ_SHIFT]*100:+.2f}%")
        with m3:
            st.metric("Resilience Band", f"[{row[config.COL_EQ_LOWER]:.3f}, {row[config.COL_EQ_UPPER]:.3f}]")
        with m4:
            st.metric("Transition Tension", f"{row[config.COL_TENSION]:.3f}")

        st.markdown("### Force Decomposition")
        force_vals = [row.get(c, np.nan) for c in force_cols]
        fdf = pd.DataFrame({"force": force_labels, "value": force_vals}).set_index("force")
        st.bar_chart(fdf)

        with st.expander("Show raw row (debug)"):
            st.json({k: (float(row[k]) if isinstance(row[k], (int, float, np.floating)) else str(row[k])) for k in row.index})

    # ---------------- Scenario Simulator ----------------
    with tab_scenario:
        st.subheader("Scenario Simulator (Counterfactual Modeling)")
        st.markdown(
            "Use these sliders to simulate policy, adoption, and organizational changes.\n\n"
            "This does **not** predict the future, it shows how equilibrium would **rebalance** under new pressures."
        )

        # Pick a job by index for scenario
        idx = st.number_input("Row index", min_value=0, max_value=int(len(df)-1), value=0, step=1)
        base_row = df.iloc[int(idx)].copy()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ai_adoption = st.slider("AI adoption speed", 0.5, 2.0, 1.0, 0.05,
                                   help="Scales AI exposure and automation probability.")
        with col2:
            regulation = st.slider("Regulation strictness", 0.0, 1.0, 0.2, 0.05,
                                   help="Higher regulation dampens automation probability.")
        with col3:
            education_invest = st.slider("Education investment", 0.0, 1.0, 0.3, 0.05,
                                         help="Boosts adaptability and transferability proxies.")
        with col4:
            corp_incentives = st.slider("Corporate automation incentives", 0.0, 1.0, 0.3, 0.05,
                                        help="Increases automation pressure despite regulation." )

        if st.button("Run Scenario"):
            sim_row = base_row.copy()

            # Apply transformations
            # AI adoption scales exposure and automation
            sim_row[config.COL_AI_EXPOSURE] = float(np.clip(sim_row[config.COL_AI_EXPOSURE] * ai_adoption, 0.0, 1.0))

            auto = float(sim_row[config.COL_AUTOMATION_PROB])
            auto = auto * (1.0 + 0.8 * corp_incentives)         # incentives push
            auto = auto * ai_adoption                            # adoption pushes
            auto = auto * (1.0 - 0.7 * regulation)               # regulation dampens
            sim_row[config.COL_AUTOMATION_PROB] = float(np.clip(auto, 0.0, 1.0))

            # Education investment increases education_score and skill breadth/balance a bit
            # We'll do it by directly modifying engineered columns AFTER recomputation,
            # but we also nudge education level score using a synthetic adjustment.
            sim_row[config.COL_YEARS_EXP] = float(sim_row.get(config.COL_YEARS_EXP, 0.0))  # keep

            # Re-score relative to full dataset so rank-based forces remain meaningful
            df_all = df.copy()
            df_all.iloc[int(idx)] = sim_row

            df_all = equilibrium.compute_engineered_features(df_all)
            # Boost adaptability & transferability via engineered columns
            df_all.loc[df_all.index == int(idx), config.COL_EDU_SCORE] = np.clip(
                df_all.loc[df_all.index == int(idx), config.COL_EDU_SCORE] + 0.25 * education_invest, 0.0, 1.0
            )
            df_all.loc[df_all.index == int(idx), config.COL_SKILL_BREADTH] = np.clip(
                df_all.loc[df_all.index == int(idx), config.COL_SKILL_BREADTH] + 2.0 * education_invest, 0.0, 10.0
            )
            df_all.loc[df_all.index == int(idx), config.COL_SKILL_BALANCE] = np.clip(
                df_all.loc[df_all.index == int(idx), config.COL_SKILL_BALANCE] + 0.15 * education_invest, 0.0, 1.0
            )

            df_all = equilibrium.compute_equilibrium(df_all)
            sim = df_all.iloc[int(idx)]

            st.markdown("### Scenario Results")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Equilibrium Center", f"{sim[config.COL_EQ_CENTER]:.3f}")
            with m2:
                st.metric("Equilibrium Shift", f"{sim[config.COL_EQ_SHIFT]*100:+.2f}%")
            with m3:
                st.metric("Resilience Band", f"[{sim[config.COL_EQ_LOWER]:.3f}, {sim[config.COL_EQ_UPPER]:.3f}]")
            with m4:
                st.metric("Transition Tension", f"{sim[config.COL_TENSION]:.3f}")

            st.markdown("### Scenario Force Decomposition")
            sval = [sim.get(c, np.nan) for c in force_cols]
            sdf = pd.DataFrame({"force": force_labels, "value": sval}).set_index("force")
            st.bar_chart(sdf)

            with st.expander("Scenario raw row"):
                st.json({k: (float(sim[k]) if isinstance(sim[k], (int, float, np.floating)) else str(sim[k])) for k in sim.index})

    # ---------------- Tension Map ----------------
    with tab_map:
        st.subheader("Workforce Tension Map")
        st.markdown(
            "This map is a workforce-wide diagnostic:\n\n"
            "- **x-axis (equilibrium_shift):** direction of pull (pressure vs resilience)\n"
            "- **y-axis (transition_tension):** instability (how hard the role is being pulled)"
        )

        left, right = st.columns([1, 3])
        with left:
            risk_filter = st.multiselect(
                "Risk Category", sorted(df[config.COL_RISK_CATEGORY].dropna().unique().tolist()),
                default=sorted(df[config.COL_RISK_CATEGORY].dropna().unique().tolist())
            )
            edu_filter = st.multiselect(
                "Education Level", sorted(df[config.COL_EDU_LEVEL].dropna().unique().tolist()),
                default=sorted(df[config.COL_EDU_LEVEL].dropna().unique().tolist())
            )
            show_n = st.slider("Max points", 200, 3000, 1200, 100)

        plot_df = df.copy()
        if risk_filter:
            plot_df = plot_df[plot_df[config.COL_RISK_CATEGORY].isin(risk_filter)]
        if edu_filter:
            plot_df = plot_df[plot_df[config.COL_EDU_LEVEL].isin(edu_filter)]

        plot_df = plot_df[[config.COL_EQ_SHIFT, config.COL_TENSION, config.COL_AVG_SALARY, config.COL_JOB_TITLE]].dropna()
        plot_df = plot_df.head(int(show_n))

        st.scatter_chart(plot_df, x=config.COL_EQ_SHIFT, y=config.COL_TENSION)

        with st.expander("Sample rows"):
            st.dataframe(plot_df.head(50))


if __name__ == "__main__":
    main()
