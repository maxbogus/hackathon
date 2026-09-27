/**
 * T-226: <HistoricalTable> — таблица исторических данных (actuals) за весь период.
 *
 * Зеркало PredictionsTable.test.tsx, но:
 * - data-testid префикс historical-table-* (отличается от predictions-table-*)
 * - колонка "Факт" вместо "Прогноз"
 * - НЕТ тестов на globalFilter (поиск убран в F-101)
 *
 * Замечание про виртуализацию в jsdom (как в PredictionsTable.test.tsx):
 * - useVirtualizer измеряет scroll container через getBoundingClientRect —
 *   в jsdom это (0, 0). Без видимого scroll контейнера virtualizer
 *   рендерит 0 строк, поэтому проверки на видимый текст строк не работают.
 * - Тесты для virtual rows проверяют наличие scroll container'а и footer'а,
 *   а не текст строк.
 */

import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { HistoricalTable } from './HistoricalTable';

const ROWS_ALL = [
  { routeId: 1, date: '2025-10-31', hour: 0, value: 500 },
  { routeId: 7, date: '2025-10-31', hour: 0, value: 600 },
  { routeId: 17, date: '2025-10-30', hour: 0, value: 700 },
  { routeId: 25, date: '2025-10-30', hour: 1, value: 800 },
  { routeId: 50, date: '2025-10-29', hour: 2, value: 900 },
];

describe('<HistoricalTable>', () => {
  it('рендерит 4 column headers с i18n (Факт, не Прогноз)', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    expect(screen.getByRole('columnheader', { name: /маршрут/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /дата/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /час/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /факт/i })).toBeInTheDocument();
  });

  it('multi-select чекбоксов рендерит чекбокс для каждого route_id', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    for (const rid of [1, 7, 17, 25, 50]) {
      const boxes = screen.getAllByRole('checkbox', { name: new RegExp(`Маршрут ${rid}$`) });
      expect(boxes.length).toBeGreaterThanOrEqual(1);
      expect(boxes[0]).toBeInTheDocument();
    }
  });

  it('default = 4 маршрута отмечены (1, 7, 17, 25), 50 — нет', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 1$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 7$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 17$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 25$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ })[0]).not.toBeChecked();
  });

  it('кнопка "Показать все" переключает состояние', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    fireEvent.click(screen.getByTestId('historical-table-show-all'));
    expect(screen.getByTestId('historical-table-collapse')).toBeInTheDocument();
  });

  it('кнопка "Свернуть" возвращает к щадящему выбору', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    fireEvent.click(screen.getByTestId('historical-table-show-all'));
    fireEvent.click(screen.getByTestId('historical-table-collapse'));
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ })[0]).not.toBeChecked();
    expect(screen.getByTestId('historical-table-show-all')).toBeInTheDocument();
  });

  it('multi-select: клик чекбокса переключает selectedRoutes', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    const all50 = screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ });
    const route50 = all50.find((el) => el.tagName === 'INPUT');
    expect(route50).toBeDefined();
    expect(route50).not.toBeChecked();
    fireEvent.click(route50 as HTMLElement);
    expect(route50).toBeChecked();
  });

  it('НЕТ поля поиска (F-101: поиск убран из таблиц)', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    expect(screen.queryByTestId('historical-table-search')).toBeNull();
    // Также проверяем что нет search input по типу:
    expect(screen.queryByRole('searchbox')).toBeNull();
  });

  it('сортировка по колонке route: клик переключает data-sort', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    const routeHeader = screen.getByRole('columnheader', { name: /маршрут/i });
    expect(routeHeader).toHaveAttribute('data-sort', 'none');
    fireEvent.click(routeHeader);
    expect(routeHeader.getAttribute('data-sort')).toMatch(/^(asc|desc)$/);
  });

  it('footer показывает "строк: N · маршрутов: M"', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    const footer = screen.getByTestId('historical-table-footer');
    expect(footer.textContent).toMatch(/строк: 4/);
    expect(footer.textContent).toMatch(/маршрутов: 4/);
  });

  it('loading state', () => {
    render(<HistoricalTable rows={[]} isLoading />);
    expect(screen.getByText(/загрузка/i)).toBeInTheDocument();
  });

  it('error state', () => {
    render(<HistoricalTable rows={[]} error="boom" />);
    expect(screen.getByRole('status')).toHaveAttribute('data-severity', 'warning');
    expect(screen.getByText(/boom/i)).toBeInTheDocument();
  });

  it('empty state (rows=[] и не loading/error)', () => {
    render(<HistoricalTable rows={[]} />);
    // Empty text: "Нет исторических данных за выбранный период"
    expect(screen.getByTestId('historical-table-empty')).toHaveTextContent(/исторических данных/i);
  });

  it('scroll container (виртуализация) + footer на 1000 строк', () => {
    const big = Array.from({ length: 1000 }, (_, i) => ({
      routeId: 1,
      date: '2025-10-31',
      hour: i % 24,
      value: 100 + i,
    }));
    render(<HistoricalTable rows={big} />);
    expect(screen.getByTestId('historical-table-scroll')).toBeInTheDocument();
    const footer = screen.getByTestId('historical-table-footer');
    // 1 маршрут × 1000 строк, в default — маршрут 1 выбран.
    expect(footer.textContent).toMatch(/строк: 1000/);
  });

  it('header применяет GRID_TEMPLATE_COLUMNS через data-атрибут (общий шаблон с data rows)', () => {
    render(<HistoricalTable rows={ROWS_ALL} />);
    const header = screen.getByTestId('historical-table-header');
    expect(header).toBeInTheDocument();
    // Конкретное значение, не just truthy — это контракт между header и data rows.
    expect(header.getAttribute('data-grid-template-columns')).toBe('70px 120px 60px 1fr');
  });
});
