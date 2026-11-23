import pytest

from peat_mos.pmtiles import _tile_coordinate


@pytest.mark.parametrize(
    ("z", "x", "y", "expected"),
    [
        pytest.param(0, 0, 0, True, id="only_tile_at_zoom_zero"),
        pytest.param(-1, 0, 0, False, id="negative_zoom_is_invalid"),
        pytest.param(1, 0, 0, True, id="top_left_corner_valid"),
        pytest.param(1, 1, 1, True, id="bottom_right_corner_valid"),
        pytest.param(1, 2, 0, False, id="x_at_tiles_per_dimension_is_invalid"),
        pytest.param(1, 0, 2, False, id="y_at_tiles_per_dimension_is_invalid"),
        pytest.param(1, -1, 0, False, id="negative_x_is_invalid"),
        pytest.param(1, 0, -1, False, id="negative_y_is_invalid"),
        pytest.param(10, 1023, 1023, True, id="far_corner_at_higher_zoom_valid"),
        pytest.param(10, 1024, 0, False, id="x_just_past_bound_at_higher_zoom"),
    ],
)
def test_is_valid_tile_coordinate(z: int, x: int, y: int, expected: bool) -> None:
    assert _tile_coordinate.is_valid_tile_coordinate(z, x, y) == expected


@pytest.mark.parametrize(
    ("z", "x", "y", "expected"),
    [
        # reference values from the PMTiles v3 spec
        pytest.param(0, 0, 0, 0, id="root_tile"),
        pytest.param(1, 0, 0, 1, id="zoom_one_first_tile"),
        pytest.param(1, 0, 1, 2, id="zoom_one_second_tile"),
        pytest.param(1, 1, 1, 3, id="zoom_one_third_tile"),
        pytest.param(1, 1, 0, 4, id="zoom_one_last_tile"),
        pytest.param(2, 0, 0, 5, id="zoom_two_first_tile_follows_zoom_one_range"),
    ],
)
def test_tile_coordinate_to_tile_id(z: int, x: int, y: int, expected: int) -> None:
    assert _tile_coordinate.tile_coordinate_to_tile_id(z, x, y) == expected
