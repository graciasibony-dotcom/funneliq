import os
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from supabase import Client, create_client

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

def get_current_user(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):]

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_response.user

def get_user_supabase_client(authorization: str = Header(None)) -> Client:
    token = authorization[len("Bearer "):]

    user_client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    user_client.postgrest.auth(token)

    return user_client

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/campaigns/count")
def campaigns_count(
    current_user = Depends(get_current_user),
    db: Client = Depends(get_user_supabase_client)
):
    response = db.table("funnel_data").select("*", count="exact").execute()
    return {"total_campaigns": response.count}