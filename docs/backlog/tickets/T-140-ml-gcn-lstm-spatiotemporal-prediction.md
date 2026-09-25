---
id: T-140
phase: 2
title: ml transit_ai models — GCN+LSTM для пространственно-временного прогноза (ТЗ §5 Этап 2)
priority: P2
effort: 8
unit: hours
rice:
  R: 4
  I: 2.0
  C: 0.6
  score: 0.6
depends_on: [T-029]
blocks: []
tags: [ml, neural, gcn, lstm, spatiotemporal, hackathon]
status: backlog
created: 2026-09-23
updated: 2026-09-25
assignee: ""
---

# T-140: GCN+LSTM — пространственно-временная модель прогноза пассажиропотока

## Context

ТЗ §5 Этап 2:
> «Реализация GCN + LSTM (пространственно-временная модель)
>  - Использовать PyTorch Geometric.
>  - Построить граф на основе топологии маршрутов и географической близости.
>  - Обучить модель, которая принимает на вход признаки всех остановок за последние L дней
>    и выдаёт прогноз на следующий день для каждой остановки.
>  - Сравнить с LSTM без графа.»

ТЗ §6.2 (граф остановок):
> «Создание графа остановок:
>  - Вершины – остановки.
>  - Рёбра – если остановки находятся на одном маршруте (вес = 1) или расстояние между ними
>    меньше 500 м (вес = 1 / расстояние).»

Текущее состояние:
- T-029 (GRU PyTorch) в tickets/, не начат.
- Нет тикета на GCN, нет кода.
- PyTorch Geometric указан в pyproject.toml для ML.

Этот тикет **может быть отложен**, если времени не хватит — но в бэклоге должен быть зафиксирован.

## Acceptance Criteria

- [ ] Модуль ml/transit_ai/models/gcn_lstm.py с классом GCNLSTMPredictor
- [ ] Архитектура:
  - GCN слой: torch_geometric.nn.GCNConv (2 слоя, hidden=64, dropout=0.2)
  - LSTM слой: 1 слой, hidden=128, window=L=14 дней
  - Выход: per-stop прогноз на следующий день
- [ ] Граф строится в ml/transit_ai/data/graph.py:
  - Узлы: остановки (id, lat, lon)
  - Рёбра тип 1: на одном маршруте, weight=1
  - Рёбра тип 2: расстояние < 500м, weight=1/distance
- [ ] DataLoader для последовательностей: скользящее окно L=14 дней × все остановки
- [ ] Сравнение с чистым LSTM (T-029) — таблица метрик RMSLE/MAE/MAPE
- [ ] Сохранение артефакта в ml/artifacts/gcn_lstm_v1/{meta.json, model.pt}
- [ ] Регистрация в model dispatcher
- [ ] Smoke test: make train-gcn-lstm на синтетике
- [ ] Benchmark: make benchmark-compare показывает gcn_lstm_v1
- [ ] Документация: ml/transit_ai/models/gcn_lstm.md
- [ ] Unit-тест: ml/tests/test_gcn_lstm.py (3+ кейса)

## Technical Notes

Архитектура (PyTorch Geometric):
```python
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv

class GCNLSTMPredictor(nn.Module):
    def __init__(self, n_stops, n_features, hidden=64, lstm_hidden=128, window=14):
        super().__init__()
        self.gcn1 = GCNConv(n_features, hidden)
        self.gcn2 = GCNConv(hidden, hidden)
        self.dropout = nn.Dropout(0.2)
        self.lstm = nn.LSTM(hidden, lstm_hidden, batch_first=True)
        self.fc = nn.Linear(lstm_hidden, 1)
        self.window = window

    def forward(self, x_seq, edge_index):
        """
        x_seq: (batch, window, n_stops, n_features)
        edge_index: (2, n_edges)
        returns: (batch, n_stops)
        """
        batch, window, n_stops, n_features = x_seq.shape
        gcn_outs = []
        for t in range(window):
            x_t = x_seq[:, t, :, :].reshape(-1, n_features)
            h = torch.relu(self.gcn1(x_t, edge_index))
            h = self.dropout(h)
            h = torch.relu(self.gcn2(h, edge_index))
            h = h.reshape(batch, n_stops, -1)
            gcn_outs.append(h)
        gcn_seq = torch.stack(gcn_outs, dim=1)
        gcn_seq = gcn_seq.permute(0, 2, 1, 3).reshape(batch * n_stops, window, -1)
        lstm_out, _ = self.lstm(gcn_seq)
        last = lstm_out[:, -1, :]
        out = self.fc(last).reshape(batch, n_stops)
        return out
```

Граф (для Москвы, ~800 остановок):
- ~3000 рёбер тип 1
- ~5000 рёбер тип 2
- Итого ~8000 рёбер

Обучение:
- Batch size: 32
- Optimizer: Adam, lr=5e-4
- Early stopping: patience=5
- Epochs: max 50
- Время: ~10-15 мин на RTX 5060

## Verification

```bash
# 1. Smoke train
make train-gcn-lstm

# 2. Type-check
cd ml && uv run mypy transit_ai/models/

# 3. Unit-тесты
cd ml && uv run pytest tests/test_gcn_lstm.py -v

# 4. Benchmark vs LSTM
make benchmark-all
make benchmark-compare | grep "gcn_lstm"

# 5. Live prediction
make up
curl "http://localhost:8000/api/v1/models/active"
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐)** — GCN = "spatial-aware ML" = инновация.
**Департамент (⭐⭐⭐⭐)** — модель учитывает соседние остановки.
**ML-сообщество (⭐⭐⭐)** — открытый код = воспроизводимость.

RICE: 0.6 — формально низкий (high effort, требует GPU, может не успеться).
Но обязательный пункт roadmap для жюри (ТЗ §5 явно требует GCN+LSTM).
