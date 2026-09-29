from __future__ import annotations

from pathlib import Path

import pytest

from fotos_plus.places import (
    Country,
    CountryDataError,
    CountryIndex,
    _build_index,
    countries_version,
    country_of,
)

BUENOS_AIRES = (-34.6037, -58.3816)
BARCELONA = (41.3874, 2.1686)
MAR_DEL_PLATA = (-38.0023, -57.5526)
MONTEVIDEO = (-34.9011, -56.1645)
PUNTA_DEL_ESTE = (-34.9545, -54.9317)
FOZ_DO_IGUAZU = (-25.5478, -54.5883)
CIUDAD_DEL_ESTE = (-25.5095, -54.6112)
RIO_DE_JANEIRO = (-22.9068, -43.1729)
ATLANTICO_MEDIO = (-35.0, -20.0)
PACIFICO_ABIERTO = (-30.0, -140.0)


def country_name(latitude: float, longitude: float) -> str | None:
    country = country_of(latitude, longitude)
    return country.name if country is not None else None


def test_carga_el_conjunto_y_declara_una_version():
    version = countries_version()
    assert isinstance(version, int)
    assert version >= 1


def test_carga_el_archivo_una_sola_vez_por_proceso():
    primero = countries_version()
    segundo = countries_version()
    assert primero == segundo


def test_reconoce_paises_conocidos():
    assert country_name(*BUENOS_AIRES) == "Argentina"
    assert country_name(*BARCELONA) == "Spain"


def test_reconoce_ciudades_costeras_que_una_escala_menor_recorta():
    assert country_name(*MAR_DEL_PLATA) == "Argentina"
    assert country_name(*MONTEVIDEO) == "Uruguay"
    assert country_name(*PUNTA_DEL_ESTE) == "Uruguay"
    assert country_name(*RIO_DE_JANEIRO) == "Brazil"


def test_reconoce_la_frontera_entre_paraguay_y_brasil():
    assert country_name(*CIUDAD_DEL_ESTE) == "Paraguay"
    assert country_name(*FOZ_DO_IGUAZU) == "Brazil"


def test_no_inventa_el_pais_mas_cercano_en_agua():
    assert country_of(*ATLANTICO_MEDIO) is None
    assert country_of(*PACIFICO_ABIERTO) is None


def test_hemisferio_sur_y_oeste():
    assert country_name(-33.4484, -70.6693) == "Chile"
    assert country_name(-12.0464, -77.0428) == "Peru"


def test_antimeridiano_sobre_isla():
    assert country_name(-17.7134, 178.065) == "Fiji"
    assert country_name(-18.1416, 178.4419) == "Fiji"


def test_coordenadas_ausentes_o_invalidas_no_clasifican():
    assert country_of(None, None) is None
    assert country_of(-34.6037, None) is None
    assert country_of(None, -58.3816) is None
    assert country_of(95.0, 10.0) is None
    assert country_of(10.0, 200.0) is None


def test_punto_en_el_borde_de_un_poligono_es_indefinido_pero_estable():
    country = country_of(*BARCELONA)
    again = country_of(*BARCELONA)
    assert country == again


def test_indice_y_recorrido_lineal_coinciden():
    from fotos_plus.places import _load_index

    index = _load_index()
    malla = index.country_of
    lineal = _linear_lookup(index)
    for latitude, longitude in (
        BUENOS_AIRES,
        BARCELONA,
        MONTEVIDEO,
        RIO_DE_JANEIRO,
        ATLANTICO_MEDIO,
        PACIFICO_ABIERTO,
    ):
        assert malla(latitude, longitude) == lineal(latitude, longitude)


def test_el_conjunto_tiene_paises_para_todo_el_mapa_con_tomas_frecuentes():
    from fotos_plus.places import _load_index

    index = _load_index()
    assert index.polygon_count > 1000
    paises = set()
    en_tierra = 0
    for row in range(-80, 85, 20):
        for column in range(-170, 175, 20):
            found = index.country_of(float(row), float(column))
            if found is not None:
                paises.add(found.code)
                en_tierra += 1
    assert len(paises) > 20
    assert en_tierra > 30


def test_version_declarada_es_entera():
    with pytest.raises(CountryDataError):
        _build_index({"features": [{"properties": {"name": "x", "code": "X"}}]})


