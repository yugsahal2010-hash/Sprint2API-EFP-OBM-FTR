import requests
import math
from schemas import *

FANTASY_URL = "https://fantasypointshelperapi.onrender.com/weighted-average"
BAYESIAN_URL = "https://opponentbayesian-helper.onrender.com/credibility"
TREND_URL = "https://formtrend-helper.onrender.com/weights"

def classify_selection(points):
    if points >= 80:
        return "Elite"
    elif points >= 55:
        return "Strong"
    elif points >= 35:
        return "Average"
    elif points >= 20:
        return "Below Average"
    return "Poor"


def get_role_weights(role):
    role_weights = {
        "batter": (1.0, 0.2, 0.3),
        "bowler": (0.4, 1.0, 0.3),
        "all_rounder": (1.0, 1.0, 0.5)
    }
    return role_weights[role]


def mean(values):
    return sum(values) / len(values) if values else 0


def std_dev(values):
    if len(values) < 2:
        return 1.0
    avg = mean(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def compute_expected_fantasy_points(payload: FantasyPointsRequest):
    runs = requests.post(FANTASY_URL, json={"values": [m.runs for m in payload.matches]}).json()["result"]
    wickets = requests.post(FANTASY_URL, json={"values": [m.wickets for m in payload.matches]}).json()["result"]
    catches = requests.post(FANTASY_URL, json={"values": [m.catches for m in payload.matches]}).json()["result"]

    batting_points = runs * payload.batting_points_per_run
    bowling_points = wickets * payload.bowling_points_per_wicket
    fielding_points = catches * payload.fielding_points_per_catch

    bat_w, bowl_w, field_w = get_role_weights(payload.role.value)

    total = batting_points * bat_w + bowling_points * bowl_w + fielding_points * field_w

    return FantasyPointsResponse(
        player_id=payload.player_id,
        player_name=payload.player_name,
        role=payload.role,
        expected_fantasy_points=round(total, 2),
        selection_rating=classify_selection(total),
        derived_metrics=DerivedMetrics(
            expected_runs=round(runs, 2),
            expected_wickets=round(wickets, 2),
            expected_catches=round(catches, 2),
            batting_points=round(batting_points, 2),
            bowling_points=round(bowling_points, 2),
            fielding_points=round(fielding_points, 2),
            weighted_batting_points=round(batting_points * bat_w, 2),
            weighted_bowling_points=round(bowling_points * bowl_w, 2),
            weighted_fielding_points=round(fielding_points * field_w, 2),
        ),
        interpretation=""
    )


def compute_opponent_performance(payload: OpponentPerformanceRequest):
   
    matches = payload.recent_matches[-20:]
    all_scores = [m.score for m in matches]
    opp_scores = [m.score for m in matches if m.opponent_team.strip().upper() == payload.target_opponent.strip().upper()]
    overall_avg = mean(all_scores)
    overall_std = std_dev(all_scores)    
    if opp_scores:
        opp_avg = mean(opp_scores)
        opp_std = std_dev(opp_scores)
    else:
        opp_avg = overall_avg
        opp_std = overall_std

    matches_vs_opponent = len(opp_scores)

  
    if opp_std < 0.0001:
        credibility = 1.0 # Fallback
    else:
       
        try:
            resp = requests.post(BAYESIAN_URL, json={"overall_std": overall_std, "opponent_std": opp_std}, timeout=5)
            credibility = resp.json().get("result", 1.0)
        except:
            credibility = (overall_std / opp_std) ** 2 if opp_std != 0 else 1.0

   
    opp_weight = matches_vs_opponent / (matches_vs_opponent + credibility) if matches_vs_opponent > 0 else 0
    overall_weight = 1 - opp_weight
    expected_score = opp_weight * opp_avg + overall_weight * overall_avg

 
    expected_variability = math.sqrt(
        overall_weight * (overall_std ** 2) + opp_weight * (opp_std ** 2)
    )

    
    pred = round(expected_score, 2)
    if pred >= 80: tier = "Elite"
    elif pred >= 55: tier = "Strong"
    elif pred >= 35: tier = "Average"
    elif pred >= 20: tier = "Below Average"
    else: tier = "Poor"

    interpretation = f"{payload.player_name} is projected at {pred} against {payload.target_opponent}, classified as {tier}."

  
    return OpponentPerformanceResponse(
        player_id=payload.player_id,
        player_name=payload.player_name,
        opponent_team=payload.target_opponent,
        predicted_score=pred,
        performance_tier=tier,
        interpretation=interpretation,
        calculation_details=CalculationDetails(
            credibility_factor=round(credibility, 4),
            opponent_weight=round(opp_weight, 4),
            overall_weight=round(overall_weight, 4),
            expected_score=round(expected_score, 4),
            expected_variability=round(expected_variability, 4),
            overall_average_score=round(overall_avg, 4),
            opponent_average_score=round(opp_avg, 4),
            matches_vs_opponent=matches_vs_opponent,
        )
    )


def compute_form_trend(payload: FormTrendRequest):
    scores = payload.performance_scores
    n = len(scores)

    weights = requests.post(TREND_URL, json={"n": n}).json()["result"]

    return FormTrendResponse(
        player_id=payload.player_id,
        player_name=payload.player_name,
        trend_label="Stable",
        trend_score=0,
        slope=0,
        r_squared=0,
        confidence="Low",
        matches_used=n,
        details=TrendDetails(
            weights=weights,
            slope=0,
            intercept=0,
            r_squared=0,
            normalized_slope=0
        ),
        interpretation=""
    )
