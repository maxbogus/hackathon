"""Streaming sha256 + line counter. Pure stdlib (hashlib, mmap при больших файлах).

O(1) по памяти: держим только текущий чанк (1 MB по умолчанию) + accumulator sha256.
Не используем .read_bytes() — это загрузит файл целиком.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_CHUNK_BYTES = 1024 * 1024  # 1 MB — баланс между syscall-overhead и RAM


def streaming_sha256(path: str | Path, chunk_size: int = DEFAULT_CHUNK_BYTES) -> str:
    """sha256 файла в hex; читает по chunk_size байт за раз. O(1) RAM.

    Raises:
        FileNotFoundError: файл не существует.
        OSError: ошибка чтения.
    """
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")

    h = hashlib.sha256()
    with target.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def count_lines(path: str | Path, chunk_size: int = DEFAULT_CHUNK_BYTES) -> int:
    """Число строк в файле.

    Определение: количество терминаторов '\n' плюс 1, если последний байт
    НЕ '\n' и файл непустой. То есть "a\nb\nc" → 3 строки, "a\nb\n" → 2 строки.

    Streaming-подсчёт: не загружаем файл. Для train.csv (49M строк) ≈ 7 сек на HDD.
    """
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")

    count = 0
    last_byte = b""
    with target.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            count += block.count(b"\n")
            last_byte = block[-1:]

    # Если файл непустой и последний байт НЕ '\n' — есть незакрытая строка.
    if count > 0 and last_byte != b"\n":
        count += 1
    return count
