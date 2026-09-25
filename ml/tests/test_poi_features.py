"""Tests for poi_features.py (T-168).

RED-then-GREEN тесты. Проверяют:
1. POI catalog: 146 объектов в 13 категориях, валидная schema.
2. Stops catalog: 142 остановки 10 маршрутов.
3. count_poi_for_stop: работает для остановок с известными POI.
4. dist_to_nearest: расстояние до метро (route 26 = Метро Университет).
5. get_stop_poi_features: 15 фичей, реальные значения для остановок route 26/50.
6. build_all_route_poi_features: 142 строки, 15 фичей.
"""

from __future__ import annotations

from pathlib import Path

from transit_ai.data.poi_features import (
    POI_FEATURE_NAMES,
    build_all_route_poi_features,
    count_poi_for_stop,
    dist_to_nearest,
    get_route_poi_features,
    get_stop_poi_features,
    load_poi_catalog,
    load_stops_catalog,
)

# --- Acceptance 1: load_poi_catalog() работает ---


def test_load_poi_catalog_returns_non_empty_list() -> None:
    """T-168: каталог POI загружается, >=100 точек (расширили с 50 до 100+)."""
    catalog = load_poi_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) >= 100, f"Expected >=100 POI, got {len(catalog)}"


def test_load_poi_catalog_has_required_fields() -> None:
    """T-168: каждая POI имеет name/category/lat/lon + 13 категорий."""
    catalog = load_poi_catalog()
    required = {"name", "category", "lat", "lon"}
    valid_categories = {
        "school",
        "university",
        "stadium",
        "park",
        "mall",
        "theater",
        "culture",
        "market",
        "clinic",
        "hospital",
        "cinema",
        "train_station",
        "metro_hub",
    }
    cats_found = set()
    for p in catalog:
        assert required.issubset(p.keys()), f"Missing fields in {p}"
        assert p["category"] in valid_categories, f"Bad category: {p['category']}"
        cats_found.add(p["category"])
        assert isinstance(p["lat"], (int, float))
        assert isinstance(p["lon"], (int, float))
        assert 55.0 <= p["lat"] <= 56.0, f"Lat out of Moscow: {p['lat']}"
        assert 37.0 <= p["lon"] <= 38.0, f"Lon out of Moscow: {p['lon']}"
    # Покрытие >= 11 из 13 категорий (минимум)
    assert len(cats_found) >= 11, f"Only {len(cats_found)} categories: {cats_found}"


# --- Acceptance 2: stops_routes.json работает ---


def test_load_stops_catalog_has_all_10_routes() -> None:
    """T-168: все 10 маршрутов имеют остановки."""
    stops = load_stops_catalog()
    expected_routes = {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}
    assert set(stops.keys()) == expected_routes, f"Got: {set(stops.keys())}"
    # Минимум 5 остановок на маршрут
    for route_id, route_stops in stops.items():
        assert len(route_stops) >= 5, f"Route {route_id}: only {len(route_stops)} stops"


def test_stop_has_name_lat_lon() -> None:
    """T-168: каждая остановка имеет name/lat/lon, координаты в Москве."""
    stops = load_stops_catalog()
    for route_id, route_stops in stops.items():
        for stop in route_stops:
            assert "name" in stop
            assert "lat" in stop and "lon" in stop
            assert 55.0 <= stop["lat"] <= 56.0
            assert 37.0 <= stop["lon"] <= 38.0


# --- Acceptance 3: count_poi_for_stop работает ---


def test_count_university_near_metro_universitet() -> None:
    """T-168: Метро Университет → МГУ в 1.5km (МГУ ~1.28km)."""
    n = count_poi_for_stop(lat=55.6925, lon=37.5345, category="university")
    assert n >= 1, f"Expected МГУ near Метро Университет, got {n}"


def test_count_metro_hub_near_metro_universitet() -> None:
    """T-168: Метро Университет → есть metro_hub в 1km (сама остановка)."""
    n = count_poi_for_stop(lat=55.6925, lon=37.5345, category="metro_hub")
    assert n >= 1, f"Expected metro_hub near Метро Университет, got {n}"


def test_count_theaters_near_teatr_durova_stop() -> None:
    """T-168: Театр Дурова (route 7/50) → theater в 1km."""
    # Театр Дурова = route 50, остановка
    n = count_poi_for_stop(lat=55.7792, lon=37.6208, category="theater")
    assert n >= 1, f"Expected theater near Театр Дурова, got {n}"


def test_count_train_station_near_belorusskaya() -> None:
    """T-168: Белорусский вокзал (route 5/7) → train_station в 1km."""
    n = count_poi_for_stop(lat=55.7764, lon=37.5821, category="train_station")
    assert n >= 1, f"Expected train_station near Белорусский вокзал, got {n}"


# --- Acceptance 4: dist_to_nearest работает ---


