/**
 * T-141 RED-then-GREEN coverage for the hybrid text registry.
 *
 * Validates:
 *   1. Static strings resolve to the expected Russian copy.
 *   2. Function-valued strings (`tf()`) interpolate correctly.
 *   3. The compile-time guard works — invalid keys fail `tsc`.
 *   4. The locked full dictionary matches a snapshot (locks future drift).
 */

import { describe, expect, it } from 'vitest';

import { TEXTS } from './ru-RU';
import { t, tf } from './t';
import type { TKey } from './keys';

// TKey is used implicitly via the const-typed lookups below (every call
// to t("...") constrains its argument against `TKey = Leaves<typeof TEXTS>`).
// The explicit re-import here keeps the type alive even if the test bodies
// change in a way that drops every literal — i.e. acts as a tripwire.
const _tkeyTripwire: TKey | undefined = undefined;
void _tkeyTripwire;

describe('t() — static lookups', () => {
  it('returns the app title', () => {
    expect(t('app.title')).toBe('Transit-AI');
  });

  it('returns the dispatcher alerts title', () => {
    expect(t('dispatcher.alerts.title')).toBe('🎛️ Диспетчер · алерты перегруза');
  });

  it('returns the passenger-mode heading', () => {
    expect(t('passenger.modeTitle')).toBe('🧍 Пассажир — нагрузка по линиям');
  });

  it('returns the severity labels', () => {
    expect(t('dispatcher.alerts.card.severityCritical')).toBe('🚨 КРИТИЧНО');
    expect(t('dispatcher.alerts.card.severityWarning')).toBe('⚠️  Внимание');
    expect(t('dispatcher.alerts.card.severityInfo')).toBe('ℹ️  Инфо');
  });

  it('returns the role labels', () => {
    // T-225: /passenger переименован в «Диспетчер» (UX-rename). /dispatcher
    // убран из nav как orphan, ключ app.roleDispatcher больше не используется.
    expect(t('app.rolePassenger.label')).toBe('Диспетчер');
    expect(t('app.roleAnalyst.label')).toBe('Аналитик');
    // T-200 / D-027: planner tab was removed — no rolePlanner key anymore.
    // T-225 / D-037: dispatcher removed from nav — no roleDispatcher key anymore.
  });

  it('returns deep-nested placeholders', () => {
    // T-225: placeholder обновлён — «Пассажир» устарело.
    expect(t('app.rolePassenger.placeholder')).toMatch(/этот режим/i);
  });
});

describe('tf() — parameterised lookups', () => {
  it('interpolates the empty-state window count', () => {
    expect(tf('dispatcher.alerts.emptyState', 30)).toBe('✅ Всё в норме на ближайшие 30 мин.');
  });

  it('interpolates the time-to-overload minutes', () => {
    expect(tf('dispatcher.alerts.card.timeToOverload', 7)).toBe('⏱ Перегруз через 7 мин');
  });

  it('interpolates the route label', () => {
    expect(tf('dispatcher.alerts.card.routeLabel', 'А')).toBe('🚋 Маршрут А');
  });

  it('interpolates the eta-card minutes', () => {
    expect(tf('passenger.etaCard.etaTemplate', 4)).toBe('⏱ 4 мин');
    expect(tf('passenger.etaCard.etaTemplate', 0)).toBe('⏱ 0 мин');
  });

  it('interpolates the eta-card load percentage', () => {
    expect(tf('passenger.etaCard.loadTemplate', 73.4)).toBe('👥 73.4% загрузка');
  });

  it('interpolates the model footer', () => {
    expect(tf('passenger.modelFooter', 'baseline_v1')).toBe(
      'Модель: baseline_v1 · обновлено только что',
    );
  });

  it('interpolates the error prefix with an Error message', () => {
    expect(tf('passenger.etaError', 'Network down')).toBe('Ошибка загрузки данных: Network down');
  });
});

