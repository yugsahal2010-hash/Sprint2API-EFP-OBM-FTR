from fastapi import FastAPI
from schemas import *
from services import *
from fastapi import HTTPException

app = FastAPI()

@app.get("/")
def home():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/expected-fantasy-points", response_model=FantasyPointsResponse)
def expected_fantasy_points(payload: FantasyPointsRequest):
    try:
        return compute_expected_fantasy_points(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/opponent-bayesian", response_model=OpponentPerformanceResponse)
def opponent_bayesian(payload: OpponentPerformanceRequest):
    return compute_opponent_performance(payload)

@app.post("/form-trend-regression", response_model=FormTrendResponse)
def form_trend(payload: FormTrendRequest):
    return compute_form_trend(payload)
