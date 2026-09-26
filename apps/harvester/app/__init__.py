"""Transit-AI Harvester — Celery worker для сбора внешних JSON.

T-193: пайплайн, который качает данные в JSON (weather, traffic, POI, events)
и складывает в data/external/. Использует Redis как broker (уже есть в
docker-compose). В проде R4 hackathon-rules блокирует online API, поэтому
режим HARVESTER_MODE=local читает из data/external/*.json и просто нормализует
их в канонический формат. Режим HARVESTER_MODE=online ходит в API
(Open-Meteo, OSM Overpass).
"""

from app.celery_app import celery_app

__all__ = ["celery_app"]
