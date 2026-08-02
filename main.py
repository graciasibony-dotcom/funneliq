import os
import catboost as cb
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import Client, create_client

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MODELS_DIR = "models"


def _load_model(model, filename):
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None
    model.load_model(path)
    return model


ltv_model = _load_model(cb.CatBoostRegressor(), "ltv_model.cbm")
upsell_model = _load_model(cb.CatBoostClassifier(), "upsell_model.cbm")
super_customer_model = _load_model(cb.CatBoostClassifier(), "super_customer_model.cbm")
budget_profit_model = _load_model(cb.CatBoostRegressor(), "budget_profit_model.cbm")


def _require_model(model):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not available")
    return model


class LTVFeatures(BaseModel):
    ad_budget: float
    num_leads: float
    leads_answered: float
    leads_not_answered: float
    followup_1: float
    followup_2: float
    followup_3: float
    followup_4: float
    followup_5: float
    customer_acquisition_cost: float


class UpsellFeatures(BaseModel):
    ad_budget: float
    num_leads: float
    leads_answered: float
    leads_not_answered: float
    followup_1: float
    followup_2: float
    followup_3: float
    followup_4: float
    followup_5: float
    calls_to_closed: float
    calls_to_not_closed: float
    customer_acquisition_cost: float
    closed: float
    not_closed: float


class SuperCustomerFeatures(BaseModel):
    ad_budget: float
    num_leads: float
    leads_answered: float
    leads_not_answered: float
    followup_1: float
    followup_2: float
    followup_3: float
    followup_4: float
    followup_5: float
    customer_acquisition_cost: float


class BudgetProfitFeatures(BaseModel):
    ad_budget: float

def get_current_user(authorization: str = Header(None)):
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization[len("Bearer "):]

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_response.user

def get_user_supabase_client(authorization: str = Header(None)) -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    token = authorization[len("Bearer "):]

    user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    user_client.postgrest.auth(token)

    return user_client

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


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


@app.post("/predict/ltv")
def predict_ltv(features: LTVFeatures, current_user = Depends(get_current_user)):
    model = _require_model(ltv_model)
    row = [[getattr(features, name) for name in LTVFeatures.model_fields]]
    prediction = model.predict(row)[0]
    return {"ltv_months": float(prediction)}


@app.post("/predict/upsell")
def predict_upsell(features: UpsellFeatures, current_user = Depends(get_current_user)):
    model = _require_model(upsell_model)
    row = [[getattr(features, name) for name in UpsellFeatures.model_fields]]
    probability = model.predict_proba(row)[0][1]
    return {
        "upsell_probability": float(probability),
        "upsell_prediction": int(probability >= 0.5),
    }


@app.post("/predict/super-customer")
def predict_super_customer(
    features: SuperCustomerFeatures, current_user = Depends(get_current_user)
):
    model = _require_model(super_customer_model)
    row = [[getattr(features, name) for name in SuperCustomerFeatures.model_fields]]
    probability = model.predict_proba(row)[0][1]
    return {"super_customer_score": round(float(probability) * 100, 1)}


@app.post("/predict/budget-profit")
def predict_budget_profit(
    features: BudgetProfitFeatures, current_user = Depends(get_current_user)
):
    model = _require_model(budget_profit_model)
    row = [[features.ad_budget]]
    prediction = model.predict(row)[0]
    return {"predicted_profit": float(prediction)}
