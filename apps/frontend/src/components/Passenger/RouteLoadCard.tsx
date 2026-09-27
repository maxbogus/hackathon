/**
 * T-218: карточка маршрута для пассажирского экрана.
 *
 * Variant 'actual' → блок факта (actuals).
 * Variant 'prediction' → блок прогноза (predictions).
 *
 * T-218+ (отзыв пользователя, см. clinerule 31):
 *   Показываем абсолютное число пассажиров + отклонение actual vs prediction.
 *   НЕ показываем «% перегруза» (boardings / TRAM_CAPACITY) — для маршрута с
 *   12 вагонами это давало 655% и «перегруз» на пустом маршруте в 5 утра.
 *
 * Шкала (асимметричная):
 *   actual > prediction:
 *     +15..+30% → yellow · +30..+60% → red · +60%+ → darkred
 *   actual < prediction (|dev| ≥ 15%):
 *     → lightblue (info, не warning)
 *   |dev| < 15%:
 *     → green (норма)
 *   нет данных:
 *     → gray
 *
 * Цвета берутся из loadTier.COLORS (single source of truth).
 */

import type { TKey } from '@/lib/i18n/keys';
import { t, tf } from '@/lib/i18n/t';

import {
  computeDeviation,
  deviationInfo,
  loadTier,
  visualFor,
  type LoadTier,
} from '@/lib/loadTier';
import type { RouteLoadVariant } from '@/lib/routeLoad';

export interface RouteLoadCardProps {
  readonly routeId: number;
  /** Текущее значение (actual или prediction). null = нет данных. */
  readonly boardings: number | null;
  /** Прогноз на этот же слот — нужен для расчёта отклонения в actual-карточках. */
  readonly predictionBoardings?: number | null;
  /** Tier из backend (load_pct vs TRAM_CAPACITY). Используется для prediction-карточек. */
  readonly tier?: LoadTier | null;
  /** raw load_pct (для tier-цвета если tier не передан). */
  readonly loadPct?: number | null;
  readonly variant?: RouteLoadVariant;
  /** T-122: выбранный маршрут — подсвечен (синхронизация с картой). */
  readonly selected?: boolean;
  /** T-122: клик/Enter/Space по карточке → выбрать маршрут на карте. */
  readonly onSelect?: (routeId: number) => void;
}

/**
 * T-231: подписи отклонения берутся из реестра (полные существительные:
 * «Перегрузка»/«Недогрузка»), а не из хардкода «перегруз/недогруз».
 */
const SIDE_TEXT_KEYS: Readonly<Record<'over' | 'under' | 'normal' | 'unknown', TKey>> = {
  over: 'passenger.side.over',
  under: 'passenger.side.under',
  normal: 'passenger.side.normal',
  unknown: 'passenger.side.unknown',
};

/**
 * Палитра для prediction-карточки (variant='prediction').
 * Один уровень из 4 (green/yellow/red/darkred) + fallback gray.
 * Single source of truth для tier-цветов — loadTier.COLORS.
 */
const VISUALS_BY_TIER = {
  green: { bg: '#f1f8e9', border: '#2e7d32', label: '🟢' },
  yellow: { bg: '#fff8e1', border: '#f9a825', label: '🟡' },
  red: { bg: '#ffebee', border: '#c62828', label: '🟠' },
  darkred: { bg: '#ffcdd2', border: '#7f0000', label: '🔴' },
  gray: { bg: '#f5f5f5', border: '#9e9e9e', label: '⚪' },
} as const;

