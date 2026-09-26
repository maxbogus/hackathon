/**
 * T-141: Hybrid text registry — Russian dictionary.
 *
 * Single source of truth for all user-facing strings in the frontend.
 * Type `TKey` (see `./keys.ts`) is derived from the *shape* of this object
 * — adding a new leaf automatically adds a new compile-checked key.
 *
 * Conventions:
 *   - All values are Russian (MVP audience — Moscow tram passengers).
 *   - Branded/sealed with `as const` so TS narrows literals, not types.
 *   - Functions (e.g. lastUpdate(n)) live alongside their static siblings;
 *     see `./t.ts` for the dispatcher (`tf(key, ...args)`).
 *   - Reuse keys across components; if a string is identical in two places
 *     it is the same key (keeps the dictionary small and grep-able).
 *
 * When you add a new UI string:
 *   1. Add it here under the right namespace (app | dispatcher | passenger | common).
 *   2. Run `yarn typecheck` — TypeScript will surface stale call sites.
 *   3. Record the migration in `./MIGRATION.md`.
 *
 * T-141 acceptance: every JSX literal in `components/`, `pages/`, `App.tsx`
 * has been lifted out into one of the keys below.
 */

export const TEXTS = {
  app: {
    title: 'Transit-AI',
    tagline: 'Хакатон: прогноз загрузки трамваев Москвы',
    navAriaLabel: 'Переключатель ролей',
    /* App.tsx role-switcher buttons (T-141 replaces 4 hardcoded RoleDef literals) */
    rolePassenger: {
      label: 'Пассажир',
      description: 'Когда приедет трамвай и будет ли место?',
      placeholder: 'Этот режим появится в следующих тикетах. Сейчас готов только режим «Пассажир».',
    },
    roleDispatcher: {
      label: 'Диспетчер',
      description: 'Алерты по перегрузу (T-131)',
    },
    roleAnalyst: {
      label: 'Аналитик',
      description: 'Графики и метрики (T-035/037)',
    },
    rolePlanner: {
      label: 'Планировщик',
      description: 'Monte Carlo сценарии (T-036)',
    },
  },

  dispatcher: {
    alerts: {
      title: '🎛️ Диспетчер · алерты перегруза',
      loading: 'Загрузка алертов…',
      errorPrefix: 'Не удалось загрузить алерты:',
      retry: 'Повторить',
      fetching: 'обновление…',
      updatedAt: (time: string) => `обновлено: ${time}`,
      windowSuffix: (min: number) => ` · горизонт ${min} мин`,
      unknownTime: '—',
      emptyState: (min: number) => `✅ Всё в норме на ближайшие ${min} мин.`,
      card: {
        routeLabel: (name: string) => `🚋 Маршрут ${name}`,
        stopPrefix: 'Остановка',
        loadPrefix: 'прогноз загрузки:',
        timeToOverload: (min: number) => `⏱ Перегруз через ${min} мин`,
        releaseButton: '🚌 Выпустить вагон',
        severityCritical: '🚨 КРИТИЧНО',
        severityWarning: '⚠️  Внимание',
        severityInfo: 'ℹ️  Инфо',
      },
    },
  },

  passenger: {
    modeTitle: '🧍 Пассажир — ближайшие трамваи',
    modeHint: 'Выберите остановку, чтобы увидеть прогноз прибытия и загрузки.',
    stopsLabel: 'Остановка',
    stopsLoading: 'Загрузка остановок…',
    stopsEmpty: 'Нет остановок',
    etaLoading: 'Загрузка прогнозов…',
    etaError: (msg: string) => `Ошибка загрузки данных: ${msg}`,
    modelFooter: (modelId: string) => `Модель: ${modelId} · обновлено только что`,
    /* EtaCard.tsx — small visual primitives */
    etaCard: {
      departed: '🚉 Ушёл',
      etaTemplate: (min: number) => `⏱ ${min} мин`,
      loadTemplate: (pct: number) => `👥 ${pct}% загрузка`,
    },
  },

  common: {
    /* Shared, neutral Russian phrases (no domain-specific terminology). */
    minutesShort: 'мин',
    loading: 'Загрузка…',
    errorPrefix: 'Ошибка:',
    retry: 'Повторить',
    yes: 'Да',
    no: 'Нет',
  },

  analyst: {
    /* T-196: Analyst dashboard — historical + predictions + feature toggles */
    title: '📊 Аналитик — данные и прогнозы',
    routeLabel: 'Маршрут',
    fromLabel: 'Период с',
    toLabel: 'Период по',
    granularityDay: 'По дням',
    granularityHour: 'По часам',
    historicalChartTitle: 'Исторические данные (boardings)',
    predictionsChartTitle: 'Прогноз (с учётом коэффициентов)',
    noData: 'Нет данных за выбранный период',
    downloadCsv: '⬇️ Скачать CSV',
    csvDownloaded: (rows: number) => `✅ Скачано ${rows} строк`,
    csvError: 'Не удалось сгенерировать CSV',
    filtersTitle: '⚙️ Параметры прогноза',
    featuresTitle: 'Фичи модели',
    zerosTitle: 'Обнуление',
    coefWeather: 'Погода',
    coefEvent: 'События',
    coefSeason: 'Сезон',
    defaultBadge: 'по умолчанию',
    summaryTitle: 'Сводка',
    summaryPredicted: (n: number) => `Прогнозов: ${n}`,
    summaryActual: (n: number) => `Фактов: ${n}`,
    summaryPeriod: (from: string, to: string) => `${from} → ${to}`,
  },
} as const;
