import requests
import math
from schemas import *
from config import FANTASY_URL, BAYESIAN_URL, TREND_URL

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
        interpretation=(
            f"{payload.player_name} is projected to score "
            f"{round(total, 2)} fantasy points as a "
            f"{payload.role.value}, rated as "
            f"{classify_selection(total).lower()}."
        )
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
    
 
    if n < 2:
        return FormTrendResponse(
            player_id=payload.player_id,
            player_name=payload.player_name,
            trend_label="Stable",
            trend_score=0, slope=0, r_squared=0, confidence="Low",
            matches_used=n,
            details=TrendDetails(weights=[], slope=0, intercept=0, r_squared=0, normalized_slope=0),
            interpretation="Insufficient data for trend analysis."
        )

 
    try:
        response = requests.post(TREND_URL, json={"n": n}, timeout=5)
      
        weights = response.json().get("result")
        if not weights or len(weights) != n:
            raise ValueError("Weight mismatch")
    except Exception as e:
      
        print(f"DEBUG: Trend API failed: {e}")
        weights = [1.0 / n] * n 

  
    scores = payload.performance_scores
    n = len(scores)
    x = list(range(1, n + 1))

    response = requests.post(TREND_URL, json={"n": n}, timeout=5)
    weights = response.json()["result"]

    mean_x = sum(w * xi for xi, w in zip(x, weights))
    mean_y = sum(w * yi for yi, w in zip(scores, weights))

    var_x = sum(w * (xi - mean_x) ** 2 for xi, w in zip(x, weights))
    cov_xy = sum(w * (xi - mean_x) * (yi - mean_y) for xi, yi, w in zip(x, scores, weights))

    slope = cov_xy / var_x if var_x != 0 else 0
    intercept = mean_y - slope * mean_x

    predicted = [intercept + slope * xi for xi in x]

    ss_total = sum(w * (yi - mean_y) ** 2 for yi, w in zip(scores, weights))
    ss_residual = sum(w * (yi - pi) ** 2 for yi, pi, w in zip(scores, predicted, weights))

    r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 1
    r_squared = max(0, min(1, r_squared))

    normalized_slope = slope / mean_y if mean_y != 0 else 0
    trend_score = normalized_slope * r_squared

    if trend_score > 0.02:
        trend_label = "Rising"
    elif trend_score < -0.02:
        trend_label = "Declining"
    else:
        trend_label = "Stable"

    if r_squared >= 0.7:
        confidence = "High"
    elif r_squared >= 0.4:
        confidence = "Moderate"
    else:
        confidence = "Low"

    interpretation = (
        f"{payload.player_name or 'The player'} is {trend_label.lower()} "
        f"with {confidence.lower()} confidence over the last {n} matches."
    )

    return FormTrendResponse(
        player_id=payload.player_id,
        player_name=payload.player_name,
        trend_label=trend_label,
        trend_score=round(trend_score, 4),
        slope=round(slope, 4),
        r_squared=round(r_squared, 4),
        confidence=confidence,
        matches_used=n,
        details=TrendDetails(
            weights=[round(w, 4) for w in weights],
            slope=round(slope, 4),
            intercept=round(intercept, 4),
            r_squared=round(r_squared, 4),
            normalized_slope=round(normalized_slope, 4)
        ),
        interpretation=interpretation
    )
