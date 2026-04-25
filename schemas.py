from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class PlayerRole(str, Enum):
    batter = "batter"
    bowler = "bowler"
    all_rounder = "all_rounder"


class MatchPerformance(BaseModel):
    runs: float
    wickets: float
    catches: float


class FantasyPointsRequest(BaseModel):
    player_id: str
    player_name: str
    role: PlayerRole
    matches: List[MatchPerformance]
    batting_points_per_run: float = 1.0
    bowling_points_per_wicket: float = 25.0
    fielding_points_per_catch: float = 8.0


class DerivedMetrics(BaseModel):
    expected_runs: float
    expected_wickets: float
    expected_catches: float
    batting_points: float
    bowling_points: float
    fielding_points: float
    weighted_batting_points: float
    weighted_bowling_points: float
    weighted_fielding_points: float


class FantasyPointsResponse(BaseModel):
    player_id: str
    player_name: str
    role: PlayerRole
    expected_fantasy_points: float
    selection_rating: str
    derived_metrics: DerivedMetrics
    interpretation: str


class MatchRecord(BaseModel):
    score: float = Field(..., ge=0)
    opponent_team: str


class OpponentPerformanceRequest(BaseModel):
    player_id: str
    player_name: str
    target_opponent: str
    recent_matches: List[MatchRecord]


class CalculationDetails(BaseModel):
    credibility_factor: float
    opponent_weight: float
    overall_weight: float
    expected_score: float
    expected_variability: float
    overall_average_score: float
    opponent_average_score: float
    matches_vs_opponent: int


class OpponentPerformanceResponse(BaseModel):
    player_id: str
    player_name: str
    opponent_team: str
    predicted_score: float
    performance_tier: str
    interpretation: str
    calculation_details: CalculationDetails


class FormTrendRequest(BaseModel):
    player_id: str
    player_name: Optional[str] = None
    performance_scores: List[float]

    @field_validator("performance_scores")
    @classmethod
    def validate_scores(cls, v):
        if len(v) < 3:
            raise ValueError("At least 3 scores required")
        return v


class TrendDetails(BaseModel):
    weights: List[float]
    slope: float
    intercept: float
    r_squared: float
    normalized_slope: float


class FormTrendResponse(BaseModel):
    player_id: str
    player_name: Optional[str]
    trend_label: str
    trend_score: float
    slope: float
    r_squared: float
    confidence: str
    matches_used: int
    details: TrendDetails
    interpretation: str
