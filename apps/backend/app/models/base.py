"""Base для всех ORM моделей (re-export).

См. app.models.Base в app/models/__init__.py.
Этот файл оставлен для обратной совместимости с кодом, который может
импортировать `from app.models.base import Base`.
"""

from app.models import Base

__all__ = ["Base"]
