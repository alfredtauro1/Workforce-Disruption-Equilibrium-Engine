from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_RAW = BASE_DIR / "data" / "raw" / "AI_Impact_on_Jobs_2030.csv"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"

REPORTS_DIR = BASE_DIR / "reports"
REPORTS_METRICS_DIR = REPORTS_DIR / "metrics"
REPORTS_FIGURES_DIR = REPORTS_DIR / "figures"

# Column names expected in the Kaggle dataset
COL_JOB_TITLE = "Job_Title"
COL_AVG_SALARY = "Average_Salary"
COL_YEARS_EXP = "Years_Experience"
COL_EDU_LEVEL = "Education_Level"
COL_AI_EXPOSURE = "AI_Exposure_Index"
COL_TECH_GROWTH = "Tech_Growth_Factor"
COL_AUTOMATION_PROB = "Automation_Probability_2030"
COL_RISK_CATEGORY = "Risk_Category"

# Skill columns (Skill_1..Skill_10)
SKILL_PREFIX = "Skill_"
SKILL_MIN = 1
SKILL_MAX = 10

# Engineered columns
COL_EDU_SCORE = "education_score"
COL_SKILL_MEAN = "skill_mean"
COL_SKILL_STD = "skill_std"
COL_SKILL_BREADTH = "skill_breadth"
COL_SKILL_BALANCE = "skill_balance"
COL_AUGMENTATION_PROXY = "augmentation_proxy"

# Force columns
COL_FORCE_AUTOMATION = "force_automation_pressure"
COL_FORCE_ADAPTABILITY = "force_adaptability"
COL_FORCE_TRANSFERABILITY = "force_skill_transferability"
COL_FORCE_DEMAND = "force_economic_demand"
COL_FORCE_AUGMENTATION = "force_ai_augmentation"

# Equilibrium outputs
COL_EQ_SHIFT = "equilibrium_shift"
COL_EQ_CENTER = "equilibrium_center"
COL_EQ_LOWER = "equilibrium_lower"
COL_EQ_UPPER = "equilibrium_upper"
COL_TENSION = "transition_tension"
