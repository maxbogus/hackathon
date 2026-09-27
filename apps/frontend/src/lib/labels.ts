/**
 * T-231: backend-идентификаторы → человекочитаемые подписи.
 *
 * Зачем: до T-231 в интерфейс протекали внутренние имена (`use_lag`,
 * `zero_route_5`), имена наборов факторов (`with_all`) и идентификаторы
 * моделей (`baseline_v1`, `test_submission_baseline`). Для Департамента
 * транспорта это недопустимо — UI говорит на языке диспетчера.
 *
 * Правила (clinerule 20 / 32):
 *   - Русские тексты живут ТОЛЬКО в `lib/i18n/ru-RU.ts`. Этот модуль хранит
 *     лишь мэппинг `backend name → TKey` и generic-фолбэк для неизвестных
 *     идентификаторов.
 *   - Переводчик инжектится (`Translator`), поэтому модуль не импортирует
 *     `t` — это pure logic, тестируемая без реестра.
 *   - Неизвестные имена никогда не дают пустую строку: сначала описание из
 *     API, затем само имя (для `*_id` — generic де-снейкинг), чтобы деградация
 *     была видимой, а не тихой.
 *
 * Fallback-цепочка для тогглов/исключений:
 *   known map → `description` из API → raw `name`
 */

import type { TKey } from './i18n/keys';

/** Минимальный контракт переводчика — совпадает с `t()` из `lib/i18n/t`. */
export type Translator = (key: TKey) => string;

/** Русские подписи фич (`feature_toggles.name` из `/api/v1/features`). */
const FEATURE_LABEL_KEYS: Readonly<Record<string, TKey>> = {
  use_poi: 'analyst.featureLabels.usePoi',
  use_traffic: 'analyst.featureLabels.useTraffic',
  use_weather: 'analyst.featureLabels.useWeather',
  use_events: 'analyst.featureLabels.useEvents',
  use_seasonal: 'analyst.featureLabels.useSeasonal',
  use_lag: 'analyst.featureLabels.useLag',
};

/** Русские пояснения фич. */
const FEATURE_HINT_KEYS: Readonly<Record<string, TKey>> = {
  use_poi: 'analyst.featureHints.usePoi',
  use_traffic: 'analyst.featureHints.useTraffic',
  use_weather: 'analyst.featureHints.useWeather',
  use_events: 'analyst.featureHints.useEvents',
  use_seasonal: 'analyst.featureHints.useSeasonal',
  use_lag: 'analyst.featureHints.useLag',
};

/** Русские подписи исключений (`zero_overrides.name`). */
const ZERO_LABEL_KEYS: Readonly<Record<string, TKey>> = {
  zero_route_5: 'analyst.zeroLabels.zeroRoute5',
  zero_night_pred_cap: 'analyst.zeroLabels.zeroNightPredCap',
  zero_weekend: 'analyst.zeroLabels.zeroWeekend',
  zero_holidays: 'analyst.zeroLabels.zeroHolidays',
};

/** Русские пояснения исключений. */
const ZERO_HINT_KEYS: Readonly<Record<string, TKey>> = {
  zero_route_5: 'analyst.zeroHints.zeroRoute5',
  zero_night_pred_cap: 'analyst.zeroHints.zeroNightPredCap',
  zero_weekend: 'analyst.zeroHints.zeroWeekend',
  zero_holidays: 'analyst.zeroHints.zeroHolidays',
};

/** Человекочитаемые имена моделей (`model_id` из ML-артефактов). */
const MODEL_LABEL_KEYS: Readonly<Record<string, TKey>> = {
  baseline_v1: 'analyst.modelLabels.baselineV1',
  test_submission_baseline: 'analyst.modelLabels.testSubmissionBaseline',
  route_baseline_v1: 'analyst.modelLabels.routeBaselineV1',
  xgboost_v8_poi: 'analyst.modelLabels.xgboostV8Poi',
};

/** Человекочитаемые имена наборов факторов (`feature_set`). */
const FEATURE_SET_LABEL_KEYS: Readonly<Record<string, TKey>> = {
  with_all: 'analyst.featureSets.withAll',
  with_poi: 'analyst.featureSets.withPoi',
  baseline: 'analyst.featureSets.baseline',
};

/**
 * Аббревиатуры, которые нельзя «приводить к предложению» (`gru` → `Gru`).
 * Также используются как маркер: аббревиатура в конце идентификатора
 * заворачивается в скобки (`xgboost_v8_poi` → «XGBoost v8 (POI)»).
 */