export function RouteLoadCard({
  routeId,
  boardings,
  predictionBoardings,
  tier: tierProp,
  loadPct,
  variant,
  selected = false,
  onSelect,
}: RouteLoadCardProps): JSX.Element {
  const cardStyle: React.CSSProperties = {
    borderRadius: 6,
    padding: '14px 10px',
    minWidth: 150,
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
  };

  const interaction = interactionProps(routeId, selected, onSelect);

  // Нет данных — серая карточка.
  if (boardings === null) {
    return (
      <article
        data-testid="route-load-card"
        data-side="unknown"
        data-route-id={routeId}
        data-variant={variant ?? 'prediction'}
        data-selected={selected ? 'true' : 'false'}
        style={{
          ...cardStyle,
          background: '#f5f5f5',
          borderTop: '4px solid #9e9e9e',
          cursor: onSelect ? 'pointer' : 'default',
          outline: selected ? '2px solid #1f2937' : 'none',
          outlineOffset: 1,
        }}
        {...interaction}
      >
        <div style={{ fontSize: 13, color: '#555' }}>{tf('map.routeLabel', routeId)}</div>
        <div style={{ fontSize: 22, color: '#9e9e9e' }}>—</div>
        <div style={{ fontSize: 11, color: '#888' }}>{t('passenger.routeNoData')}</div>
      </article>
    );
  }

  const roundedBoardings = Math.round(boardings);
  const isActual = variant === 'actual';

  // Tier + подпись:
  //   actual      → через deviation (asymmetric scale, clinerule 31)
  //   prediction  → через load_pct из backend (loadTier, классика)
  let sideAttr: 'over' | 'under' | 'normal' | 'unknown';
  let tierAttr: LoadTier | 'unknown';
  let bgColor: string;
  let borderColor: string;
  let iconLabel: string;
  let footerText: string;

  if (isActual) {
    const deviation = computeDeviation(boardings, predictionBoardings ?? null);
    const info = deviationInfo(deviation);
    const visual = visualFor(info);
    sideAttr = info.side;
    // data-side атрибут показывает LoadSide (over/under/normal/unknown),
    // data-tier — LoadTier (green/yellow/red/darkred/unknown). Разные типы.
    tierAttr = info.tier === 'unknown' ? 'unknown' : info.tier;
    bgColor = visual.bg;
    borderColor = visual.border;
    iconLabel = visual.label;
    if (deviation === null) {
      footerText = t('passenger.routeNoPrediction');
    } else {
      const sign = deviation > 0 ? '+' : '';
      footerText = `${iconLabel} ${sign}${deviation.toFixed(1)}% · ${t(SIDE_TEXT_KEYS[info.side])}`;
    }
  } else {
    // prediction-карточка: число и есть прогноз, deviation не имеет смысла.
    const resolvedTier: LoadTier | null =
      tierProp ?? (loadPct !== null && loadPct !== undefined ? loadTier(loadPct) : null);
    const visual = resolvedTier ? VISUALS_BY_TIER[resolvedTier] : VISUALS_BY_TIER.gray;
    sideAttr = 'unknown';
    tierAttr = resolvedTier ?? 'unknown';
    bgColor = visual.bg;
    borderColor = visual.border;
    iconLabel = visual.label;
    footerText = iconLabel;
  }

  return (
    <article
      data-testid="route-load-card"
      data-side={sideAttr}
      data-tier={tierAttr}
      data-route-id={routeId}
      data-variant={variant ?? 'prediction'}
      data-selected={selected ? 'true' : 'false'}
      style={{
        ...cardStyle,
        background: bgColor,
        borderTop: `4px solid ${borderColor}`,
        cursor: onSelect ? 'pointer' : 'default',
        outline: selected ? '2px solid #1f2937' : 'none',
        outlineOffset: 1,
      }}
      {...interaction}
    >
      <div style={{ fontSize: 13, color: '#555' }}>{tf('map.routeLabel', routeId)}</div>
      <div
        style={{
          fontSize: 30,
          fontWeight: 700,
          lineHeight: 1,
          color: borderColor,
        }}
      >
        {roundedBoardings} {t('common.unitPeople')}
      </div>
      {isActual && (
        <div style={{ fontSize: 11, color: '#666' }}>
          {t('passenger.predictedShort')}:{' '}
          {predictionBoardings !== null && predictionBoardings !== undefined
            ? `${Math.round(predictionBoardings)} ${t('common.unitPeople')}`
            : '—'}
        </div>
      )}
      <div style={{ fontSize: 12, color: '#555' }}>{footerText}</div>
    </article>
  );
}

/**
 * T-122: интерактивность карточки (выбор маршрута для карты).
 *
 * Разметка без `<button>`: карточка — `article` с фиксированным testid и
 * data-атрибутами, которые читают существующие тесты. Если `onSelect` не
 * передан — никаких role/tabIndex (карточка не становится «кнопкой» молча).
 */
function interactionProps(
  routeId: number,
  selected: boolean,
  onSelect?: (routeId: number) => void,
): React.HTMLAttributes<HTMLElement> {
  if (!onSelect) return {};

  return {
    role: 'button',
    tabIndex: 0,
    'aria-pressed': selected,
    onClick: () => onSelect(routeId),
    onKeyDown: (event: React.KeyboardEvent<HTMLElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onSelect(routeId);
      }
    },
  };
}
