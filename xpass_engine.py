"""Expected pass completion (xP) — logistic model analogous to xG for passes.

xPV (expected pass *value*) lives in xp_engine / xp_m4. This module models
P(completion | origin, destination) from coordinates only.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import passes_engine as pe
import xp_engine as xe
import xp_study_engine as xse

XPASS_MODEL_VERSION = "xpass_logistic_od12x8_dist_prog_lat_v3"
XPASS_HARD_COE_THRESHOLD = 0.65
XPASS_HARD_COE_MIN_ATTEMPTS = 25
XPASS_COL = "xpass"
XPASS_RESIDUAL_COL = "xpass_residual"
MIN_PLAYER_PASSES = 100
MIN_MINUTES = 450

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
XPASS_MODEL_PATH = MODELS_DIR / "xpass_logistic.joblib"
XPASS_META_PATH = MODELS_DIR / "xpass_meta.json"
XPASS_PLAYERS_JSON = DATA_DIR / "xpass_european_players.json"

GRID = xse.STUDY_GRID


def _n_origin_cells() -> int:
    return GRID.od_origin_rows * GRID.od_origin_cols


def _n_dest_cells() -> int:
    return GRID.od_dest_rows * GRID.od_dest_cols


def _geometry_features(df: pd.DataFrame) -> np.ndarray:
    dist = df["pass_distance"].to_numpy(dtype=float)
    dist_safe = np.maximum(dist, 0.5)
    dx = df["x_end"].to_numpy(dtype=float) - df["x_start"].to_numpy(dtype=float)
    dy = df["y_end"].to_numpy(dtype=float) - df["y_start"].to_numpy(dtype=float)
    progress = df["progress_ratio"].to_numpy(dtype=float) if "progress_ratio" in df.columns else (
        xse._progress_ratio_series(df).to_numpy(dtype=float)
    )
    lateral = np.abs(dy) / dist_safe
    forward = dx / dist_safe
    return np.column_stack([
        dist,
        dist ** 2,
        np.sqrt(dist),
        progress,
        lateral,
        forward,
        lateral * dist,
        forward * dist,
    ])


def build_xpass_design_matrix(df: pd.DataFrame, grid: xse.GridConfig = GRID) -> sparse.csr_matrix:
    """Sparse features: geometry + origin/destination cells."""
    geom = _geometry_features(df)
    n = len(df)
    o_idx = df["oy"].to_numpy(int) * grid.od_origin_cols + df["ox"].to_numpy(int)
    d_idx = df["dy"].to_numpy(int) * grid.od_dest_cols + df["dx"].to_numpy(int)
    n_o = _n_origin_cells()
    n_d = _n_dest_cells()
    return sparse.hstack([
        sparse.csr_matrix(geom),
        sparse.csr_matrix((np.ones(n), (np.arange(n), o_idx)), shape=(n, n_o)),
        sparse.csr_matrix((np.ones(n), (np.arange(n), d_idx)), shape=(n, n_d)),
    ])


def attach_od_cells_all(passes: pd.DataFrame, grid: xse.GridConfig = GRID) -> pd.DataFrame:
    """Origin/destination cells for every pass with an end coordinate (won or lost)."""
    out = passes.copy()
    mask = out["has_end"].fillna(False)
    out["ox"] = -1
    out["oy"] = -1
    out["dx"] = -1
    out["dy"] = -1
    if not mask.any():
        out["distance_band"] = xse._distance_band_series(out["pass_distance"])
        return out
    sub = out.loc[mask]
    ox, oy = xse._cell_indices(
        sub["x_start"].to_numpy(dtype=float),
        sub["y_start"].to_numpy(dtype=float),
        cols=grid.od_origin_cols,
        rows=grid.od_origin_rows,
    )
    dx, dy = xse._cell_indices(
        sub["x_end"].to_numpy(dtype=float),
        sub["y_end"].to_numpy(dtype=float),
        cols=grid.od_dest_cols,
        rows=grid.od_dest_rows,
    )
    out.loc[mask, "ox"] = ox
    out.loc[mask, "oy"] = oy
    out.loc[mask, "dx"] = dx
    out.loc[mask, "dy"] = dy
    out["distance_band"] = xse._distance_band_series(out["pass_distance"])
    return out


def _prepare_passes(passes: pd.DataFrame) -> pd.DataFrame:
    work = passes.loc[passes["has_end"].fillna(False)].copy()
    if work.empty:
        return work
    if "ox" not in work.columns or (work["ox"] < 0).any():
        work = attach_od_cells_all(work, GRID)
    valid = (work["ox"] >= 0) & (work["dx"] >= 0)
    work = work.loc[valid].copy()
    if "progress_ratio" not in work.columns:
        work["progress_ratio"] = xse._progress_ratio_series(work)
    return work


def fit_xpass_model(
    train_passes: pd.DataFrame,
    *,
    c: float = 0.08,
    max_iter: int = 400,
) -> Pipeline:
    train = _prepare_passes(train_passes)
    if train.empty:
        raise RuntimeError("No passes available for xPass training.")
    X = build_xpass_design_matrix(train)
    y = train["is_won"].astype(int).to_numpy()
    model = Pipeline([
        ("scaler", StandardScaler(with_mean=False)),
        ("logistic", LogisticRegression(
            C=c,
            solver="saga",
            max_iter=max_iter,
            n_jobs=-1,
            random_state=42,
        )),
    ])
    model.fit(X, y)
    return model


def score_passes_xpass(
    passes: pd.DataFrame,
    model: Pipeline,
) -> pd.DataFrame:
    out = passes.copy()
    out[XPASS_COL] = np.nan
    out[XPASS_RESIDUAL_COL] = np.nan
    work = _prepare_passes(out)
    if work.empty:
        return out
    probs = model.predict_proba(build_xpass_design_matrix(work))[:, 1]
    out.loc[work.index, XPASS_COL] = probs
    won = work["is_won"].astype(int).to_numpy(dtype=float)
    out.loc[work.index, XPASS_RESIDUAL_COL] = won - probs
    return out


def _match_level_cv_metrics(
    passes: pd.DataFrame,
    *,
    n_splits: int = 5,
    c: float = 0.08,
) -> dict[str, float]:
    work = _prepare_passes(passes)
    if work.empty or "event_id" not in work.columns:
        return {}
    groups = work["event_id"].astype(int).to_numpy()
    unique_matches = np.unique(groups)
    if len(unique_matches) < n_splits:
        n_splits = max(2, len(unique_matches))
    gkf = GroupKFold(n_splits=n_splits)
    y_all: list[int] = []
    p_all: list[float] = []
    for train_idx, test_idx in gkf.split(work, groups=groups):
        train = work.iloc[train_idx]
        test = work.iloc[test_idx]
        y_train = train["is_won"].astype(int).to_numpy()
        if len(np.unique(y_train)) < 2 or len(np.unique(test["is_won"].astype(int))) < 1:
            continue
        model = fit_xpass_model(train, c=c)
        probs = model.predict_proba(build_xpass_design_matrix(test))[:, 1]
        y_all.extend(test["is_won"].astype(int).tolist())
        p_all.extend(probs.tolist())
    if not y_all:
        return {}
    y_arr = np.asarray(y_all, dtype=int)
    p_arr = np.clip(np.asarray(p_all, dtype=float), 1e-6, 1 - 1e-6)
    return {
        "brier_score": float(brier_score_loss(y_arr, p_arr)),
        "log_loss": float(log_loss(y_arr, p_arr)),
        "roc_auc": float(roc_auc_score(y_arr, p_arr)),
        "completion_rate": float(y_arr.mean()),
        "mean_predicted": float(p_arr.mean()),
    }


def _per90(value: float, minutes: float | None) -> float | None:
    if minutes is None or minutes <= 0:
        return None
    return float(value) * 90.0 / float(minutes)


def aggregate_player_xpass_metrics(
    scored: pd.DataFrame,
    *,
    minutes_info: dict[str, dict] | None = None,
    min_passes: int = MIN_PLAYER_PASSES,
) -> list[dict]:
    minutes_info = minutes_info or {}
    players: list[dict] = []
    for pid, grp in scored.groupby("player_id", sort=False):
        pid = str(pid)
        attempts = grp[grp[XPASS_COL].notna()]
        n_attempts = len(attempts)
        if n_attempts < min_passes:
            continue
        mins = minutes_info.get(pid, {})
        minutes = mins.get("minutes")
        if minutes is not None and float(minutes) < MIN_MINUTES:
            continue

        xpass = attempts[XPASS_COL].to_numpy(dtype=float)
        residual = attempts[XPASS_RESIDUAL_COL].to_numpy(dtype=float)
        won = attempts["is_won"].astype(int).to_numpy()
        completed = int(won.sum())
        expected = float(xpass.sum())
        actual_pct = completed / n_attempts
        expected_pct = expected / n_attempts
        coe_pct = actual_pct - expected_pct
        coe_count = completed - expected

        hard_mask = xpass < XPASS_HARD_COE_THRESHOLD
        hard_attempts = int(hard_mask.sum())
        hard_coe_pct = None
        if hard_attempts >= XPASS_HARD_COE_MIN_ATTEMPTS:
            hard_won = int(won[hard_mask].sum())
            hard_exp = float(xpass[hard_mask].sum())
            hard_coe_pct = (hard_won / hard_attempts) - (hard_exp / hard_attempts)

        long_mask = attempts["distance_band"].astype(str) == "long" if "distance_band" in attempts.columns else (
            attempts["pass_distance"].to_numpy(dtype=float) > xse.XP_DISTANCE_BAND_MAX_SHORT_M
        )
        long_attempts = int(long_mask.sum()) if hasattr(long_mask, "sum") else 0
        long_coe_pct = None
        if long_attempts >= 25:
            long_won = int(won[long_mask].sum())
            long_exp = float(xpass[long_mask].sum())
            long_coe_pct = (long_won / long_attempts) - (long_exp / long_attempts)

        residual_total = float(residual.sum())
        difficulty_mean = float((1.0 - xpass).mean())

        xp_m4 = grp.loc[grp["is_won"] & grp["has_end"], "xp_m4"] if "xp_m4" in grp.columns else pd.Series(dtype=float)
        xpv_per_pass = float(xp_m4.mean()) if len(xp_m4) else None
        xpv_total = float(xp_m4.sum()) if len(xp_m4) else None

        players.append({
            "player_id": pid,
            "player_name": str(grp["player_name"].iloc[0]),
            "position": str(grp["position"].iloc[0]) if "position" in grp.columns else "—",
            "team": mins.get("team", str(grp["team"].mode().iloc[0] if "team" in grp.columns and not grp["team"].mode().empty else "—")),
            "league": pe._european_league_label(str(grp["league_source"].mode().iloc[0])) if "league_source" in grp.columns and not grp["league_source"].mode().empty else "—",
            "minutes": minutes,
            "pass_attempts": n_attempts,
            "passes_completed": completed,
            "pass_completion_pct": round(actual_pct * 100.0, 2),
            "xpass_expected_pct": round(expected_pct * 100.0, 2),
            "xpass_coe_pct": round(coe_pct * 100.0, 2),
            "xpass_coe_count": round(coe_count, 1),
            "xpass_residual_total": round(residual_total, 2),
            "xpass_residual_p90": round(_per90(residual_total, minutes) or 0.0, 3),
            "xpass_difficulty_mean": round(difficulty_mean, 4),
            "xpass_hard_coe_pct": round(hard_coe_pct * 100.0, 2) if hard_coe_pct is not None else None,
            "xpass_long_coe_pct": round(long_coe_pct * 100.0, 2) if long_coe_pct is not None else None,
            "xpass_attempts_p90": round(_per90(n_attempts, minutes) or 0.0, 1),
            "xpv_per_pass": round(xpv_per_pass, 4) if xpv_per_pass is not None else None,
            "xpv_total": round(xpv_total, 1) if xpv_total is not None else None,
            "xpv_per_pass_p90": round(_per90(xpv_total or 0.0, minutes) or 0.0, 3) if xpv_total is not None else None,
        })
    return players


def _attach_ranks(players: list[dict]) -> None:
    if not players:
        return

    def _rank(metric: str, reverse: bool = True) -> None:
        eligible = [p for p in players if p.get(metric) is not None]
        eligible.sort(key=lambda p: float(p[metric]), reverse=reverse)
        for i, p in enumerate(eligible, start=1):
            p[f"{metric}_rank"] = i

    _rank("xpass_coe_pct")
    _rank("xpass_residual_total")
    _rank("xpass_residual_p90")
    _rank("xpass_hard_coe_pct")
    _rank("xpass_difficulty_mean")
    _rank("xpv_per_pass")
    _rank("xpv_per_pass_p90")


def build_and_save_european_xpass(
    *,
    refit: bool = True,
    c: float = 0.08,
) -> dict:
    """Train xPass on European season, score passes, persist model + player JSON."""
    season = xe.load_european_league_season_passes()
    if season.empty:
        raise RuntimeError("European season parquet is empty.")

    cv_metrics = _match_level_cv_metrics(season, c=c)
    model = fit_xpass_model(season, c=c) if refit else joblib.load(XPASS_MODEL_PATH)
    if refit:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, XPASS_MODEL_PATH)

    scored = score_passes_xpass(season, model)
    minutes_info = pe._minutes_from_passes_frame(scored)
    players = aggregate_player_xpass_metrics(scored, minutes_info=minutes_info)
    _attach_ranks(players)

    train = _prepare_passes(scored)
    train_probs = model.predict_proba(build_xpass_design_matrix(train))[:, 1]
    y = train["is_won"].astype(int).to_numpy()
    full_metrics = {
        "brier_score": float(brier_score_loss(y, train_probs)),
        "log_loss": float(log_loss(y, train_probs)),
        "roc_auc": float(roc_auc_score(y, train_probs)),
        "completion_rate": float(y.mean()),
        "mean_predicted": float(train_probs.mean()),
    }

    meta = {
        "version": XPASS_MODEL_VERSION,
        "model_type": "logistic_l2",
        "c": c,
        "grid": GRID.key,
        "n_passes_scored": int(len(train)),
        "n_players": len(players),
        "cv_match_metrics": cv_metrics,
        "full_sample_metrics": full_metrics,
        "min_player_passes": MIN_PLAYER_PASSES,
        "min_minutes": MIN_MINUTES,
    }
    XPASS_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    payload = {
        "meta": meta,
        "players": players,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    XPASS_PLAYERS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return meta


def load_xpass_player_bundle() -> dict:
    """Load precomputed xPass player metrics (lightweight JSON for UI)."""
    if not XPASS_PLAYERS_JSON.is_file():
        return {"meta": {}, "players": []}
    return json.loads(XPASS_PLAYERS_JSON.read_text(encoding="utf-8"))


XP_PLAYER_MERGE_KEYS: tuple[str, ...] = (
    "xpass_residual_p90",
    "xpass_hard_coe_pct",
    "xpass_coe_pct",
    "xpass_expected_pct",
    "pass_attempts",
)


def attach_xpass_metrics_to_players(players: list[dict]) -> None:
    """Merge offline xPass execution metrics into xP player dicts by player_id."""
    bundle = load_xpass_player_bundle()
    by_id = {str(p["player_id"]): p for p in bundle.get("players", [])}
    for player in players:
        src = by_id.get(str(player.get("player_id")))
        if not src:
            continue
        for key in XP_PLAYER_MERGE_KEYS:
            if src.get(key) is not None:
                player[key] = src[key]