const ACRONYMS: Readonly<Record<string, string>> = {
  xgboost: 'XGBoost',
  catboost: 'CatBoost',
  lightgbm: 'LightGBM',
  gru: 'GRU',
  lstm: 'LSTM',
  nn: 'NN',
  poi: 'POI',
  mc: 'MC',
  api: 'API',
  csv: 'CSV',
  xlsx: 'XLSX',
  ui: 'UI',
  llm: 'LLM',
  sql: 'SQL',
  wape: 'WAPE',
  mape: 'MAPE',
};

function humanizeToken(token: string, isFirst: boolean): string {
  const lower = token.toLowerCase();
  const acronym = ACRONYMS[lower];
  if (acronym !== undefined) return acronym;
  // Версии и числа не капитализируем: v11, v8, 55.
  if (/^v\d/.test(lower) || /^\d/.test(lower)) return lower;
  return isFirst ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
}

/**
 * Generic де-снейкинг идентификатора для неизвестных значений:
 *   route_baseline_v1     → «Route baseline v1»
 *   xgboost_v8_poi        → «XGBoost v8 (POI)»
 *   with_events_only      → «With events only»
 *
 * Пустая строка / строка из одних разделителей → `''`, чтобы вызывающий код
 * мог нарисовать «—».
 */
export function humanizeIdentifier(raw: string): string {
  const tokens = raw
    .trim()
    .split(/[_\-\s]+/)
    .filter((token) => token.length > 0);
  const last = tokens.at(-1);
  if (last === undefined) return '';

  const head = tokens.slice(0, -1).map((token, index) => humanizeToken(token, index === 0));
  const trailingAcronym = ACRONYMS[last.toLowerCase()];
  const tail =
    tokens.length > 1 && trailingAcronym !== undefined
      ? `(${trailingAcronym})`
      : humanizeToken(last, tokens.length === 1);
  return [...head, tail].join(' ');
}

/**
 * Подпись тоггла: известное имя → реестр, иначе описание из API, иначе raw name.
 * Описание из API — английское, но это лучше, чем протекающий `use_foo`.
 */
export function featureName(
  name: string,
  description: string | null | undefined,
  translate: Translator,
): string {
  const key = FEATURE_LABEL_KEYS[name];
  if (key !== undefined) return translate(key);
  return nonEmpty(description) ?? name;
}

/**
 * Пояснение тоггла под подписью. Для неизвестных имён — пустая строка:
 * подпись уже показывает описание из API, дублировать его не нужно.
 */
export function featureHint(name: string, translate: Translator): string {
  const key = FEATURE_HINT_KEYS[name];
  return key !== undefined ? translate(key) : '';
}

/** Подпись исключения (zero override). */
export function zeroName(
  name: string,
  description: string | null | undefined,
  translate: Translator,
): string {
  const key = ZERO_LABEL_KEYS[name];
  if (key !== undefined) return translate(key);
  return nonEmpty(description) ?? name;
}

/** Пояснение исключения (zero override). */
export function zeroHint(name: string, translate: Translator): string {
  const key = ZERO_HINT_KEYS[name];
  return key !== undefined ? translate(key) : '';
}

/**
 * Имя модели для UI: известные id → реестр, остальные → де-снейкинг.
 * Raw `model_id` вызывающий код показывает в `title=` (трассируемость).
 */
export function modelName(modelId: string | null | undefined, translate: Translator): string {
  const raw = nonEmpty(modelId);
  if (raw === null) return '';
  const key = MODEL_LABEL_KEYS[raw];
  return key !== undefined ? translate(key) : humanizeIdentifier(raw);
}

/**
 * Имя набора факторов: `with_all` → «Все факторы».
 * `null` / пустая строка → `''` (вызывающий рисует «—»).
 */
export function featureSetName(
  featureSet: string | null | undefined,
  translate: Translator,
): string {
  const raw = nonEmpty(featureSet);
  if (raw === null) return '';
  const key = FEATURE_SET_LABEL_KEYS[raw];
  return key !== undefined ? translate(key) : humanizeIdentifier(raw);
}

/**
 * Состояние исключений (zero overrides) для панели активного прогноза.
 * `null` / `undefined` → `''` (бэкенд не сообщил состояние).
 */
export function zerosStateText(applied: boolean | null | undefined, translate: Translator): string {
  if (applied === null || applied === undefined) return '';
  return applied ? translate('analyst.zerosOn') : translate('analyst.zerosOff');
}

/** `null` для пустой/пробельной строки — иначе исходное значение. */
function nonEmpty(value: string | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}
