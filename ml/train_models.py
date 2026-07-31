import pandas as pd
import catboost as cb
import json
import os

DATA_PATH = 'data/funnel_marketing_data.csv'
MODELS_DIR = 'models'
os.makedirs(MODELS_DIR, exist_ok=True)
df = pd.read_csv(DATA_PATH)

FOLLOWUP_COLS = ['followup_1', 'followup_2', 'followup_3', 'followup_4', 'followup_5']

saved_files = []


# =========================================================================
# מודל 1 - LTV (regressor, חבילה 2)
# =========================================================================
df_ltv = df[df['purchased'] == 1].copy()

features_ltv = [
    'ad_budget', 'num_leads', 'leads_answered', 'leads_not_answered',
    *FOLLOWUP_COLS, 'customer_acquisition_cost'
]
X_ltv = df_ltv[features_ltv]
y_ltv = df_ltv['ltv_months']

ltv_model = cb.CatBoostRegressor(random_state=42, verbose=0)
ltv_model.fit(X_ltv, y_ltv)

ltv_model_path = os.path.join(MODELS_DIR, 'ltv_model.cbm')
ltv_model.save_model(ltv_model_path)
saved_files.append(ltv_model_path)


# =========================================================================
# מודל 2 - Upsell (classifier, חבילה 3)
# =========================================================================
df_up = df[df['purchased'] == 1].copy()

features_upsell = [
    'ad_budget', 'num_leads', 'leads_answered', 'leads_not_answered',
    *FOLLOWUP_COLS, 'calls_to_closed', 'calls_to_not_closed',
    'customer_acquisition_cost', 'closed', 'not_closed'
]
X_up = df_up[features_upsell]
y_up = df_up['upsell']

upsell_model = cb.CatBoostClassifier(
    random_state=42, verbose=0, auto_class_weights='Balanced'
)
upsell_model.fit(X_up, y_up)

upsell_model_path = os.path.join(MODELS_DIR, 'upsell_model.cbm')
upsell_model.save_model(upsell_model_path)
saved_files.append(upsell_model_path)


# =========================================================================
# מודל 3 - Super Customer Score (classifier, חבילה 4)
# =========================================================================
df_ref = df[df['purchased'] == 1].copy()

features_super = [
    'ad_budget', 'num_leads', 'leads_answered', 'leads_not_answered',
    *FOLLOWUP_COLS, 'customer_acquisition_cost'
]
X_ref = df_ref[features_super]
y_ref = (df_ref['referred'] == 'Yes').astype(int)

super_customer_model = cb.CatBoostClassifier(
    depth=8, iterations=200, learning_rate=0.03,
    random_state=42, verbose=0, auto_class_weights='Balanced'
)
super_customer_model.fit(X_ref, y_ref)

super_customer_model_path = os.path.join(MODELS_DIR, 'super_customer_model.cbm')
super_customer_model.save_model(super_customer_model_path)
saved_files.append(super_customer_model_path)


# =========================================================================
# מודל 4 - Budget/Profit (regressor, חבילה 6)
# =========================================================================
df_profit = df.dropna(subset=['cumulative_profit'])

X_budget = df_profit[['ad_budget']]
y_profit = df_profit['cumulative_profit']

budget_profit_model = cb.CatBoostRegressor(random_state=42, verbose=0)
budget_profit_model.fit(X_budget, y_profit)

preds_train = budget_profit_model.predict(X_budget)
rmse_train = ((preds_train - y_profit) ** 2).mean() ** 0.5
ss_res = ((y_profit - preds_train) ** 2).sum()
ss_tot = ((y_profit - y_profit.mean()) ** 2).sum()
r2_train = 1 - ss_res / ss_tot
print(f"Budget/Profit model (train): R2={r2_train:.3f}, RMSE={rmse_train:.1f} "
      f"(מתועד: R2≈0.664, RMSE≈6,489 — CV, לא train, אז ציפייה לטווח דומה בלבד)")

budget_profit_model_path = os.path.join(MODELS_DIR, 'budget_profit_model.cbm')
budget_profit_model.save_model(budget_profit_model_path)
saved_files.append(budget_profit_model_path)


# =========================================================================
# תובנות נשירת מעקבים (לא מודל - ניתוח תיאורי, חבילה 5)
# =========================================================================
stage_cols = ['num_leads', *FOLLOWUP_COLS]
sums = df[stage_cols].sum()

stages = []
dropout_pct = []
for i in range(1, len(stage_cols)):
    prev, curr = stage_cols[i - 1], stage_cols[i]
    dropout = (1 - sums[curr] / sums[prev]) * 100
    stages.append(f'{prev}->{curr}')
    dropout_pct.append(round(dropout, 1))

best_idx = dropout_pct.index(min(dropout_pct))
best_stage = stages[best_idx]

if dropout_pct[4] > dropout_pct[3]:
    recommendation = (
        f"השלב היעיל ביותר הוא {best_stage} (נשירה של {dropout_pct[best_idx]}%). "
        f"השלב האחרון ({stages[4]}) מראה נשירה גבוהה יותר ({dropout_pct[4]}%) "
        f"מהשלב שלפניו ({stages[3]}, {dropout_pct[3]}%). "
        f"מומלץ להמשיך את המעקב לפחות עד {best_stage.split('->')[1]}, "
        f"ולבדוק לעומק בנפרד את {stages[4]} (למשל A/B טסט על ניסוח או תזמון) "
        f"לפני שמוותרים עליו."
    )
else:
    recommendation = (
        f"השלב היעיל ביותר הוא {best_stage} (נשירה של {dropout_pct[best_idx]}%). "
        f"השלב האחרון ({stages[4]}) אינו מראה עלייה בנשירה לעומת השלב שלפניו."
    )

dropout_insights = {
    'stages': stages,
    'dropout_pct': dropout_pct,
    'recommendation': recommendation,
}

dropout_insights_path = os.path.join(MODELS_DIR, 'followup_dropout_insights.json')
with open(dropout_insights_path, 'w', encoding='utf-8') as f:
    json.dump(dropout_insights, f, ensure_ascii=False, indent=2)
saved_files.append(dropout_insights_path)


# =========================================================================
# סיכום
# =========================================================================
print("\n=== קבצים שנשמרו ב-models/ ===")
for path in saved_files:
    size_kb = os.path.getsize(path) / 1024
    print(f"{path}: {size_kb:.1f} KB")
