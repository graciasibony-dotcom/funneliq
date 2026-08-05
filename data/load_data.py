import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()
supabase_url = os.environ["SUPABASE_URL"]
supabase_key = os.environ["SUPABASE_SERVICE_KEY"]

# יוצרים חיבור פעיל ל-Supabase
supabase = create_client(supabase_url, supabase_key)

#  קוראים את ה-CSV לתוך טבלת pandas
df = pd.read_csv("data/funnel_marketing_data.csv")

df = df.astype(object).where(pd.notnull(df), None)

#  ממירים ל-JSON records - הפורמט ש-Supabase מצפה לו
records = df.to_dict(orient="records")

#  שולחים בבת אחת (batch insert)
response = supabase.table("funnel_data").insert(records).execute()

print(f"Loaded {len(records)} rows into funnel_data.")