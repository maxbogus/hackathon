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
      // Emoji обновлён в lib/roles.ts ( → 🎛️). Сам дашборд PassengerMode
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
    // T-222 follow-up: новая вкладка /predictions с TanStack Table v8.
    rolePredictions: {
      label: 'Прогноз · таблица',
      description: 'Все 14640 прогнозов (10 маршрутов × 61 день × 24 ч)',
    },
    // T-226: новая вкладка /historical с TanStack Table v8 (actuals).
    roleHistorical: {
      label: 'Исторические данные',
      description: 'Фактический пассажиропоток за весь период наблюдений',
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

  /* T-222 follow-up: страница /predictions — таблица прогнозов. */
  predictions: {
    viewTitle: ' Прогноз — таблица на весь период',
    /* T-231: убраны «из БД», «поиск» (нет с F-101) и «WAPE-score» (жаргон). */
    viewHint:
      'Все сохранённые прогнозы за 1 ноября — 31 декабря (10 маршрутов). Фильтры по маршрутам и сортировка по любой колонке. По умолчанию показаны 4 маршрута с наилучшей точностью прогноза.',
  },

  passenger: {
    /* T-231: экран диспетчера, а не пассажира — официальное название раздела. */
    modeTitle: ' Пассажиропоток по маршрутам',
    modeHint: 'Текущая загрузка маршрутов. Выберите маршрут для анализа или перераспределения.',
    stopsLabel: 'Остановка',
    stopsLoading: 'Загрузка остановок…',
    stopsEmpty: 'Нет маршрутов',
    /* F-097: pre-existing missing key — добавлен по дороге */
    routesEmpty: 'Нет доступных маршрутов',
    etaLoading: 'Загрузка нагрузки…',
    etaError: (msg: string) => `Ошибка загрузки данных: ${msg}`,
    /* T-231: «Точность (WAPE)» вместо жаргонного «WAPE-score», имя модели —
       человекочитаемое (см. lib/labels.ts modelName). */
    modelFooter: (modelName: string) => `Модель: ${modelName} · Обновлено только что`,
    activeModelFooter: (modelName: string, wape: string) =>
      `Модель: ${modelName} · Точность (WAPE): ${wape} · Обновлено только что`,
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
    /* T-231: строгие термины вместо разговорных «как было / как будет». */
    actualsHeader: 'Фактическая нагрузка',
    predictionsHeader: 'Прогнозируемая нагрузка',
    routeNoData: 'Нет данных',
    /* T-218+ (отзыв пользователя): карточка показывает прогноз и отклонение */
    /* T-231: заглавная буква + точка в единицах («Прогноз: 754 чел.») */
    predictedShort: 'Прогноз',
    deviationShort: 'Отклонение',
    routeNoPrediction: 'Нет прогноза',
    /* T-231: подписи отклонения actual vs prediction (RouteLoadCard footer) */
    side: {
      over: 'Перегрузка',
      under: 'Недогрузка',
      normal: 'В норме',
      unknown: 'Нет прогноза',
    },
    /* T-218+: легенда цветовой шкалы (LoadLegend.tsx) */
    /* T-231: полные существительные, без сокращений «перегруз/недогруз/откл.». */
    legend: {
      title: 'Условные обозначения',
      green: 'Норма · отклонение менее 15%',
      yellow: 'Перегрузка +15…+30% от прогноза',
      red: 'Перегрузка +30…+60%',
      darkred: 'Перегрузка · более +60%',
      lightblue: 'Недогрузка · ниже прогноза',
      gray: 'Нет данных',
    },
    /* T-222: PredictionsTable.tsx — TanStack Table v8 + virtual scroll.
       T-226 / F-101: searchPlaceholder удалён (поиск работает глючно,
       multi-select маршрутов достаточно для 10 маршрутов). */
    predictionsTable: {
      title: ' ',
      routesFilterLabel: 'Маршруты',
      columnRoute: 'Маршрут',
      columnDate: 'Дата',
      columnHour: 'Час',
      columnValue: 'Прогноз (чел.)',
      showAll: 'Выбрать все',
      collapse: 'Свернуть',
      emptyMessage: 'Нет данных за выбранный период',
      loadErrorPrefix: 'Не удалось загрузить прогноз:',
      rowsFooter: (n: number) => `строк: ${n}`,
      routesFooter: (n: number) => `маршрутов: ${n}`,
      sortAsc: 'asc',
      sortDesc: 'desc',
      sortNone: 'none',
    },
    /* T-226: HistoricalTable.tsx — TanStack Table v8 + virtual scroll,
       зеркало predictionsTable без поиска (F-101), колонка «Факт». */
    historicalTable: {
      title: '',
      routesFilterLabel: 'Маршруты',
      columnRoute: 'Маршрут',
      columnDate: 'Дата',
      columnHour: 'Час',
      columnValue: 'Факт. посадки (чел.)',
      showAll: 'Выбрать все',
      collapse: 'Свернуть',
      emptyMessage: 'Нет исторических данных за выбранный период',
      loadErrorPrefix: 'Не удалось загрузить исторические данные:',
      rowsFooter: (n: number) => `строк: ${n}`,
      routesFooter: (n: number) => `маршрутов: ${n}`,
      sortAsc: 'asc',
      sortDesc: 'desc',
      sortNone: 'none',
    },
  },

  common: {
    /* Shared, neutral Russian phrases (no domain-specific terminology). */
    minutesShort: 'мин',
    /* T-231: единица измерения пассажиропотока («754 чел.»). */
    unitPeople: 'чел.',
    loading: 'Загрузка…',
    errorPrefix: 'Ошибка:',
    retry: 'Повторить',
    yes: 'Да',
    no: 'Нет',
  },

  analyst: {
    /* T-196: Analyst dashboard — historical + predictions + feature toggles */
    title: '',
    routeLabel: 'Маршрут',
    /* T-233: текст опции селектора маршрута («Маршрут 7»). */
    routeOption: (routeId: number) => `Маршрут ${routeId}`,
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
    historicalChartTitle: 'Исторические данные (посадки)',
    predictionsChartTitle: 'Прогноз (с учётом коэффициентов)',
    noData: 'Нет данных за выбранный период',
    downloadCsv: '⬇️ Скачать CSV',
    csvDownloaded: (rows: number) => `✅ Скачано ${rows} строк`,
    csvError: 'Не удалось сгенерировать CSV',
    filtersTitle: ' Параметры прогноза',
    featuresTitle: 'Факторы прогнозирования',
    zerosTitle: 'Исключения',
    coefsTitle: 'Корректирующие коэффициенты',
    /* T-231: русские подписи/пояснения для feature_toggles из API.
       Резолв — lib/labels.ts featureName/featureHint (fallback на API-описание). */
    featureLabels: {
      usePoi: 'Учитывать объекты (POI)',
      useTraffic: 'Учитывать трафик',
      useWeather: 'Учитывать погоду',
      useEvents: 'Учитывать события',
      useSeasonal: 'Учитывать сезонность',
      useLag: 'Учитывать историю',
    },
    featureHints: {
      usePoi: 'Объекты рядом с остановками: школы, торговые центры, парки',
      useTraffic: 'Загруженность дорог и перекрёстков',
      useWeather: 'Температура воздуха и осадки',
      useEvents: 'Календарь событий: открытие инфраструктуры',
      useSeasonal: 'Праздники и школьные каникулы',
      useLag: 'История пассажиропотока по маршруту',
    },
    /* T-231: русские подписи/пояснения для zero_overrides из API. */
    zeroLabels: {
      zeroRoute5: 'Исключить маршрут 5',
      zeroNightPredCap: 'Ограничить ночной прогноз',
      zeroWeekend: 'Исключить выходные',
      zeroHolidays: 'Исключить праздники',
    },
    zeroHints: {
      zeroRoute5: 'Маршрут 5 не учитывается в прогнозе: участок закрыт',
      zeroNightPredCap: 'Ночные часы обнуляются, если прогноз ниже 55 чел.',
      zeroWeekend: 'Суббота и воскресенье обнуляются',
      zeroHolidays: 'Федеральные праздники обнуляются',
    },
    /* T-231: человекочитаемые имена моделей (см. lib/labels.ts modelName). */
    modelLabels: {
      baselineV1: 'Базовая v1',
      testSubmissionBaseline: 'Базовый тестовый',
      routeBaselineV1: 'Базовая по маршрутам v1',
      xgboostV8Poi: 'XGBoost v8 (POI)',
    },
    /* T-231: человекочитаемые имена наборов факторов (feature_set). */
    featureSets: {
      withAll: 'Все факторы',
      withPoi: 'С учётом объектов',
      baseline: 'Базовый набор',
    },
    /* T-231: состояние исключений в панели активного прогноза. */
    zerosOn: 'Исключения: вкл.',
    zerosOff: 'Исключения: выкл.',
    coefWeather: 'Погода',
    coefEvent: 'События',
    coefSeason: 'Сезон',
    defaultBadge: 'по умолчанию',
    summaryTitle: 'Сводка',
    summaryPredicted: (n: number) => `Прогнозов: ${n}`,
    summaryActual: (n: number) => `Фактов: ${n}`,
    summaryPeriod: (from: string, to: string) => `${from} → ${to}`,

    /* T-228: XLSX-экспорт (бэкенд /predictions/export.xlsx, T-206) */
    downloadXlsx: '⬇️ Скачать XLSX',
    xlsxDownloaded: (rows: number) => `✅ Скачано ${rows} строк (XLSX)`,
    xlsxError: 'Не удалось сгенерировать XLSX',

    /* T-230: наборы прогнозов — генерация, кандидат, эталон */
    howItWorksTitle: 'Как это работает',
    howItWorksStep1:
      '1. Слева выберите факторы, исключения и коэффициенты — это параметры генерации прогноза.',
    howItWorksStep2:
      '2. Нажмите «Сгенерировать прогноз»: расчёт идёт на сервере (Celery) и занимает несколько минут. График при этом показывает данные активного набора.',
    howItWorksStep3:
      '3. Когда расчёт закончится, появится кандидат: имя файла, число строк и точность прогноза (WAPE, больше — лучше).',
    howItWorksStep4:
      '4. «Загрузить и сделать активным» заменит текущие прогнозы в базе на новые; «Оставить эталон» — отменит кандидата.',
    howItWorksStep5:
      '5. Вернуться к исходному прогнозу можно в любой момент кнопкой «Восстановить исходный прогноз» — старые расчёты не удаляются.',
    howItWorksNote:
      'Прогнозы хранятся наборами: активный набор отдают все экраны (Аналитик, Диспетчер), эталон остаётся как резерв.',
    activeSetTitle: 'Активный прогноз',
    activeSetEtalonBadge: 'эталон',
    activeSetGeneratedBadge: 'сгенерирован',
    activeSetRows: 'Строк',
    activeSetHoldout: 'Точность (WAPE)',
    generateTitle: 'Генерация прогноза',
    generateButton: '▶️ Сгенерировать прогноз',
    generateRunning: '⏳ Считаем… обучение XGBoost занимает несколько минут',
    generateError: 'Не удалось запустить генерацию',
    generateWorkerHint: 'Если статус не меняется — поднимите воркер: make pipeline-up',
    candidateTitle: 'Готов новый прогноз (кандидат)',
    candidateFile: 'Файл набора',
    candidateRows: 'Строк',
    candidateLoadButton: '✅ Загрузить и сделать активным',
    candidateRejectButton: '🚫 Оставить эталон',
    candidateLoadError: 'Не удалось загрузить кандидата',
    candidateLoaded: (rows: number) => `✅ Активным стал новый набор (${rows} строк)`,
    candidateRejected: 'Кандидат отклонён — активен прежний набор',
    candidateFailed: 'Генерация не удалась',
    candidateNeedsFix: 'Файл не прошёл проверку (manifest/строки) — загрузка недоступна',
    restoreEtalonButton: 'Восстановить исходный прогноз',
    restoreEtalonDone: 'Активен исходный прогноз',
    restoreEtalonError: 'Не удалось вернуть эталон',
    recommendationReady: '✅ Лучше текущего — можно загружать',
    recommendationWorse: '⚠️ Хуже текущего — вероятно, не стоит',
    recommendationIdentical: '≈ Такой же, как текущий',
    recommendationNeedsFix: '⛔ Файл невалиден (NEEDS_FIX)',
    chartFallbackNote:
      'Показан активный набор: для текущих коэффициентов прогноз ещё не сгенерирован',
    runStatusLabel: (status: string) => `статус: ${status}`,
  },

  /* T-226: HistoricalView.tsx — header для страницы /historical */
  historical: {
    viewTitle: 'Исторические данные',
    /* T-231: убран технический «(из БД)» — пользователю не важен источник. */
    viewHint: 'Фактический пассажиропоток за весь период наблюдений',
  },

  /* T-122/T-227: components/Map — карта маршрутов на дашборде «Диспетчер».
     Цвет линии/точек = tier из /predictions/load (как у карточек, clinerule 31). */
  map: {
    title: '🗺️ Карта маршрутов',
    ariaLabel: 'Карта трамвайных маршрутов Москвы',
    hint: 'Клик по карточке или линии подсвечивает маршрут, остальные остаются контекстом',
    empty: 'Геоданные маршрутов недоступны',
    noKey: 'Яндекс.Карты недоступны: ключ не задан или некорректен — показана карта OpenStreetMap.',
    routeLabel: (routeId: number) => `Маршрут ${routeId}`,
  },
} as const;