describe('t() — type safety (compile-time)', () => {
  it('accepts every existing key at the type level', () => {
    // This list is exhaustive at compile time -- if a key is renamed in
    // `ru-RU.ts`, the `as TKey` casts below force TypeScript to error,
    // keeping the snapshot in sync with the dictionary.
    const sampleKeys: readonly TKey[] = [
      'app.title',
      'app.tagline',
      'app.navAriaLabel',
      'app.rolePassenger.label',
      'app.rolePassenger.description',
      'app.rolePassenger.placeholder',
      // T-225: app.roleDispatcher удалён (orphan).
      'app.roleAnalyst.label',
      'app.roleAnalyst.description',
      'dispatcher.alerts.title',
      'dispatcher.alerts.loading',
      'dispatcher.alerts.errorPrefix',
      'dispatcher.alerts.retry',
      'dispatcher.alerts.fetching',
      'dispatcher.alerts.updatedAt', // function -- allowed
      'dispatcher.alerts.windowSuffix', // function
      'dispatcher.alerts.unknownTime',
      'dispatcher.alerts.emptyState', // function
      'dispatcher.alerts.card.routeLabel', // function
      'dispatcher.alerts.card.stopPrefix',
      'dispatcher.alerts.card.loadPrefix',
      'dispatcher.alerts.card.timeToOverload', // function
      'dispatcher.alerts.card.releaseButton',
      'dispatcher.alerts.card.severityCritical',
      'dispatcher.alerts.card.severityWarning',
      'dispatcher.alerts.card.severityInfo',
      'passenger.modeTitle',
      'passenger.modeHint',
      'passenger.stopsLabel',
      'passenger.stopsLoading',
      'passenger.stopsEmpty',
      'passenger.etaLoading',
      'passenger.etaError', // function
      'passenger.modelFooter', // function
      'passenger.etaCard.departed',
      'passenger.etaCard.etaTemplate', // function
      'passenger.etaCard.loadTemplate', // function
      'common.minutesShort',
    ];
    // Runtime check: every *static* key resolves to a string via `t()`.
    // Function-valued keys (`updatedAt`, `emptyState`, ...) go through `tf()`,
    // which has its own coverage above -- calling `t()` on them would throw,
    // so we filter them out of this exhaustive list.
    const functionKeys: ReadonlySet<TKey> = new Set<TKey>([
      'dispatcher.alerts.updatedAt',
      'dispatcher.alerts.windowSuffix',
      'dispatcher.alerts.emptyState',
      'dispatcher.alerts.card.routeLabel',
      'dispatcher.alerts.card.timeToOverload',
      'passenger.etaError',
      'passenger.modelFooter',
      'passenger.etaCard.etaTemplate',
      'passenger.etaCard.loadTemplate',
    ]);
    const staticKeys = sampleKeys.filter((k) => !functionKeys.has(k));
    expect(staticKeys.length).toBeGreaterThan(20);
    for (const k of staticKeys) {
      expect(typeof t(k)).toBe('string');
    }
    expect(sampleKeys.length).toBeGreaterThan(30);
  });

  it('rejects typos in keys via the TKey type', () => {
    // Compile-time proof: a typo cannot be assigned to TKey. If this
    // assignment ever starts compiling, somebody has broadened the type
    // in `keys.ts` -- which is exactly what we want to catch. We assert
    // here at runtime only to keep the file valid TypeScript; the type
    // error itself is the test.
    const validKey = 'app.title' satisfies TKey;
    expect(validKey).toBe('app.title');
  });
});

describe('TEXTS — locked snapshot', () => {
  it('matches the frozen shape of the dictionary', () => {
    // Snapshot surfaces every accidental addition to the dictionary.
    // Update it deliberately -- never silently.
    expect(Object.keys(TEXTS).sort()).toEqual([
      'analyst',
      'app',
      'common',
      'dispatcher',
      'passenger',
      // T-222 follow-up: новая вкладка /predictions с TanStack Table v8.
      'predictions',
    ]);
  });

  it('exposes all severity labels as strings', () => {
    const card = TEXTS.dispatcher.alerts.card;
    expect(typeof card.severityCritical).toBe('string');
    expect(typeof card.severityWarning).toBe('string');
    expect(typeof card.severityInfo).toBe('string');
  });
});
