---
id: T-223
phase: 4
title: Frontend PassengerMode.tsx — 3 секции (факт / прогноз / таблица)
priority: P0
effort: 1
unit: hours
rice:
  R: 3
  I: 3
  C: 0.9
  score: 8.1
depends_on: [T-221, T-222]
blocks: [T-224]
tags: [frontend, passenger, ui, clinerule-31]
status: ready
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-220..T-222 подготовили:
- `/api/v1/historical/export.csv` (T-220)
- `routeCsv.ts` parser + fetch helpers (T-221)
- `PredictionsTable.tsx` (TanStack Table) + `LastDayCard.tsx` (T-222)

Переписываем `PassengerMode.tsx` — 3 секции:
1. «Фактическая нагрузка» — карточки `LastDayCard` per route за **последний день actuals**
2. «Прогнозируемая нагрузка» — карточки `LastDayCard` per route за **последний день predictions**
3. «Данные» — `<PredictionsTable rows={predictionRows} />`

Существующая логика с `/predictions/load` и `/historical/load` (T-218, AVG-агрегаты)
**уходит** — давала неверные числа (F-099: AVG за час ≠ SUM за день).

## Acceptance Criteria

- [ ] `apps/frontend/src/pages/PassengerMode.tsx` переписан (3 секции)
- [ ] Использует `fetchActualsCsv` + `fetchPredictionsCsv` из T-221
- [ ] Использует `LastDayCard` + `PredictionsTable` из T-222
- [ ] «Последний день actuals» = `MAX(period_start::date)` из actualRows
- [ ] «Последний день predictions» = `MAX(period_start::date)` из predictionRows
- [ ] Карточки показывают `SUM(value) GROUP BY route_id` для этого дня
- [ ] Секция «Фактическая нагрузка» НЕ рендерится если actualRows пусты
- [ ] Секция «Прогнозируемая нагрузка» НЕ рендерится если predictionRows пусты
- [ ] Loading state — `<p>{t('common.loading')}</p>` пока грузятся CSV
- [ ] Error state — `Alert` если fetch упал
- [ ] Footer с active model — как в T-218, но с человекочитаемым именем и «Точность (WAPE)» (T-231)
- [ ] vitest 6+ passed (`PassengerMode.test.tsx`)
- [ ] `yarn typecheck` 0 errors
- [ ] `yarn lint` без новых ошибок

## RED (apps/frontend/src/pages/PassengerMode.test.tsx — переписать)

```tsx
import { describe, expect, it, vi, afterEach, within } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PassengerMode } from './PassengerMode';

const ACTIVE_MODEL = {model_id: 'baseline_v1', metrics: {wape_score: 0.9272, rmsle: 0.23}};

afterEach(() => vi.restoreAllMocks());

function mockCsv(opts: {actuals?: string; predictions?: string; modelDown?: boolean} = {}): void {
  const actuals = opts.actuals ?? '';
  const predictions = opts.predictions ?? '';
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.includes('/historical/export.csv')) return new Response(actuals, {status: 200, headers: {'content-type': 'text/csv'}});
    if (url.includes('/predictions/export.csv')) return new Response(predictions, {status: 200, headers: {'content-type': 'text/csv'}});
    if (url.includes('/models/active')) {
      if (opts.modelDown) return new Response('boom', {status: 503});
      return new Response(JSON.stringify(ACTIVE_MODEL), {status: 200});
    }
    return new Response('not found', {status: 404});
  }) as typeof global.fetch;
}

describe('<PassengerMode> — 3 секции', () => {
  it('renders 3 sections: факт, прогноз, таблица', async () => {
    mockCsv({
      actuals: 'route;period_start;period_end;value\n1;2025-10-31T00:00:00Z;2025-10-31T01:00:00Z;5000\n',
      predictions: 'route;period_start;period_end;value\n1;2025-12-31T00:00:00Z;2026-01-01T00:00:00Z;7000\n',
    });
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText(/фактическая нагрузка/i)).toBeInTheDocument();
      expect(screen.getByText(/прогнозируемая нагрузка/i)).toBeInTheDocument();
      expect(screen.getByText(/данные/i)).toBeInTheDocument();
    });
  });

  it('карточка факта показывает SUM за последний день actuals', async () => {
    mockCsv({
      actuals: [
        'route;date;hour;value',
        '1;2025-10-31;0;1000',
        '1;2025-10-31;1;2000',
        '1;2025-10-31;2;3000',
        '7;2025-10-31;0;500',
      ].join('\n'),
    });
    render(<PassengerMode />);
    await waitFor(() => {
      const card1 = cardByTestId('fact-cards', 1);
      expect(card1?.textContent).toMatch(/6000 чел/);
      expect(card1?.textContent).toMatch(/2025-10-31/);
    });
  });

  it('карточка прогноза показывает SUM за последний день predictions', async () => {
    mockCsv({
      predictions: [
        'route;date;hour;value',
        '17;2025-12-31;0;10000',
        '17;2025-12-31;1;5000',
      ].join('\n'),
    });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByTestId('pred-cards', 17);
      expect(card?.textContent).toMatch(/15000 чел/);
      expect(card?.textContent).toMatch(/2025-12-31/);
    });
  });

  it('таблица рендерит все строки из predictionRows', async () => {
    const preds = [
      'route;date;hour;value',
      '1;a;b;100',
      '1;c;d;200',
      '1;e;f;300',
      '7;a;b;400',
      '7;c;d;500',
    ].join('\n');
    mockCsv({predictions: preds});
    render(<PassengerMode />);
    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      expect(rows.length).toBeGreaterThanOrEqual(6);
    });
  });

  it('не рендерит секцию «фактическая нагрузка» если actuals пусты', async () => {
    mockCsv({predictions: '1;a;b;100\n'});
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.queryByText(/фактическая нагрузка/i)).not.toBeInTheDocument();
    });
  });

  it('показывает loading во время fetch', () => {
    mockCsv();
    render(<PassengerMode />);
    expect(screen.getByText(/загрузка/i)).toBeInTheDocument();
  });
});

function cardByTestId(gridTestId: string, routeId: number): HTMLElement | undefined {
  const grid = screen.getByTestId(gridTestId);
  return within(grid).getByTestId('last-day-card-' + routeId, {exact: false});
}
```

