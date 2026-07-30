# FunnelIQ

כלי פנימי לניתוח וחיזוי נתוני משפך מכירות (funnel data) — מספק API
לשאילתות על נתוני קמפיינים לצורך תובנות וחיזוי.

## ארכיטקטורה

הפרויקט בנוי משלוש שכבות:

- **GitHub Actions (CI)** — כל push או pull request ל-`main` מריץ בדיקת
  lint בסיסית (ruff) על הקוד, כדי לתפוס שגיאות פשוטות לפני מיזוג.
- **Supabase (DB + Auth + RLS)** — מסד הנתונים (Postgres) מאחסן את
  נתוני המשפך. גישה למשתמשים מאומתת מול Supabase Auth (JWT), ו-Row
  Level Security (RLS) אוכף שכל שאילתה מוגבלת למשתמשים מחוברים בלבד.
- **Railway** — פריסת ה-API (FastAPI). כל push ל-`main` ב-GitHub מפעיל
  build ו-deploy אוטומטיים; משתני הסביבה (מפתחות Supabase) מוגדרים
  ישירות בשירות ב-Railway ולא נשמרים בקוד.

## הרצה מקומית

1. יצירת סביבה וירטואלית והתקנת תלויות:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. יצירת קובץ `.env` בשורש הפרויקט עם המשתנים הבאים (בלי לשתף את
   הערכים האמיתיים — ניתן לקבל אותם מ-Supabase Dashboard):

   ```
   SUPABASE_URL=
   SUPABASE_SERVICE_KEY=
   SUPABASE_ANON_KEY=
   ```

3. הרצת השרת:

   ```bash
   uvicorn main:app --reload
   ```

   השרת יעלה על `http://localhost:8000`, וניתן לבדוק זמינות מול
   `http://localhost:8000/health`.

## טעינת נתונים

הטבלה `funnel_data` ריקה לכתחילה. כדי לאכלס אותה מקובץ ה-CSV (לא
נכלל ב-git — יש להשיג אותו בנפרד ולמקם ב-`data/funnel_marketing_data.csv`),
להריץ מתוך שורש הפרויקט, עם אותם משתני `.env`:

```bash
python data/load_data.py
```

## סביבה חיה

https://funneliq-production-f496.up.railway.app
