# Composite Cricket Analytics API

This API combines three cricket analytics models into one FastAPI service.

## Endpoints

### 1. `/api/v1/expected-fantasy-points`
Calculates the expected fantasy points for a player using:
- weighted expected runs
- weighted expected wickets
- weighted expected catches

This endpoint calls the **Fantasy Helper API** to compute weighted averages.

---

### 2. `/api/v1/opponent-performance`
Predicts player performance against a target opponent using Bayesian weighting.

This endpoint calls the **Bayesian Helper API** to compute the credibility factor.

---

### 3. `/api/v1/player/form-trend`
Calculates whether the player's recent form is:
- Rising
- Stable
- Declining

This endpoint calls the **Form Trend Helper API** to compute exponential weights.

---

## Helper APIs used

### Fantasy Helper API
Used for:
- weighted runs
- weighted wickets
- weighted catches

---

### Bayesian Helper API
Used for:
- credibility factor calculation

---

### Form Trend Helper API
Used for:
- exponential weights calculation

---

## Additional Endpoints

### `/`
Home route

### `/health`
Health check route

---

## Deployment

Deploy the composite API and the 3 helper APIs separately on Render.

Helper API URLs are configured in:

`config.py`
