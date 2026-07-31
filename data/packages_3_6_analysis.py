"""
FunnelIQ — קוד מרוכז לחבילות עבודה 3-6
=========================================
קובץ זה מכיל את כל הקוד שהורץ עבור חבילות 3-6 (upsell, super-customer,
follow-up dropout, budget optimization). מומלץ להעתיק כל חלק ל-cell נפרד
ב-notebook (04, 05, 06 בהתאמה) ולהריץ בעצמך כדי להבין ולוודא תוצאות.

דרישות מוקדמות:
    pip install pandas numpy matplotlib xgboost lightgbm catboost scikit-learn
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from sklearn.model_selection import (
    cross_val_score, cross_val_predict, StratifiedKFold, KFold, GridSearchCV
)
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

df = pd.read_csv('data/funnel_marketing_data.csv')  # התאימי נתיב אם צריך


# =========================================================================
# חבילה 3 — חיזוי הסתברות ל-Upsell (סיווג)
# =========================================================================
# החלטת leakage: בשונה מ-LTV, כאן נקודת החיזוי היא אחרי סגירת העסקה
# המקורית, ולכן closed/not_closed/calls_to_closed/calls_to_not_closed
# נחשבים לגיטימיים. cumulative_profit, ltv_months, referred מוחרגים.
df_up = df[df['purchased'] == 1].copy()

features_upsell = [
    'ad_budget', 'num_leads', 'leads_answered', 'leads_not_answered',
    'followup_1', 'followup_2', 'followup_3', 'followup_4', 'followup_5',
    'calls_to_closed', 'calls_to_not_closed', 'customer_acquisition_cost',
    'closed', 'not_closed'
]
X_up = df_up[features_upsell]
y_up = df_up['upsell']

models_clf = {
    'XGBoost': xgb.XGBClassifier(
        random_state=42, scale_pos_weight=(y_up == 0).sum() / (y_up == 1).sum()
    ),
    'LightGBM': lgb.LGBMClassifier(random_state=42, verbose=-1, class_weight='balanced'),
    'CatBoost': cb.CatBoostClassifier(
        random_state=42, verbose=0, auto_class_weights='Balanced'
    ),
}

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scoring = {'accuracy': 'accuracy', 'precision': 'precision', 'recall': 'recall', 'f1': 'f1'}

results_upsell = {}
for name, model in models_clf.items():
    row = {m: cross_val_score(model, X_up, y_up, cv=skf, scoring=s).mean()
           for m, s in scoring.items()}
    results_upsell[name] = row

print("=== חבילה 3: תוצאות סיווג upsell ===")
print(pd.DataFrame(results_upsell).T)

# Feature importance (CatBoost — המודל הטוב ביותר)
best_upsell_model = models_clf['CatBoost'].fit(X_up, y_up)
importance_upsell = pd.DataFrame({
    'feature': features_upsell,
    'importance': best_upsell_model.feature_importances_
}).sort_values('importance', ascending=False)
print("\nFeature importance (CatBoost):")
print(importance_upsell)

# חוק עסקי פשוט מול המודל
rule_pred = ((df_up['customer_acquisition_cost'] < 1000) & (df_up['followup_1'] > 22)).astype(int)
model_pred_cv = cross_val_predict(models_clf['CatBoost'], X_up, y_up, cv=skf)

print("\n=== חוק עסקי מול מודל ===")
for label, pred in [('חוק עסקי', rule_pred), ('מודל CatBoost', model_pred_cv)]:
    print(f"{label}: Accuracy={accuracy_score(y_up, pred):.3f}, "
          f"Precision={precision_score(y_up, pred):.3f}, "
          f"Recall={recall_score(y_up, pred):.3f}, "
          f"F1={f1_score(y_up, pred):.3f}")


# =========================================================================
# חבילה 4 — ציון "סופר-לקוח" (referred)
# =========================================================================
# פיצ'רים: נתוני משפך מוקדמים בלבד (לפני סגירת עסקה), כי הניקוד אמור
# לעבוד על לקוח חדש שעדיין לא ידוע איך יסתיים התהליך שלו.
df_ref = df[df['purchased'] == 1].copy()

features_super = [
    'ad_budget', 'num_leads', 'leads_answered', 'leads_not_answered',
    'followup_1', 'followup_2', 'followup_3', 'followup_4', 'followup_5',
    'customer_acquisition_cost'
]
X_ref = df_ref[features_super]
y_ref = (df_ref['referred'] == 'Yes').astype(int)

# Hyperparameter tuning
param_grid = {
    'learning_rate': [0.03, 0.1, 0.2],
    'depth': [4, 6, 8],
    'iterations': [200, 500],
}
base_model = cb.CatBoostClassifier(random_state=42, verbose=0, auto_class_weights='Balanced')
grid = GridSearchCV(base_model, param_grid, scoring='f1', cv=skf, n_jobs=-1)
grid.fit(X_ref, y_ref)
print("\n=== חבילה 4: Hyperparameter tuning ===")
print("Best params:", grid.best_params_)
print("Best F1 (CV):", grid.best_score_)

# מודל סופי + פייפליין ניקוד 0-100
final_model = cb.CatBoostClassifier(
    **grid.best_params_, random_state=42, verbose=0, auto_class_weights='Balanced'
)
final_model.fit(X_ref, y_ref)
proba = final_model.predict_proba(X_ref)[:, 1]
df_ref['super_customer_score'] = (proba * 100).round(1)

# פרופיל סופר-לקוחות (הגדרה: referred=Yes, upsell=1, tenure מעל חציון)
median_ltv = df_ref['ltv_months'].median()
super_mask = (
    (df_ref['referred'] == 'Yes') & (df_ref['upsell'] == 1) &
    (df_ref['ltv_months'] > median_ltv)
)
super_customers = df_ref[super_mask]
regular_customers = df_ref[~super_mask]

total_profit = df_ref['cumulative_profit'].sum()
super_profit = super_customers['cumulative_profit'].sum()
print("\n=== פרופיל סופר-לקוחות ===")
print(f"מספר: {len(super_customers)} מתוך {len(df_ref)} "
      f"({len(super_customers)/len(df_ref)*100:.1f}%)")
print(f"אחוז מהרווח הכולל: {super_profit/total_profit*100:.1f}%")
print(f"CAC ממוצע — סופר-לקוחות: {super_customers['customer_acquisition_cost'].mean():.1f}")
print(f"CAC ממוצע — שאר: {regular_customers['customer_acquisition_cost'].mean():.1f}")


# =========================================================================
# חבילה 5 — פרדוקס המעקבים (dropout ניתוח תיאורי)
# =========================================================================
stages = ['num_leads', 'followup_1', 'followup_2', 'followup_3', 'followup_4', 'followup_5']
sums = df[stages].sum()

print("\n=== חבילה 5: נשירה בכל שלב מעקב ===")
for i in range(1, len(stages)):
    prev, curr = stages[i - 1], stages[i]
    dropout = 1 - sums[curr] / sums[prev]
    print(f"{prev} -> {curr}: נשירה {dropout*100:.1f}%")

# ויזואליזציה
dropouts, labels = [], []
for i in range(1, len(stages)):
    prev, curr = stages[i - 1], stages[i]
    dropouts.append((1 - sums[curr] / sums[prev]) * 100)
    labels.append(f'{prev}\n->{curr}')

plt.figure(figsize=(8, 5))
plt.bar(labels, dropouts)
plt.ylabel('אחוז נשירה (%)')
plt.title('שיעור נשירה בכל שלב מעקב')
plt.tight_layout()
plt.savefig('followup_dropout.png', dpi=120)
plt.show()

print(f"\nclosed מתוך followup_5: {df['closed'].sum()/sums['followup_5']*100:.1f}%")
print(f"closed מתוך num_leads: {df['closed'].sum()/sums['num_leads']*100:.1f}%")


# =========================================================================
# חבילה 6 — אופטימיזציית תקציב
# =========================================================================
# פיצ'ר יחיד: ad_budget בלבד, כי זה המשתנה שבפועל נשלט בהחלטת ההקצאה.
df_profit = df.dropna(subset=['cumulative_profit'])
X_budget = df_profit[['ad_budget']]
y_profit = df_profit['cumulative_profit']

profit_model = cb.CatBoostRegressor(random_state=42, verbose=0)
kf = KFold(n_splits=5, shuffle=True, random_state=42)
rmse = -cross_val_score(profit_model, X_budget, y_profit, cv=kf,
                         scoring='neg_root_mean_squared_error')
r2 = cross_val_score(profit_model, X_budget, y_profit, cv=kf, scoring='r2')
print(f"\n=== חבילה 6: מודל cumulative_profit ~ ad_budget ===")
print(f"RMSE: {rmse.mean():.1f}, R2: {r2.mean():.3f}")

profit_model.fit(X_budget, y_profit)

# מציאת גודל קמפיין אופטימלי (רווח-לשקל מקסימלי), בתוך טווח הדאטה בלבד
grid_budgets = np.arange(500, 20001, 250)
preds = profit_model.predict(pd.DataFrame({'ad_budget': grid_budgets}))
profit_per_shekel = preds / grid_budgets
best_idx = np.argmax(profit_per_shekel)
optimal_budget = grid_budgets[best_idx]
print(f"תקציב אופטימלי לקמפיין בודד: {optimal_budget}")

# סימולציית אסטרטגיות הקצאה עבור תקציב חודשי כולל
TOTAL_MONTHLY_BUDGET = 50000
strategies = {
    'קמפיין ענק אחד': [TOTAL_MONTHLY_BUDGET],  # אזהרה: מחוץ לטווח הדאטה!
    '5 קמפיינים גדולים': [10000] * 5,
    '10 קמפיינים בינוניים': [5000] * 10,
    '25 קמפיינים קטנים (אופטימלי)': [2000] * 25,
    '50 קמפיינים זעירים': [1000] * 50,
}

print("\n=== סימולציית הקצאת תקציב ===")
for name, budgets in strategies.items():
    in_range = all(b <= 20000 for b in budgets)
    preds_sim = profit_model.predict(pd.DataFrame({'ad_budget': budgets}))
    print(f"{name}: רווח כולל צפוי = {preds_sim.sum():,.0f} "
          f"{'' if in_range else '(⚠️ מחוץ לטווח הדאטה — אקסטרפולציה לא אמינה)'}")