## GREEN (apps/frontend/src/pages/PassengerMode.tsx — переписать)

```tsx
/**
 * T-223: PassengerMode = 3 секции (факт / прогноз / таблица) из CSV.
 * - «Фактическая нагрузка» — LastDayCard per route за MAX(actual.period_start) (T-231: copy)
 * - «Прогнозируемая нагрузка» — LastDayCard per route за MAX(prediction.period_start)
 * - «Данные» — TanStack Table со всеми строками
 */
import { useEffect, useMemo, useState } from 'react';
import { Alert } from '@/lib/Alert';
import { fetchActiveModel, formatWapeScore, type ActiveModelInfo } from '@/lib/activeModel';
import { fetchActualsCsv, fetchPredictionsCsv, type PredictionRow } from '@/lib/routeCsv';
import { LastDayCard } from '@/components/Passenger/LastDayCard';
import { PredictionsTable } from '@/components/Passenger/PredictionsTable';
import { t, tf } from '@/lib/i18n/t';

export function PassengerMode(): JSX.Element {
  const [actuals, setActuals] = useState<PredictionRow[]>([]);
  const [predictions, setPredictions] = useState<PredictionRow[]>([]);
  const [activeModel, setActiveModel] = useState<ActiveModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    (async () => {
      try {
        const [a, p] = await Promise.all([fetchActualsCsv(ctl.signal), fetchPredictionsCsv(ctl.signal)]);
        if (!ctl.signal.aborted) { setActuals(a); setPredictions(p); }
      } catch (e) {
        if (!ctl.signal.aborted) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!ctl.signal.aborted) setLoading(false);
      }
    })();
    fetchActiveModel(ctl.signal).then(m => { if (!ctl.signal.aborted) setActiveModel(m); }).catch(() => {});
    return () => ctl.abort();
  }, []);

  const factCards = useMemo(() => buildDayCards(actuals, 'actual'), [actuals]);
  const predCards = useMemo(() => buildDayCards(predictions, 'prediction'), [predictions]);

  const wapeLabel = formatWapeScore(activeModel?.wape_score ?? null);
  const modelId = activeModel?.model_id ?? '—';
  const footerText = wapeLabel !== null ? tf('passenger.activeModelFooter', modelId, wapeLabel) : tf('passenger.modelFooter', modelId);

  return (
    <section style={{padding: '16px 24px', fontFamily: 'system-ui, sans-serif'}}>
      <h2 style={{marginTop: 0}}>{t('passenger.modeTitle')}</h2>
      <p style={{color: '#666', marginTop: 4}}>{t('passenger.modeHint')}</p>
      {error && <Alert severity="warning" icon="⚠️">{tf('passenger.etaError', error)}</Alert>}
      {loading && <p style={{color: '#666'}}>{t('common.loading')}</p>}
      {!loading && factCards.length > 0 && (
        <>
          <h3 style={{marginTop: 16}}>{t('passenger.factHeader')}</h3>
          <p style={{color: '#888', fontSize: 12}}>{tf('passenger.factDateLabel', factCards[0].date)}</p>
          <div data-testid="fact-cards" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginTop: 8}}>
            {factCards.map(c => <LastDayCard key={c.routeId} {...c} />)}
          </div>
        </>
      )}
      {!loading && predCards.length > 0 && (
        <>
          <h3 style={{marginTop: 24}}>{t('passenger.predictionsDayHeader')}</h3>
          <p style={{color: '#888', fontSize: 12}}>{tf('passenger.predictionDateLabel', predCards[0].date)}</p>
          <div data-testid="pred-cards" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginTop: 8}}>
            {predCards.map(c => <LastDayCard key={c.routeId} {...c} />)}
          </div>
        </>
      )}
      {!loading && predictions.length > 0 && (
        <>
          <h3 style={{marginTop: 24}}>{tf('passenger.tableTitle', predictions.length)}</h3>
          <PredictionsTable rows={predictions} />
        </>
      )}
      <p style={{marginTop: 16, color: '#888', fontSize: 12}}>{footerText}</p>
    </section>
  );
}

function buildDayCards(rows: PredictionRow[], variant: 'actual' | 'prediction') {
  if (rows.length === 0) return [];
  const dates = rows.map(r => r.period_start.slice(0, 10));
  const maxDate = dates.reduce((a, b) => (a > b ? a : b));
  const lastDay = rows.filter(r => r.period_start.startsWith(maxDate));
  const byRoute = new Map<number, number>();
  for (const r of lastDay) byRoute.set(r.routeId, (byRoute.get(r.routeId) ?? 0) + r.value);
  return Array.from(byRoute.entries()).map(([routeId, boardings]) => ({routeId, date: maxDate, boardings, variant}));
}
```

## Verification

```bash
cd /home/maxbogus/Repositories/hackathon/apps/frontend && yarn test:run src/pages/PassengerMode.test.tsx
yarn typecheck
```
