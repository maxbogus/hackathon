"""Unified neural sequence predictor for route-level boardings (T-177-NEURAL-CONFIG).

Адаптация contest/ecup26-user-value/scripts/neural_models.py:
- SequenceModel: kind ∈ {gru, lstm, mamba} — pure PyTorch, R1 BSD-compatible
- Mamba (S6 selective SSM) — pure PyTorch (no external deps)
- Per-route embedding + hour + calendar features (weekday, is_weekend)
- Attention pooling + MLP head → log1p(boardings)

Refs:
- contest neural_models.py (T3.19/T3.20)
- T-029 (GRU baseline), T-175 (v2_extended), T-177-NEURAL-CONFIG (this)
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import torch
from torch import nn
import torch.nn.functional as F

__all__ = [
    "RouteNeuralConfig",
    "RouteNeuralPredictor",
    "MambaBlock",
    "SequenceModel",
]

# Lazy import torch (тяжёлый, грузим только при использовании)
_torch: Any = None


def _get_torch() -> Any:
    """Lazy import torch."""
    global _torch
    if _torch is None:
        import torch
        _torch = {"torch": torch, "nn": nn}
    return _torch


# ============================================================================
# Config
# ============================================================================

KindStr = Literal["gru", "lstm", "mamba"]


@dataclass(frozen=True)
class RouteNeuralConfig:
    """Single config for any neural sequence encoder."""

    kind: KindStr = "gru"
    hidden: int = 64
    layers: int = 2
    seq_len: int = 336
    lr: float = 3e-4
    epochs: int = 20
    batch_size: int = 256
    seed: int = 42
    route_emb_dim: int = 32
    use_calendar: bool = True


# ============================================================================
# MambaBlock (S6 selective SSM) — pure PyTorch, no external deps
# Adapted from contest neural_models.py (T3.20)
# ============================================================================


class MambaBlock(nn.Module):
    """Selective SSM (S6) block — pure PyTorch.

    Faithful to the Mamba paper (Gu & Dao 2023): causal depthwise conv,
    input-dependent dt/B/C projections, Euler-discretized recurrence.
    Self-implemented для R1 (BSD-compatible).
    """

    def __init__(
        self,
        d_model: int,
        d_state: int = 8,
        d_conv: int = 4,
        expand: int = 2,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_inner = int(expand * d_model)
        self.in_proj = nn.Linear(d_model, self.d_inner * 2, bias=False)
        self.conv = nn.Conv1d(
            self.d_inner,
            self.d_inner,
            d_conv,
            groups=self.d_inner,
            padding=d_conv - 1,
            bias=False,
        )
        self.x_proj = nn.Linear(self.d_inner, d_state * 2 + d_state, bias=False)
        self.dt_proj = nn.Linear(d_state, self.d_inner, bias=True)
        self.A_log = nn.Parameter(
            torch.log(torch.arange(1, d_state + 1)).view(1, d_state).repeat(self.d_inner, 1)
        )
        self.D = nn.Parameter(torch.ones(self.d_inner))
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, _ = x.shape
        xz = self.in_proj(x)
        x0, z = xz.chunk(2, dim=-1)
        x0 = F.silu(x0)
        x0 = self.conv(x0.transpose(1, 2))[..., :L].transpose(1, 2)
        x0 = F.silu(x0)
        dt_bc = self.x_proj(x0)
        dt = F.softplus(self.dt_proj(dt_bc[..., : self.d_state]))
        Bs = dt_bc[..., self.d_state : 2 * self.d_state]
        Cs = dt_bc[..., 2 * self.d_state :]
        A = -torch.exp(self.A_log)
        y = self._scan(x0, dt, A, Bs, Cs)
        return self.out_proj(y * F.silu(z))

    def _scan(self, x, delta, A, B, C, chunk: int = 32) -> torch.Tensor:
        """Sequential scan (стабильная версия для 8GB VRAM)."""
        Bn, L, D = x.shape
        N = A.shape[1]
        dA = torch.exp(delta.unsqueeze(-1) * A)
        xb = delta.unsqueeze(-1) * B.unsqueeze(2) * x.unsqueeze(-1)
        h = torch.zeros(Bn, D, N, device=x.device)
        ys = []
        for t in range(L):
            h = dA[:, t] * h + xb[:, t]
            y_t = torch.einsum("bdn,bn->bd", h, C[:, t])
            ys.append(y_t)
        return torch.stack(ys, dim=1) + self.D * x


# ============================================================================
# Unified SequenceModel
# ============================================================================


class SequenceModel(nn.Module):
    """Unified encoder: embedding → encoder (gru/lstm/mamba) → attention pool → MLP head."""

    def __init__(
        self,
        kind: KindStr,
        input_dim: int,
        hidden: int,
        layers: int,
        n_routes: int,
        route_emb_dim: int = 32,
        use_calendar: bool = True,
    ) -> None:
        super().__init__()
        self.kind = kind
        self.hidden = hidden
        self.route_emb = nn.Embedding(n_routes, route_emb_dim)
        self.hour_emb = nn.Embedding(24, 8)
        self.use_calendar = use_calendar
        if use_calendar:
            self.weekday_emb = nn.Embedding(7, 4)
            self.is_weekend_emb = nn.Embedding(2, 2)
            inp_dim = route_emb_dim + 8 + 4 + 2
        else:
            inp_dim = route_emb_dim + 8
        self.input_proj = nn.Linear(inp_dim, hidden)
        if kind == "gru":
            self.encoder = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        elif kind == "lstm":
            self.encoder = nn.LSTM(hidden, hidden, num_layers=layers, batch_first=True)
        elif kind == "mamba":
            self.encoder = nn.ModuleList(
                [MambaBlock(hidden, d_state=8, expand=2) for _ in range(layers)]
            )
        else:
            raise ValueError(f"Unsupported kind: {kind}")
        self.query = nn.Parameter(torch.randn(hidden) * 0.05)
        self.head = nn.Sequential(
            nn.Linear(hidden, 32), nn.ReLU(), nn.Linear(32, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [B, L, D] где D зависит от use_calendar."""
        B, L, D = x.shape
        hours = x[:, :, 0].long()
        hour_e = self.hour_emb(hours)
        route_idx = torch.randint(0, self.route_emb.num_embeddings, (B,), device=x.device)
        route_e = self.route_emb(route_idx).unsqueeze(1).expand(B, L, -1)
        if self.use_calendar:
            weekdays = x[:, :, 2].long().clamp(0, 6)
            is_wknd = x[:, :, 3].long().clamp(0, 1)
            weekday_e = self.weekday_emb(weekdays)
            wknd_e = self.is_weekend_emb(is_wknd)
            inp = torch.cat([route_e, hour_e, weekday_e, wknd_e], dim=-1)
        else:
            inp = torch.cat([route_e, hour_e], dim=-1)
        h = torch.relu(self.input_proj(inp))
        if self.kind == "gru":
            out, _ = self.encoder(h)
        elif self.kind == "lstm":
            out, _ = self.encoder(h)
        elif self.kind == "mamba":
            out = h
            for blk in self.encoder:
                out = blk(out)
        w = torch.softmax(torch.einsum("blh,h->bl", out, self.query), dim=1)
        pooled = torch.einsum("bl,blh->bh", w, out)
        return self.head(pooled).squeeze(-1)


