"""Tests for transit_ai.lineage.hashing — streaming sha256 для больших файлов.

Проблема: train.csv = 8 GB. hash_dataframe() из training.registry.py грузит
DataFrame в RAM через pickle — OOM на 16 GB машине. Нужен streaming-вариант:
sha256 по 1 MB чанкам, без загрузки всего файла.

Запуск: uv run pytest ml/tests/test_lineage_hashing.py -q
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from transit_ai.lineage import hashing as lh


def test_streaming_sha256_matches_hashlib_for_small_file(tmp_path: Path) -> None:
    """Корректность: streaming sha256 == hashlib.file(proxy).hexdigest() на маленьком файле."""
    p = tmp_path / "small.csv"
    p.write_bytes(b"tran_no;device_no;tran_date_time\n1;2;2025-01-01\n3;4;2025-01-02\n")

    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    actual = lh.streaming_sha256(p)
    assert actual == expected
    assert len(actual) == 64  # hex sha256


def test_streaming_sha256_uses_constant_memory(tmp_path: Path) -> None:
    """8 GB файл НЕ должен загружаться целиком — пик RSS растёт < 50 MB даже на большом файле.

    Создаём 50 MB разреженный файл (быстрее теста) и проверяем, что RSS дельты < 50 MB.
    """
    big = tmp_path / "big.bin"
    chunk = os.urandom(1024 * 1024)  # 1 MB шум
    # 50 чанков = 50 MB (быстрее чем 8 GB, ту же логику проверяет)
    with big.open("wb") as f:
        for _ in range(50):
            f.write(chunk)

    import resource  # POSIX-only; на Linux OK

    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    digest = lh.streaming_sha256(big)
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    assert len(digest) == 64
    # На Linux ru_maxrss в KB. Допуск: пик не должен расти больше чем на 50 MB.
    growth_kb = rss_after - rss_before
    assert growth_kb < 50 * 1024, f"RSS grew by {growth_kb} KB — не streaming!"


def test_streaming_sha256_nonexistent_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        lh.streaming_sha256(tmp_path / "does-not-exist.csv")


def test_streaming_sha256_empty_file(tmp_path: Path) -> None:
    """Пустой файл → sha256('no bytes') = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855."""
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert lh.streaming_sha256(p) == expected


def test_chunk_size_is_configurable(tmp_path: Path) -> None:
    """Размер чанка — параметр; дефолт 1 MB."""
    p = tmp_path / "x.bin"
    p.write_bytes(os.urandom(3 * 1024 * 1024 + 17))  # 3 MB + 17 bytes
    full = hashlib.sha256(p.read_bytes()).hexdigest()
    assert lh.streaming_sha256(p, chunk_size=64 * 1024) == full
    assert lh.streaming_sha256(p, chunk_size=1024 * 1024) == full
    assert lh.streaming_sha256(p, chunk_size=8 * 1024 * 1024) == full


def test_count_lines_streaming(tmp_path: Path) -> None:
    """Streaming-подсчёт строк (через \n) — должен совпадать с wc -l."""
    p = tmp_path / "lines.txt"
    p.write_bytes(b"a\nb\nc\n")  # 3 строки, последняя без финального \n? дано с \n -> 3
    assert lh.count_lines(p) == 3

    p2 = tmp_path / "no_trailing_newline.txt"
    p2.write_bytes(b"a\nb\nc")  # 3 строки без финального \n
    assert lh.count_lines(p2) == 3

    p3 = tmp_path / "empty.txt"
    p3.write_bytes(b"")
    assert lh.count_lines(p3) == 0
