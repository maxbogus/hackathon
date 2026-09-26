"""Tests for sweep_neural.py (T-177-NEURAL-CONFIG)."""

from __future__ import annotations

from pathlib import Path


def test_sweep_neural_grid_has_gru_lstm_mamba(tmp_path: Path) -> None:
    """GRID содержит все 3 kinds (gru, lstm, mamba)."""
    from scripts.sweep_neural import GRID

    kinds = {c[0] for c in GRID}
    assert "gru" in kinds
    assert "lstm" in kinds
    assert "mamba" in kinds


def test_sweep_neural_grid_has_required_columns(tmp_path: Path) -> None:
    """GRID элементы имеют правильную структуру."""
    from scripts.sweep_neural import GRID

    for cfg in GRID:
        assert len(cfg) == 6
        kind, hidden, layers, lr, seq_len, epochs = cfg
        assert kind in ("gru", "lstm", "mamba")
        assert isinstance(hidden, int) and hidden > 0
        assert isinstance(layers, int) and layers >= 1
        assert isinstance(seq_len, int) and seq_len > 0
        assert 1e-4 <= lr <= 1e-3
        assert 5 <= epochs <= 30


def test_sweep_neural_load_done_skips_failures(tmp_path: Path) -> None:
    """load_done skip FAIL/TIMEOUT."""
    from scripts.sweep_neural import _append_row, load_done

    csv_path = tmp_path / "test.csv"
    _append_row(csv_path, "kind,hidden,layers,lr,seq_len,epochs,wape_score,best_epoch,date,saved")
    _append_row(csv_path, "gru,64,1,0.0003,168,15,0.5,15,2026-09-26,1")
    _append_row(csv_path, "mamba,32,1,0.0003,48,10,FAIL,0,2026-09-26,0")

    done = load_done(csv_path)
    assert ("gru", 64, 1, 0.0003, 168) in done
    assert ("mamba", 32, 1, 0.0003, 48) not in done
