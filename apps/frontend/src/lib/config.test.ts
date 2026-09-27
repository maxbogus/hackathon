/**
 * Config — типизированный слой загрузки .env с stub-fallback.
 *
 * Поведение:
 * - строка из import.meta.env либо попадает в {source:'real',value}, либо
 *   в {source:'stub',value,reason} если она пустая или матчит плейсхолдер
 *   из .env.example (паттерн: `^your_.*_here$`).
 * - Числа (temperature, maxTokens) и булевы (reasoningEnabled) — plain.
 *
 * TDD-цикл: см. `.clinerules/16-tdd-cycle.md`.
 * Никаких побочных эффектов (не пишет в env, не делает fetch).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  loadConfig,
  hasRealYandexMapsKey,
  getYandexMapsKeyOrNull,
  getStubMessage,
  type ConfigEntry,
} from './config';

const PLACEHOLDER_KEY = 'your_key_here';
const PLACEHOLDER_2GIS = 'your_2gis_key_here';
const REAL_KEY = 'abc123-def456-789-real-api-key-zzz';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('loadConfig() — структура', () => {
  it('возвращает объект со всеми секциями (map, search, llm)', () => {
    const cfg = loadConfig();
    expect(cfg).toHaveProperty('map');
    expect(cfg).toHaveProperty('search');
    expect(cfg).toHaveProperty('llm');
  });

  it('map.impl приходит строкой из VITE_MAP_IMPL', () => {
    vi.stubEnv('VITE_MAP_IMPL', 'yandex');
    expect(loadConfig().map.impl).toBe('yandex');
  });

  it('map.impl дефолтит в osm при отсутствии env', () => {
    // T-122: Vite читает КОРНЕВОЙ .env (envDir в vite.config.ts), где в дев-режиме
    // может стоять VITE_MAP_IMPL=yandex. «Отсутствие значения» моделируем явной
    // пустой строкой, чтобы тест не зависел от локального .env разработчика.
    vi.stubEnv('VITE_MAP_IMPL', '');
    expect(loadConfig().map.impl).toBe('osm');
  });

  it('llm.temperature приходит как plain number', () => {
    vi.stubEnv('LLM_TEMPERATURE', '0.7');
    expect(typeof loadConfig().llm.temperature).toBe('number');
    expect(loadConfig().llm.temperature).toBe(0.7);
  });
});

describe('ConfigEntry — детекция stub vs real', () => {
  it('пустая строка → stub с reason про пустоту', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', '');
    const key = loadConfig().map.yandexMapsKey;
    expect(key.source).toBe('stub');
    if (key.source === 'stub') {
      expect(key.reason).toMatch(/VITE_YANDEX_MAPS_API_KEY/);
      expect(key.reason.toLowerCase()).toContain('.env');
    }
  });

  it('плейсхолдер "your_key_here" → stub', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', PLACEHOLDER_KEY);
    expect(loadConfig().map.yandexMapsKey.source).toBe('stub');
  });

  it('плейсхолдер с произвольным префиксом "your_2gis_key_here" → stub', () => {
    vi.stubEnv('VITE_TWOGIS_API_KEY', PLACEHOLDER_2GIS);
    expect(loadConfig().search.twogisKey.source).toBe('stub');
  });

  it('плейсхолдер "your_some_custom_thing_here" → stub (regex-матч)', () => {
    vi.stubEnv('OPENROUTER_API_KEY', 'your_some_custom_thing_here');
    expect(loadConfig().llm.openrouterKey.source).toBe('stub');
  });

  it('реальный ключ "abc123..." → real с тем же value', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', REAL_KEY);
    const key = loadConfig().map.yandexMapsKey;
    expect(key.source).toBe('real');
    if (key.source === 'real') {
      expect(key.value).toBe(REAL_KEY);
    }
  });

  it('reason у stub содержит ключ смены переменной (actionable)', () => {
    vi.stubEnv('OPENROUTER_API_KEY', PLACEHOLDER_KEY);
    const c = loadConfig().llm.openrouterKey;
    if (c.source === 'stub') {
      expect(c.reason).toContain('OPENROUTER_API_KEY');
    } else {
      throw new Error('expected stub');
    }
  });
});

describe('hasRealYandexMapsKey()', () => {
  it('true когда ключ настоящий', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', REAL_KEY);
    expect(hasRealYandexMapsKey()).toBe(true);
  });

  it('false когда ключ отсутствует', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', '');
    expect(hasRealYandexMapsKey()).toBe(false);
  });

  it('false когда ключ = плейсхолдер', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', PLACEHOLDER_KEY);
    expect(hasRealYandexMapsKey()).toBe(false);
  });
});

describe('getYandexMapsKeyOrNull()', () => {
  it('возвращает ключ когда real', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', REAL_KEY);
    expect(getYandexMapsKeyOrNull()).toBe(REAL_KEY);
  });

  it('возвращает null когда stub', () => {
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', PLACEHOLDER_KEY);
    expect(getYandexMapsKeyOrNull()).toBeNull();
  });
});

describe('getStubMessage()', () => {
  it('возвращает null для real entry', () => {
    const real: ConfigEntry<string> = { source: 'real', value: REAL_KEY };
    expect(getStubMessage(real)).toBeNull();
  });

  it('возвращает reason для stub entry', () => {
    const stub: ConfigEntry<string> = {
      source: 'stub',
      value: '',
      reason: 'abc',
    };
    expect(getStubMessage(stub)).toBe('abc');
  });
});

describe('loadConfig() — покрытие всех ключей', () => {
  it('search.provider дефолтит в "overpass"', () => {
    expect(loadConfig().search.provider).toBe('overpass');
  });

  it('search.provider приходит из VITE_SEARCH_PROVIDER', () => {
    vi.stubEnv('VITE_SEARCH_PROVIDER', '2gis');
    expect(loadConfig().search.provider).toBe('2gis');
  });

  it('llm.openrouterKey детектит stub при пустом', () => {
    vi.stubEnv('OPENROUTER_API_KEY', '');
    expect(loadConfig().llm.openrouterKey.source).toBe('stub');
  });

  it('llm.openrouterKey детектит real', () => {
    vi.stubEnv('OPENROUTER_API_KEY', 'sk-real-token');
    const k = loadConfig().llm.openrouterKey;
    expect(k.source).toBe('real');
    if (k.source === 'real') {
      expect(k.value).toBe('sk-real-token');
    }
  });

  it('llm.anthropicKey детектит stub', () => {
    vi.stubEnv('ANTHROPIC_API_KEY', PLACEHOLDER_KEY);
    expect(loadConfig().llm.anthropicKey.source).toBe('stub');
  });

  it('llm.gigachatCredentials детектит stub', () => {
    vi.stubEnv('GIGACHAT_CREDENTIALS', '');
    expect(loadConfig().llm.gigachatCredentials.source).toBe('stub');
  });
});
