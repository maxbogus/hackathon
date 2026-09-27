/**
 * T-222: <PredictionsTable> — таблица прогнозов на весь submission-период.
 *
 * Замечание про виртуализацию в jsdom:
 * - useVirtualizer измеряет scroll container через getBoundingClientRect —
 *   в jsdom это (0, 0). Без видимого scroll контейнера virtualizer
 *   рендерит 0 строк, поэтому проверки на видимый текст строк не работают.
 * - Тесты для virtual rows проверяют наличие scroll container'а и footer'а
 *   (которые рендерятся без зависимости от виртуализации), а не текст строк.
 */

import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { PredictionsTable } from './PredictionsTable';

const ROWS_ALL = [
  { routeId: 1, date: '2025-11-01', hour: 0, value: 100 },
  { routeId: 7, date: '2025-11-01', hour: 0, value: 200 },
  { routeId: 17, date: '2025-11-02', hour: 0, value: 300 },
  { routeId: 25, date: '2025-11-02', hour: 1, value: 400 },
  { routeId: 50, date: '2025-11-03', hour: 2, value: 500 },
];

describe('<PredictionsTable>', () => {
  it('рендерит 4 column headers с i18n', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    expect(screen.getByRole('columnheader', { name: /маршрут/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /дата/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /час/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /прогноз/i })).toBeInTheDocument();
  });

  it('multi-select чекбоксов рендерит чекбокс для каждого route_id', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    for (const rid of [1, 7, 17, 25, 50]) {
      const boxes = screen.getAllByRole('checkbox', { name: new RegExp(`Маршрут ${rid}$`) });
      expect(boxes.length).toBeGreaterThanOrEqual(1);
      expect(boxes[0]).toBeInTheDocument();
    }
  });

  it('default = 4 маршрута отмечены (1, 7, 17, 25), 50 — нет', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 1$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 7$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 17$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 25$/ })[0]).toBeChecked();
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ })[0]).not.toBeChecked();
  });

  it('кнопка "Показать все" переключает состояние', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    fireEvent.click(screen.getByTestId('predictions-table-show-all'));
    expect(screen.getByTestId('predictions-table-collapse')).toBeInTheDocument();
  });

  it('кнопка "Свернуть" возвращает к щадящему выбору', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    fireEvent.click(screen.getByTestId('predictions-table-show-all'));
    fireEvent.click(screen.getByTestId('predictions-table-collapse'));
    expect(screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ })[0]).not.toBeChecked();
    expect(screen.getByTestId('predictions-table-show-all')).toBeInTheDocument();
  });

  it('multi-select: клик чекбокса переключает selectedRoutes', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const all50 = screen.getAllByRole('checkbox', { name: /^Маршрут 50$/ });
    const route50 = all50.find((el) => el.tagName === 'INPUT');
    expect(route50).toBeDefined();
    expect(route50).not.toBeChecked();
    fireEvent.click(route50 as HTMLElement);
    expect(route50).toBeChecked();
  });

  it('globalFilter — input с правильным placeholder', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const search = screen.getByTestId('predictions-table-search');
    const placeholder = search.getAttribute('placeholder') ?? '';
    expect(placeholder).toMatch(/поиск/i);
  });

  it('globalFilter — изменение значения', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const search = screen.getByTestId('predictions-table-search') as HTMLInputElement;
    fireEvent.change(search, { target: { value: '2025-11-02' } });
    expect(search.value).toBe('2025-11-02');
  });

  it('сортировка по колонке route: клик переключает data-sort', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const routeHeader = screen.getByRole('columnheader', { name: /маршрут/i });
    expect(routeHeader).toHaveAttribute('data-sort', 'none');
    fireEvent.click(routeHeader);
    expect(routeHeader.getAttribute('data-sort')).toMatch(/^(asc|desc)$/);
  });

  it('footer показывает "строк: N · маршрутов: M"', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const footer = screen.getByTestId('predictions-table-footer');
    expect(footer.textContent).toMatch(/строк: 4/);
    expect(footer.textContent).toMatch(/маршрутов: 4/);
  });

  it('loading state', () => {
    render(<PredictionsTable rows={[]} isLoading />);
    expect(screen.getByText(/загрузка/i)).toBeInTheDocument();
  });

  it('error state', () => {
    render(<PredictionsTable rows={[]} error="boom" />);
    expect(screen.getByRole('status')).toHaveAttribute('data-severity', 'warning');
    expect(screen.getByText(/boom/i)).toBeInTheDocument();
  });

  it('empty state (rows=[] и не loading/error)', () => {
    render(<PredictionsTable rows={[]} />);
    expect(screen.getByText(/нет данных/i)).toBeInTheDocument();
  });

  it('scroll container (виртуализация) + footer на 1000 строк', () => {
    const big = Array.from({ length: 1000 }, (_, i) => ({
      routeId: 1,
      date: '2025-11-01',
      hour: i % 24,
      value: 100 + i,
    }));
    render(<PredictionsTable rows={big} />);
    expect(screen.getByTestId('predictions-table-scroll')).toBeInTheDocument();
    const footer = screen.getByTestId('predictions-table-footer');
    // 1 маршрут × 1000 строк, в default — маршрут 1 выбран.
    expect(footer.textContent).toMatch(/строк: 1000/);
  });

  // T-222 follow-up: после того как заменил <table> на CSS Grid <div role="table">,
  // header.row и data.row используют общий grid-template-columns → колонки выровнены.
  // Проверяем что header существует и подхватил GRID_TEMPLATE_COLUMNS через data-атрибут.
  // (В jsdom virtualizer не рендерит строки без scroll, поэтому проверяем только header —
  //  data row использует ту же константу по построению, см. virtualRowStyle().)
  it('header применяет GRID_TEMPLATE_COLUMNS через data-атрибут (общий шаблон с data rows)', () => {
    render(<PredictionsTable rows={ROWS_ALL} />);
    const header = screen.getByTestId('predictions-table-header');
    expect(header).toBeInTheDocument();
    // Конкретное значение, не just truthy — это контракт между header и data rows.
    expect(header.getAttribute('data-grid-template-columns')).toBe('70px 120px 60px 1fr');
  });
});
