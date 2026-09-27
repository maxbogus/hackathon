/**
 * T-122 / D-003: Strategy-выбор реализации карты (OSM ↔ Yandex) через env.
 *
 * Вынесено из `MapProvider.tsx` намеренно: файл с React-компонентом не должен
 * экспортировать обычные функции (eslint `react-refresh/only-export-components`
 * — при `--max-warnings=0` это блокирует `yarn lint`). Плюс чистую функцию
 * проще покрыть тестами без рендера.
 */

export type MapImplKind = 'osm' | 'yandex';

/**
 * Какая реализация рендерится.
 *
 * Яндекс выбирается ТОЛЬКО когда он явно запрошен в env (`VITE_MAP_IMPL=yandex`)
 * И есть реальный ключ (`getYandexMapsKeyOrNull() !== null`). Иначе — OSM
 * (Leaflet, без ключей): демо не должно зависеть от наличия/валидности ключа.
 */
export function selectMapImpl(impl: string | undefined | null, hasYandexKey: boolean): MapImplKind {
  return impl === 'yandex' && hasYandexKey ? 'yandex' : 'osm';
}