def test_feature_sin_nombre_o_codigo_es_error():
    with pytest.raises(CountryDataError):
        _build_index({"version": 1, "features": [{"properties": {"name": "x"}}]})


def test_geometria_vacia_o_de_tipo_desconocido_se_ignora():
    index = _build_index(
        {
            "version": 3,
            "features": [
                {"properties": {"name": "Nowhere", "code": "NUL"}, "geometry": None},
                {
                    "properties": {"name": "Weird", "code": "WED"},
                    "geometry": {"type": "LineString", "coordinates": []},
                },
                {
                    "properties": {"name": "Real", "code": "REA"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]
                        ],
                    },
                },
            ],
        }
    )
    assert index.version == 3
    assert index.polygon_count == 1
    assert index.country_of(1.0, 1.0) == Country("REA", "Real")
    assert isinstance(index, CountryIndex)


def test_anillo_degradado_se_descarta():
    index = _build_index(
        {
            "version": 1,
            "features": [
                {
                    "properties": {"name": "Sliver", "code": "SLV"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0.0, 0.0], [1.0, 1.0]]],
                    },
                },
                {
                    "properties": {"name": "Real", "code": "REA"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]
                        ],
                    },
                },
            ],
        }
    )
    assert index.polygon_count == 1
    assert index.country_of(0.5, 0.5) == Country("REA", "Real")


def test_un_conjunto_sin_poligonos_utiles_es_error():
    with pytest.raises(CountryDataError):
        _build_index(
            {
                "version": 1,
                "features": [
                    {
                        "properties": {"name": "Sliver", "code": "SLV"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0.0, 0.0], [1.0, 1.0]]],
                        },
                    }
                ],
            }
        )


def test_multipoligono_acepta_todas_sus_partes():
    index = _build_index(
        {
            "version": 1,
            "features": [
                {
                    "properties": {"name": "Duo", "code": "DUO"},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]],
                            [[[10.0, 10.0], [12.0, 10.0], [12.0, 12.0], [10.0, 12.0], [10.0, 10.0]]],
                        ],
                    },
                }
            ],
        }
    )
    assert index.polygon_count == 2
    assert index.country_of(1.0, 1.0) == Country("DUO", "Duo")
    assert index.country_of(11.0, 11.0) == Country("DUO", "Duo")
    assert index.country_of(6.0, 6.0) is None


def test_hueco_excluye_el_punto():
    index = _build_index(
        {
            "version": 1,
            "features": [
                {
                    "properties": {"name": "Donut", "code": "DON"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]],
                            [[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0], [4.0, 4.0]],
                        ],
                    },
                }
            ],
        }
    )
    assert index.country_of(1.0, 1.0) == Country("DON", "Donut")
    assert index.country_of(5.0, 5.0) is None


def test_poligono_que_cruza_el_antimeridiano():
    # Los datos part el anillo en dos tramos a cada lado de 180, no en uno que
    # atraviese de 179 a -179: ese salto de 358 grados describiria el mundo entero
    # menos la franja, que no es lo que se quiere representar.
    index = _build_index(
        {
            "version": 1,
            "features": [
                {
                    "properties": {"name": "Wrap", "code": "WRP"},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [
                                [
                                    [179.0, 10.0],
                                    [180.0, 10.0],
                                    [180.0, 12.0],
                                    [179.0, 12.0],
                                    [179.0, 10.0],
                                ]
                            ],
                            [
                                [
                                    [-180.0, 10.0],
                                    [-179.0, 10.0],
                                    [-179.0, 12.0],
                                    [-180.0, 12.0],
                                    [-180.0, 10.0],
                                ]
                            ],
                        ],
                    },
                }
            ],
        }
    )
    assert index.country_of(11.0, 179.5) == Country("WRP", "Wrap")
    assert index.country_of(11.0, -179.5) == Country("WRP", "Wrap")
    assert index.country_of(11.0, 0.0) is None
    assert index.country_of(15.0, 179.5) is None


def _linear_lookup(index: CountryIndex):
    def lookup(latitude: float, longitude: float):
        from fotos_plus.places import COORDINATE_SCALE

        lon = int(round(longitude * COORDINATE_SCALE))
        lat = int(round(latitude * COORDINATE_SCALE))
        for polygon in index._polygons:
            if polygon.contains(lon, lat):
                return polygon.country
        return None

    return lookup
