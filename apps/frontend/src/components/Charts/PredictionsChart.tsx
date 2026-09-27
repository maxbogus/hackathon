/**
 * PredictionsChart — line chart для прогнозов из БД.
 *
 * T-196: использует GET /api/v1/predictions/db/{route_id}.
 * С feature_set/zeros_applied фильтрами (default = best F-083).
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

interface PredictionPoint {
  period_start: string;
  value: number;
  feature_set: string;
  zeros_applied: boolean;
}

interface PredictionsResponse {
  route_id: number;
  from_date: string;
  to_date: string;
  feature_set: string | null;
  zeros_applied: boolean | null;
  points: PredictionPoint[];
}

interface PredictionsChartProps {
  routeId: number;
  fromDate: string;
  toDate: string;
  horizon: 'day' | 'month' | 'year';
  granularity: 'hour' | 'day' | 'month';
  coefWeather: number;
  coefEvent: number;
  coefSeason: number;
}

export function PredictionsChart({
  routeId,
  fromDate,
  toDate,
  horizon,
  granularity,
  coefWeather,
  coefEvent,
  coefSeason,
}: PredictionsChartProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: [
      'predictions-db',
      routeId,
      fromDate,
      toDate,
      horizon,
      granularity,
      coefWeather,
      coefEvent,
      coefSeason,
    ],
    queryFn: async () => {
      const data = await customInstance<PredictionsResponse>({
        url:
          `/api/v1/predictions/db/${routeId}?from=${fromDate}&to=${toDate}` +
          `&horizon=${horizon}&granularity=${granularity}` +
          `&coef_weather=${coefWeather}&coef_event=${coefEvent}&coef_season=${coefSeason}`,
        method: 'GET',
      });
      return data;
    },
    refetchInterval: 5 * 60_000,
  });

  if (isLoading) return <p>{t('common.loading')}</p>;
  if (isError)
    return (
      <p role="alert">
        {t('common.errorPrefix')} {String(error)}
      </p>
    );

  const points = data?.points ?? [];
  if (points.length === 0) return <p data-testid="predictions-empty">{t('analyst.noData')}</p>;

  const chartData = points.map((p) => ({
    datetime: p.period_start.slice(0, 13), // YYYY-MM-DDTHH
    value: p.value,
  }));

  return (
    <div data-testid="predictions-chart">
      <h3>
        {t('analyst.predictionsChartTitle')}
        {data?.feature_set ? ` (${data.feature_set})` : ''}
        {data?.zeros_applied ? ' · zeros=ON' : ''}
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="datetime" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#82ca9d" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
