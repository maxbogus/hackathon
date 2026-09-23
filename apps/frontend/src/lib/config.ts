/**
 * Config — типизированный слой загрузки .env с stub-fallback.
 *
 * Поведение (см. config.test.ts):
 * - loadConfig() возвращает полную структуру AppConfig.
 * - Строковые секреты/ключи → ConfigEntry<string> (real либо stub с reason).
 * - Stub-детекция: пустая строка ИЛИ regex `^your_.*_here$`.
 * - Числа/булевы (temperature/maxTokens/reasoningEnabled) → plain.
 *
 * Почему не скрытые секреты в `t()` (i18n):
 * - эти сообщения никогда не показываются пользователю (reason — для dev).
 * - миграция тривиальна когда появится UI-баннер.
 *
 * Никаких побочных эффектов. Совместимо с vi.stubEnv() в тестах.
 */

export type ConfigSource = 'real' | 'stub';

/** Универсальный контейнер: либо реальное значение, либо заглушка с метаданными. */
export type ConfigEntry<T> =
  { source: 'real'; value: T } | { source: 'stub'; value: T; reason: string };

export type MapImpl = 'osm' | 'yandex';
export type SearchProvider = 'overpass' | '2gis' | 'yandex';
export type LLMType = 'openrouter' | 'anthropic' | 'gigachat' | 'reasoning' | 'deepseek';

export interface MapConfig {
  impl: MapImpl;
  yandexMapsKey: ConfigEntry<string>;
  yandexGeocoderKey: ConfigEntry<string>;
  geocoderUrl: string;
}

export interface SearchConfig {
  provider: SearchProvider;
  twogisKey: ConfigEntry<string>;
}

export interface LLMConfig {
  type: LLMType;
  model: string;
  temperature: number;
  maxTokens: number;
  reasoningEnabled: boolean;
  openrouterKey: ConfigEntry<string>;
  anthropicKey: ConfigEntry<string>;
  gigachatCredentials: ConfigEntry<string>;
}

export interface AppConfig {
  map: MapConfig;
  search: SearchConfig;
  llm: LLMConfig;
}

// === Helpers ============================================================

const PLACEHOLDER_RE = /^your_.*_here$/;

function readEnv(key: string): string {
  // import.meta.env значения всегда string | undefined
  const value = import.meta.env[key];
  return typeof value === 'string' ? value : '';
}

function entryFor(envKey: string, friendlyAction: string): ConfigEntry<string> {
  const raw = readEnv(envKey);
  if (raw === '') {
    return {
      source: 'stub',
      value: raw,
      reason:
        `Не задан "${envKey}" в .env. ${friendlyAction} ` +
        `Скопируйте .env.example → .env и подставьте реальный ключ.`,
    };
  }
  if (PLACEHOLDER_RE.test(raw)) {
    return {
      source: 'stub',
      value: raw,
      reason:
        `"${envKey}" всё ещё равен плейсхолдеру из .env.example (${raw}). ` +
        `${friendlyAction} Подставьте настоящее значение.`,
    };
  }
  return { source: 'real', value: raw };
}

// === Public API =========================================================

export function loadConfig(): AppConfig {
  return {
    map: {
      impl: (readEnv('VITE_MAP_IMPL') as MapImpl) || 'osm',
      yandexMapsKey: entryFor(
        'VITE_YANDEX_MAPS_API_KEY',
        'Карта отображается через OpenStreetMap.',
      ),
      yandexGeocoderKey: entryFor(
        'VITE_YANDEX_GEOCODER_API_KEY',
        'Обратный геокодинг через Яндекс недоступен.',
      ),
      geocoderUrl: readEnv('VITE_YANDEX_GEOCODER_URL') || 'https://geocode-maps.yandex.ru/1.x',
    },
    search: {
      provider: (readEnv('VITE_SEARCH_PROVIDER') as SearchProvider) || 'overpass',
      twogisKey: entryFor('VITE_TWOGIS_API_KEY', 'Поиск через 2ГИС недоступен.'),
    },
    llm: {
      type: (readEnv('LLM_TYPE') as LLMType) || 'openrouter',
      model: readEnv('LLM_MODEL') || 'openai/gpt-4o-mini',
      temperature: Number(readEnv('LLM_TEMPERATURE') || '0.3'),
      maxTokens: Number(readEnv('LLM_MAX_TOKENS') || '2000'),
      reasoningEnabled: (readEnv('LLM_REASONING_ENABLED') || 'false').toLowerCase() === 'true',
      openrouterKey: entryFor(
        'OPENROUTER_API_KEY',
        'Ассистент работает в demo-режиме без OpenRouter.',
      ),
      anthropicKey: entryFor('ANTHROPIC_API_KEY', 'Антропик-провайдер недоступен.'),
      gigachatCredentials: entryFor('GIGACHAT_CREDENTIALS', 'GigaChat-провайдер недоступен.'),
    },
  };
}

export function hasRealYandexMapsKey(): boolean {
  return loadConfig().map.yandexMapsKey.source === 'real';
}

export function getYandexMapsKeyOrNull(): string | null {
  const e = loadConfig().map.yandexMapsKey;
  return e.source === 'real' ? e.value : null;
}

export function getStubMessage(entry: ConfigEntry<unknown>): string | null {
  return entry.source === 'stub' ? entry.reason : null;
}
