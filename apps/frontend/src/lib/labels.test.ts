/**
 * T-231: <lib/labels.ts> — мэппинг backend-идентификаторов в человекочитаемые
 * подписи (department-grade UI copy).
 *
 * Что проверяем:
 *   1. Известные имена тогглов/исключений резолвятся в русские подписи из
 *      реестра (clinerule 20) — в UI не протекает `use_lag` / `zero_route_5`.
 *   2. Неизвестные имена не ломают UI: fallback на описание из API, затем на
 *      исходное имя (никогда не пустая строка).
 *   3. `model_id` / `feature_set` показываются человеку (`baseline_v1` →
 *      «Базовая v1»), неизвестные — через generic де-снейкинг
 *      (`xgboost_v11_base_only` → «XGBoost v11 base only»).
 *
 * `labels.ts` — pure logic: translator инжектится, модуль не импортирует `t`
 * (clinerule 20: `lib/*.ts` не содержит UI-строк). Поэтому часть тестов
 * инжектит identity-переводчик (проверяем КЛЮЧИ), часть — реальный `t`
 * (проверяем итоговый русский текст).
 */

import { describe, expect, it } from 'vitest';

import {
  featureHint,
  featureName,
  featureSetName,
  humanizeIdentifier,
  modelName,
  zerosStateText,
  zeroHint,
  zeroName,
} from './labels';
import { t } from './i18n/t';
import type { TKey } from './i18n/keys';

/** Identity-переводчик: возвращает сам ключ — так виден резолв. */
const asKey = (key: TKey): string => key;

describe('humanizeIdentifier', () => {
  it('переводит snake_case в читаемую фразу', () => {
    expect(humanizeIdentifier('route_baseline_v1')).toBe('Route baseline v1');
    expect(humanizeIdentifier('xgboost_v11_base_only')).toBe('XGBoost v11 base only');
  });

  it('знает аббревиатуры (POI/GRU/LSTM/CSV)', () => {
    expect(humanizeIdentifier('xgboost_v8_poi')).toBe('XGBoost v8 (POI)');
    expect(humanizeIdentifier('gru_v2_quick')).toBe('GRU v2 quick');
  });

  it('пустая строка не превращается в мусор', () => {
    expect(humanizeIdentifier('')).toBe('');
    expect(humanizeIdentifier('   ')).toBe('');
    expect(humanizeIdentifier('___')).toBe('');
  });
});

describe('featureName / featureHint', () => {
  it('известные тогглы → русские подписи из реестра', () => {
    expect(featureName('use_events', 'Events calendar (T-172)', t)).toBe('Учитывать события');
    expect(featureName('use_lag', 'Lag features (T-152)', t)).toBe('Учитывать историю');
    expect(featureName('use_poi', 'POI features (T-168)', t)).toBe('Учитывать объекты (POI)');
    expect(featureName('use_seasonal', 'Seasonal calendar', t)).toBe('Учитывать сезонность');
    expect(featureName('use_traffic', 'Traffic features (T-124)', t)).toBe('Учитывать трафик');
    expect(featureName('use_weather', 'Weather features (T-123)', t)).toBe('Учитывать погоду');
  });

  it('известные тогглы → русские пояснения (без кодов вида T-168)', () => {
    const hint = featureHint('use_events', t);
    expect(hint).toContain('событ');
    expect(hint).not.toContain('T-172');
    expect(hint).not.toMatch(/[A-Za-z]{4,}/);
  });

  it('резолвит ключи реестра, а не литералы (identity-переводчик)', () => {
    expect(featureName('use_poi', '', asKey)).toBe('analyst.featureLabels.usePoi');
    expect(featureHint('use_poi', asKey)).toBe('analyst.featureHints.usePoi');
  });

  it('неизвестный тоггл → описание из API, затем raw name', () => {
    expect(featureName('use_foo', 'Custom toggle', t)).toBe('Custom toggle');
    expect(featureName('use_foo', '', t)).toBe('use_foo');
    // неизвестный: пояснение пустое, чтобы не дублировать подпись
    expect(featureHint('use_foo', t)).toBe('');
  });
});

describe('zeroName / zeroHint', () => {
  it('известные исключения → управленческие формулировки', () => {
    expect(zeroName('zero_holidays', 'Zero federal holidays', t)).toBe('Исключить праздники');
    expect(zeroName('zero_night_pred_cap', 'Zero night hours', t)).toBe(
      'Ограничить ночной прогноз',
    );
    expect(zeroName('zero_route_5', 'Zero out route 5', t)).toBe('Исключить маршрут 5');
    expect(zeroName('zero_weekend', 'Zero weekend boardings', t)).toBe('Исключить выходные');
  });

  it('резолвит ключи реестра (identity-переводчик)', () => {
    expect(zeroName('zero_route_5', '', asKey)).toBe('analyst.zeroLabels.zeroRoute5');
    expect(zeroHint('zero_route_5', asKey)).toBe('analyst.zeroHints.zeroRoute5');
  });

  it('неизвестное исключение → описание из API, затем raw name', () => {
    expect(zeroName('zero_something', 'Mystery override', t)).toBe('Mystery override');
    expect(zeroName('zero_something', '', t)).toBe('zero_something');
  });
});

describe('modelName', () => {
  it('известные model_id → человекочитаемые имена', () => {
    expect(modelName('baseline_v1', t)).toBe('Базовая v1');
    expect(modelName('test_submission_baseline', t)).toBe('Базовый тестовый');
    expect(modelName('route_baseline_v1', t)).toBe('Базовая по маршрутам v1');
    expect(modelName('xgboost_v8_poi', t)).toBe('XGBoost v8 (POI)');
  });

  it('неизвестный model_id → generic де-снейкинг (никогда snake_case)', () => {
    const label = modelName('xgboost_v11_base_only', t);
    expect(label).toBe('XGBoost v11 base only');
    expect(label).not.toContain('_');
  });

  it('пустой id → пустая строка (caller рисует «—»)', () => {
    expect(modelName('', t)).toBe('');
  });
});

describe('featureSetName / zerosStateText', () => {
  it('feature_set → «Все факторы» / «Базовый набор» / «С учётом объектов»', () => {
    expect(featureSetName('with_all', t)).toBe('Все факторы');
    expect(featureSetName('with_poi', t)).toBe('С учётом объектов');
    expect(featureSetName('baseline', t)).toBe('Базовый набор');
  });

  it('неизвестный feature_set → де-снейкинг, пустой → пусто', () => {
    expect(featureSetName('with_events_only', t)).toBe('With events only');
    expect(featureSetName('', t)).toBe('');
    expect(featureSetName(null, t)).toBe('');
  });

  it('zeros_state → «Исключения: вкл./выкл.»', () => {
    expect(zerosStateText(true, t)).toBe('Исключения: вкл.');
    expect(zerosStateText(false, t)).toBe('Исключения: выкл.');
    expect(zerosStateText(null, t)).toBe('');
  });
});
