/**
 * HistoricalChart — line chart для historical boardings.
 *
 * T-196: использует GET /api/v1/historical/{route_id}.
 * Заменяет placeholder в /analyst.
 */

import { useQuery } from '@tanstack/react-query';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { t } from '@/lib/i18n/t';

import { customInstance } from '@/api/customInstance';

interface HistoricalPoint {
  period_start: string;
  period_end: string;
  value: number;
}

interface HistoricalResponse {
  route_id: number;
  from_date: string;
  to_date: string;
  granularity: string;
  points: HistoricalPoint[];
}

interface HistoricalChartProps {
  routeId: number;
  fromDate: string;
  toDate: string;
}

export function HistoricalChart({ routeId, fromDate, toDate }: HistoricalChartProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['historical', routeId, fromDate, toDate],
    queryFn: async () => {
      // F-097: customInstance теперь возвращает развёрнутый T, а не {data, headers, status}.
      const data = await customInstance<HistoricalResponse>({
        url: `/api/v1/historical/${routeId}?from=${fromDate}&to=${toDate}&granularity=day`,
        method: 'GET',
      });
      return data;
    },
    refetchInterval: 5 * 60_000, // 5 min
  });

  if (isLoading) return <p>{t('common.loading')}</p>;
  if (isError)
    return (
      <p role="alert">
        {t('common.errorPrefix')} {String(error)}
      </p>
    );

  const points = data?.points ?? [];
  if (points.length === 0) return <p data-testid="historical-empty">{t('analyst.noData')}</p>;

  const chartData = points.map((p) => ({
    date: p.period_start.slice(0, 10),
    value: p.value,
  }));

  return (
    <div data-testid="historical-chart">
      <h3>{t('analyst.historicalChartTitle')}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#8884d8" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