def test_dist_to_nearest_metro_for_route_26_is_close() -> None:
    """T-168: route 26 mid → dist_to_nearest_metro < 4km (Университет ~3.2km)."""
    # route 26 mid = (55.7111, 37.5729) — Метро Университет ~3.2km, Октябрьская ~3.2km
    d = dist_to_nearest(lat=55.7111, lon=37.5729, category="metro_hub")
    assert d < 4.0, f"Expected metro <4km, got {d:.2f}km"


def test_dist_to_nearest_university_for_route_50_is_close() -> None:
    """T-168: route 50 mid → dist_to_nearest_university < 3km (Бауманка)."""
    d = dist_to_nearest(lat=55.7748, lon=37.6451, category="university")
    assert d < 3.0, f"Expected university <3km, got {d:.2f}km"


# --- Acceptance 5: get_stop_poi_features возвращает 15 фичей ---


def test_get_stop_poi_features_has_15_features() -> None:
    """T-168: dict с 15 ключами из POI_FEATURE_NAMES."""
    feats = get_stop_poi_features(lat=55.6925, lon=37.5345)
    assert set(feats.keys()) == set(POI_FEATURE_NAMES), (
        f"Missing: {set(POI_FEATURE_NAMES) - set(feats.keys())}, "
        f"Extra: {set(feats.keys()) - set(POI_FEATURE_NAMES)}"
    )
    assert len(feats) == 15


def test_get_stop_poi_features_values_non_negative() -> None:
    """T-168: все значения >= 0 (counts) и >= 0 для dist (km)."""
    feats = get_stop_poi_features(lat=55.6925, lon=37.5345)
    for k, v in feats.items():
        assert v >= 0, f"{k} negative: {v}"


def test_get_stop_poi_features_metro_universitet_has_high_poi_score() -> None:
    """T-168: Метро Университет → много POI (МГУ + metro + school рядом)."""
    feats = get_stop_poi_features(lat=55.6925, lon=37.5345)
    # Имя колонки генерируется динамически (n_universities_1500m)
    n_uni_col = [k for k in feats if k.startswith("n_universit")][0]
    n_metro_col = [k for k in feats if k.startswith("n_metro_hub")][0]
    assert feats[n_uni_col] >= 1, f"Expected МГУ, got {feats[n_uni_col]}"
    assert feats[n_metro_col] >= 1, f"Expected metro, got {feats[n_metro_col]}"
    assert feats["poi_score"] > 5, f"Expected poi_score > 5, got {feats['poi_score']}"


# --- Acceptance 6: build_all_route_poi_features shape ---


def test_build_all_route_poi_features_shape() -> None:
    """T-168: 142 строки (10 маршрутов × в среднем 14 остановок), 15 фичей."""
    df = build_all_route_poi_features()
    assert df.shape[0] == 142, f"Expected 142 stops, got {df.shape[0]}"
    assert df.shape[1] == 15 + 2, (
        f"Expected 17 cols (15 feats + route_id + stop_name), got {df.shape[1]}"
    )
    assert "route_id" in df.columns
    assert "stop_name" in df.columns
    assert set(POI_FEATURE_NAMES).issubset(set(df.columns))


def test_build_all_route_poi_features_values_non_negative() -> None:
    """T-168: все счётные фичи >= 0."""
    df = build_all_route_poi_features()
    for col in POI_FEATURE_NAMES:
        if col.startswith("n_"):
            assert (df[col] >= 0).all(), f"{col} has negatives"


def test_get_route_poi_features_route_26_has_universities() -> None:
    """T-168: route 26 (Метро Университет → Октябрьская) имеет n_universities > 0."""
    df = get_route_poi_features(route_id=26)
    assert df.shape[0] == 9, f"Expected 9 stops, got {df.shape[0]}"
    n_uni_col = [c for c in df.columns if c.startswith("n_universit")][0]
    assert (df[n_uni_col] > 0).any(), (
        f"Route 26 should have at least one stop near university: {df[n_uni_col].tolist()}"
    )


# --- Acceptance 7: файлы существуют и не пустые ---


def test_poi_catalog_file_exists() -> None:
    """T-168: файл data/external/poi_moscow.json существует и не пустой."""
    path = Path(__file__).resolve().parents[2] / "data" / "external" / "poi_moscow.json"
    assert path.exists(), f"POI catalog not found: {path}"
    assert path.stat().st_size > 5000, (
        f"POI catalog too small: {path.stat().st_size} bytes"
    )


def test_stops_catalog_file_exists() -> None:
    """T-168: файл data/external/stops_routes.json существует и не пустой."""
    path = (
        Path(__file__).resolve().parents[2] / "data" / "external" / "stops_routes.json"
    )
    assert path.exists(), f"Stops catalog not found: {path}"
    assert path.stat().st_size > 5000, (
        f"Stops catalog too small: {path.stat().st_size} bytes"
    )
