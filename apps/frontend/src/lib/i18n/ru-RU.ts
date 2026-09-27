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
      // T-225 / D-037: «Пассажир» в nav переименован в «Диспетчер» (UX-rename).
      // Emoji обновлён в lib/roles.ts (🧍 → 🎛️). Сам дашборд PassengerMode
      // (страница /passenger) сохраняет имя «Пассажир — нагрузка по линиям»
      // в passenger.modeTitle — это название страницы, а не роль в nav.
      label: 'Диспетчер',
      description: 'Когда приедет трамвай и будет ли место?',
      placeholder:
        'Этот режим сейчас в активной разработке. Показаны реальные и прогнозные данные по маршрутам.',
    },
    // T-225 / D-037: блок app.roleDispatcher удалён (orphan, /dispatcher
    // остался как orphan-роут для прямого URL — см. routes/dispatcher.tsx).
    roleAnalyst: {
      label: 'Аналитик',
      description: 'Графики и метрики (T-035/037)',
    },
    // T-200 / D-027: planner tab was removed — no rolePlanner key anymore.
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
      /* F-097: новый суффикс для horizon label (day|month|year) */
      horizonSuffix: (horizon: string) => ` · горизонт ${horizon}`,
      unknownTime: '—',
      emptyState: (min: number) => `✅ Всё в норме на ближайшие ${min} мин.`,
      emptyStateNoMin: '✅ Всё в норме на выбранный горизонт.',
      /* T-200 (новая редакция): 3 горизонта вместо 30 мин */
      horizonGroupLabel: 'Горизонт прогноза',
      horizon1Day: '1 день',
      horizon3Months: '3 месяца',
      horizon1Year: '1 год',
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
    modeTitle: '🧍 Пассажир — нагрузка по линиям',
    modeHint: 'Текущая загрузка каждого маршрута. Выберите свободный — и езжайте.',
    stopsLabel: 'Остановка',
    stopsLoading: 'Загрузка остановок…',
    stopsEmpty: 'Нет маршрутов',
    /* F-097: pre-existing missing key — добавлен по дороге */
    routesEmpty: 'Нет доступных маршрутов',
    etaLoading: 'Загрузка нагрузки…',
    etaError: (msg: string) => `Ошибка загрузки данных: ${msg}`,
    modelFooter: (modelId: string) => `Модель: ${modelId} · обновлено только что`,
    activeModelFooter: (modelId: string, wape: string) =>
      `Модель: ${modelId} · WAPE-score ${wape} · обновлено только что`,
    /* EtaCard.tsx — small visual primitives */
    etaCard: {
      departed: '🚉 Ушёл',
      etaTemplate: (min: number) => `⏱ ${min} мин`,
      loadTemplate: (pct: number) => `👥 ${pct}% загрузка`,
    },
    /* T-200 (новая редакция): легенда загрузки по 4 уровням */
    loadTier: {
      green: 'свободно',
      yellow: 'умеренно',
      red: 'тесно',
      darkred: 'перегруз',
    },
    /* T-218: PassengerMode показывает ДВА блока (clinerule 31) */
    actualsHeader: 'Как было (факт)',
    predictionsHeader: 'Как будет (прогноз)',
    routeNoData: 'нет данных',
    /* T-218+ (отзыв пользователя): карточка показывает прогноз и отклонение */
    predictedShort: 'прогноз',
    deviationShort: 'отклонение',
    routeNoPrediction: 'нет прогноза',
    /* T-218+: легенда цветовой шкалы (LoadLegend.tsx) */
    legend: {
      title: 'Условные обозначения',
      green: 'в норме · |откл| < 15%',
      yellow: '+15..+30% от прогноза',
      red: '+30..+60%',
      darkred: 'перегруз +60%+',
      lightblue: 'недогруз · меньше чем ожидалось',
      gray: 'нет данных',
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
    horizonLabel: 'Горизонт',
    granularityLabel: 'Детализация',
    horizonDay: 'День',
    horizonMonth: 'Месяц',
    horizonYear: 'Год',
    granularityDay: 'По дням',
    granularityHour: 'По часам',
    granularityMonth: 'По месяцам',
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