# ============================================================================
# RouteNeuralPredictor — unified API (заменяет GRURoutePredictor)
# ============================================================================


@dataclass
class RouteNeuralPredictor:
    """Unified neural sequence predictor для route-level boardings.

    fit() / predict_batch() / save() / load() — те же сигнатуры что у
    GRURoutePredictor, но kind ∈ {gru, lstm, mamba}.
    """

    config: RouteNeuralConfig
    model_id: str = "rneural_v1"
    model_: Any = None
    fallback_lookup_: dict[tuple[int, int], float] = field(default_factory=dict)
    route_ids_: list[int] = field(default_factory=list)
    fitted_: bool = False

    def fit(self, history: pd.DataFrame) -> None:
        """Train unified encoder на route-level history."""
        if history.empty:
            raise ValueError("Cannot fit on empty data")
        required = {"timestamp", "route_id", "boardings"}
        missing = required - set(history.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        torch = _get_torch()["torch"]
        nn = _get_torch()["nn"]
        cfg = self.config
        torch.manual_seed(cfg.seed)
        df = history.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        if "hour" not in df.columns:
            df["hour"] = df["timestamp"].dt.hour
        df = df.sort_values(["route_id", "timestamp"]).reset_index(drop=True)
        self.route_ids_ = sorted(df["route_id"].astype(int).unique().tolist())
        n_routes = len(self.route_ids_)
        X_seqs = []
        y_targets = []
        for rid, group in df.groupby("route_id"):
            group = group.sort_values("timestamp").reset_index(drop=True)
            original_len = len(group)
            boardings = group["boardings"].values.astype(np.float32)
            hours = group["hour"].values.astype(np.int64)
            timestamps = pd.to_datetime(group["timestamp"].values)
            weekdays = np.array([ts.weekday() for ts in timestamps], dtype=np.int64)
            is_wknd = (weekdays >= 5).astype(np.int64)
            if original_len < cfg.seq_len:
                pad = cfg.seq_len - original_len
                boardings = np.concatenate(
                    [np.full(pad, boardings[-1], dtype=np.float32), boardings]
                )
                hours = np.concatenate([np.full(pad, hours[-1], dtype=np.int64), hours])
                weekdays = np.concatenate([np.full(pad, weekdays[-1], dtype=np.int64), weekdays])
                is_wknd = np.concatenate([np.full(pad, is_wknd[-1], dtype=np.int64), is_wknd])
            n = len(boardings)
            n_features = 4 if cfg.use_calendar else 2
            for i in range(n - cfg.seq_len + 1):
                seq = np.zeros((cfg.seq_len, n_features), dtype=np.float32)
                seq[:, 0] = hours[i : i + cfg.seq_len]
                seq[:, 1] = np.log1p(boardings[i : i + cfg.seq_len])
                if cfg.use_calendar:
                    seq[:, 2] = weekdays[i : i + cfg.seq_len]
                    seq[:, 3] = is_wknd[i : i + cfg.seq_len]
                X_seqs.append(seq)
                target_idx = i + cfg.seq_len
                if target_idx >= original_len:
                    target_idx = original_len - 1
                y_targets.append(np.log1p(group["boardings"].iloc[target_idx]))
        X = torch.tensor(np.stack(X_seqs))
        y = torch.tensor(np.array(y_targets, dtype=np.float32))
        n_samples = len(X)
        print(
            f"RouteNeural[{cfg.kind}] train: {n_samples:,} seq x L={cfg.seq_len}, "
            f"routes={n_routes}, h={cfg.hidden}, l={cfg.layers}"
        )
        self.model_ = SequenceModel(
            kind=cfg.kind,
            input_dim=cfg.hidden,
            hidden=cfg.hidden,
            layers=cfg.layers,
            n_routes=n_routes,
            route_emb_dim=cfg.route_emb_dim,
            use_calendar=cfg.use_calendar,
        )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_.to(device)
        opt = torch.optim.AdamW(self.model_.parameters(), lr=cfg.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs)
        lossf = nn.MSELoss()
        for epoch in range(cfg.epochs):
            self.model_.train()
            perm = torch.randperm(n_samples)
            tot = 0.0
            for i in range(0, n_samples, cfg.batch_size):
                b = perm[i : i + cfg.batch_size]
                xb = X[b].to(device)
                yb = y[b].to(device)
                opt.zero_grad()
                loss = lossf(self.model_(xb), yb)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model_.parameters(), 1.0)
                opt.step()
                tot += loss.item() * len(b)
            scheduler.step()
            print(f"  epoch {epoch + 1}/{cfg.epochs}: train_mse={tot / n_samples:.4f}")
        self.fallback_lookup_ = (
            df.groupby(["route_id", "hour"])["boardings"].mean().to_dict()
        )
        self.fitted_ = True

    def predict_batch(
        self,
        future_grid: pd.DataFrame,
        history: pd.DataFrame | None = None,
    ) -> np.ndarray:
        """Predict для batch of (route, hour)."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted")
        if future_grid.empty:
            return np.array([], dtype=np.float64)
        torch = _get_torch()["torch"]
        cfg = self.config
        if history is None or self.model_ is None:
            return self._fallback_predict(future_grid)
        df = future_grid.reset_index(drop=True)
        preds = np.zeros(len(df), dtype=np.float64)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        n_features = 4 if cfg.use_calendar else 2
        self.model_.eval()
        with torch.no_grad():
            for rid, group in history.groupby("route_id"):
                group = group.sort_values("timestamp").reset_index(drop=True)
                if len(group) < cfg.seq_len:
                    continue
                boardings = group["boardings"].values.astype(np.float32)
                hours = group["hour"].values.astype(np.int64)
                timestamps = pd.to_datetime(group["timestamp"].values)
                weekdays = np.array([ts.weekday() for ts in timestamps], dtype=np.int64)
                is_wknd = (weekdays >= 5).astype(np.int64)
                seq = np.zeros((1, cfg.seq_len, n_features), dtype=np.float32)
                seq[0, :, 0] = hours[-cfg.seq_len:]
                seq[0, :, 1] = np.log1p(boardings[-cfg.seq_len:])
                if cfg.use_calendar:
                    seq[0, :, 2] = weekdays[-cfg.seq_len:]
                    seq[0, :, 3] = is_wknd[-cfg.seq_len:]
                pred_log = self.model_(torch.tensor(seq).to(device)).cpu().numpy()[0]
                pred = float(np.expm1(pred_log))
                mask = df["route_id"].astype(int) == int(rid)
                preds[mask.values] = max(pred, 0.0)
        for i, row in df.reset_index(drop=True).iterrows():
            if preds[i] == 0.0:
                preds[i] = self.fallback_lookup_.get(
                    (int(row["route_id"]), int(row["hour"])), 0.0
                )
        return preds

    def _fallback_predict(self, future_grid: pd.DataFrame) -> np.ndarray:
        return np.array(
            [
                self.fallback_lookup_.get(
                    (int(row["route_id"]), int(row["hour"])), 0.0
                )
                for _, row in future_grid.iterrows()
            ]
        )

    def save(self, path: Path | str) -> None:
        """Save (state_dict + config + fallback)."""
        torch = _get_torch()["torch"]
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "model_state_dict": self.model_.state_dict() if self.model_ else None,
            "config": self.config,
            "route_ids": self.route_ids_,
            "fallback_lookup": self.fallback_lookup_,
            "model_id": self.model_id,
            "fitted_": self.fitted_,
        }
        with p.open("wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path | str) -> RouteNeuralPredictor:
        """Load from pickle."""
        torch = _get_torch()["torch"]
        with open(path, "rb") as f:
            state = pickle.load(f)
        instance = cls(
            config=state["config"],
            model_id=state.get("model_id", "rneural_v1"),
        )
        instance.route_ids_ = state["route_ids"]
        instance.fallback_lookup_ = state["fallback_lookup"]
        instance.fitted_ = state.get("fitted_", True)
        instance.model_ = None
        return instance
