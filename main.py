from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}


from fastapi import FastAPI
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/campaigns/count")
def campaigns_count():
    response = supabase.table("funnel_data").select("*", count="exact").execute()
    return {"total_campaigns": response.count}