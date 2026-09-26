"""Tests for sweep_gru.py (T-177-GRU-SWEEP, по шаблону contest sweep_neural.py).

Контракт:
- GRID содержит (kind, hidden, layers, lr, seq_len, epochs)
- load_done() читает CSV и возвращает set of (kind, hidden, layers, lr, seq_len)
- append_row() пишет одну строку в CSV с header
- Файл interrupt-safe: можно прервать и продолжить (resume)
"""

from __future__ import annotations

from pathlib import Path


def test_sweep_gru_grid_has_required_columns(tmp_path: Path) -> None:
    """GRID элементы имеют правильную структуру (kind, hidden, layers, lr, seq_len, epochs)."""
    from scripts.sweep_gru import GRID

    assert len(GRID) >= 5, f"GRID должен иметь ≥5 configs, имеет {len(GRID)}"
    for cfg in GRID:
        assert len(cfg) == 6, f"GRID row должен иметь 6 полей: {cfg}"
        kind, hidden, layers, lr, seq_len, epochs = cfg
        assert kind == "gru"
        assert hidden in (64, 96, 128, 192, 256)
        assert layers in (1, 2, 3)
        assert 1e-4 <= lr <= 1e-3
        assert seq_len in (168, 336, 504, 720)
        assert 5 <= epochs <= 30


def test_sweep_gru_append_row_creates_csv(tmp_path: Path) -> None:
    """append_row добавляет строку в существующий CSV."""
    from scripts.sweep_gru import _append_row

    csv_path = tmp_path / "test_sweep.csv"
    # Создаём файл с header сначала (как делает main())
    csv_path.write_text(
        "kind,hidden,layers,lr,seq_len,epochs,wape_score,best_epoch,date,saved\n"
    )
    _append_row(csv_path, "gru,128,2,0.0003,336,20,0.1234,18,2026-09-26,1")
    content = csv_path.read_text()
    assert "kind,hidden,layers,lr,seq_len,epochs,wape_score" in content
    assert "gru,128,2,0.0003,336,20,0.1234" in content


def test_sweep_gru_load_done_skips_done(tmp_path: Path) -> None:
    """load_done правильно читает выполненные configs и пропускает их."""
    from scripts.sweep_gru import _append_row, load_done

    csv_path = tmp_path / "done.csv"
    _append_row(csv_path, "header")
    _append_row(csv_path, "gru,128,2,0.0003,336,20,0.5,18,2026-09-26,1")
    _append_row(csv_path, "gru,64,1,0.0003,168,15,0.4,12,2026-09-26,0")

    done = load_done(csv_path)
    assert ("gru", 128, 2, 0.0003, 336) in done
    assert ("gru", 64, 1, 0.0003, 168) in done
    assert ("gru", 256, 2, 0.0003, 336) not in done


def test_sweep_gru_load_done_handles_empty(tmp_path: Path) -> None:
    """load_done на несуществующем файле возвращает пустой set."""
    from scripts.sweep_gru import load_done

    csv_path = tmp_path / "nonexistent.csv"
    done = load_done(csv_path)
    assert done == set()


def test_sweep_gru_load_done_skips_failed(tmp_path: Path) -> None:
    """FAIL/Timeout строки не считаются done (можно перезапустить)."""
    from scripts.sweep_gru import _append_row, load_done

    csv_path = tmp_path / "mixed.csv"
    _append_row(csv_path, "header")
    _append_row(csv_path, "gru,128,2,0.0003,336,20,FAIL,0,2026-09-26,0")
    _append_row(csv_path, "gru,64,1,0.0003,168,15,TIMEOUT,0,2026-09-26,0")

    done = load_done(csv_path)
    assert len(done) == 0, f"FAIL/TIMEOUT не должны быть в done, got {done}"
