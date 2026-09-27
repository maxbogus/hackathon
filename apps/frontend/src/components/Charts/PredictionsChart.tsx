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
import { featureSetName, zerosStateText } from '@/lib/labels';

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

/**
 * buildPredictionsUrl — URL для /predictions/db/{route_id} (T-230).
 *
 * preferActive=true → backend берёт параметры активного набора (фолбэк,
 * когда по текущим коэффициентам прогноз не сгенерирован).
 */
function buildPredictionsUrl(props: PredictionsChartProps, preferActive: boolean): string {
  const base =
    `/api/v1/predictions/db/${props.routeId}?from=${props.fromDate}&to=${props.toDate}` +
    `&horizon=${props.horizon}&granularity=${props.granularity}`;
  return preferActive
    ? `${base}&prefer_active=true`
    : `${base}&coef_weather=${props.coefWeather}` +
        `&coef_event=${props.coefEvent}&coef_season=${props.coefSeason}`;
}

export function PredictionsChart(props: PredictionsChartProps): JSX.Element {
  const { routeId, fromDate, toDate, horizon, granularity } = props;
  const { coefWeather, coefEvent, coefSeason } = props;

  const slidersQuery = useQuery({
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
    queryFn: () =>
      customInstance<PredictionsResponse>({
        url: buildPredictionsUrl(props, false),
        method: 'GET',
      }),
    refetchInterval: 5 * 60_000,
  });

  const slidersEmpty = (slidersQuery.data?.points.length ?? 0) === 0;

  // T-230 (вариант 3): фолбэк на активный набор + жёлтая подпись.
  const activeQuery = useQuery({
    queryKey: ['predictions-db-active', routeId, fromDate, toDate, horizon, granularity],
    queryFn: () =>
      customInstance<PredictionsResponse>({
        url: buildPredictionsUrl(props, true),
        method: 'GET',
      }),
    enabled: slidersEmpty,
    refetchInterval: 5 * 60_000,
  });

  if (slidersQuery.isLoading) return <p>{t('common.loading')}</p>;
  if (slidersQuery.isError)
    return (
      <p role="alert">
        {t('common.errorPrefix')} {String(slidersQuery.error)}
      </p>
    );

  const usingFallback = slidersEmpty && (activeQuery.data?.points.length ?? 0) > 0;
  const data = usingFallback ? activeQuery.data : slidersQuery.data;
  const points = data?.points ?? [];
  if (points.length === 0) return <p data-testid="predictions-empty">{t('analyst.noData')}</p>;

  const chartData = points.map((p) => ({
    datetime: p.period_start.slice(0, 13), // YYYY-MM-DDTHH
    value: p.value,
  }));

  // T-231: в заголовке графика — не `(with_all) · zeros=ON`, а человекочитаемо.
  const featureSetLabel = featureSetName(data?.feature_set, t);
  const zerosLabel = zerosStateText(data?.zeros_applied, t);

  return (
    <div data-testid="predictions-chart">
      <h3>
        {t('analyst.predictionsChartTitle')}
        {featureSetLabel ? ` · ${featureSetLabel}` : ''}
        {zerosLabel ? ` · ${zerosLabel}` : ''}
      </h3>
      {usingFallback && (
        <p
          data-testid="predictions-fallback-note"
          style={{ fontSize: 13, color: '#92400e', margin: '4px 0' }}
        >
          {t('analyst.chartFallbackNote')}
        </p>
      )}
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
