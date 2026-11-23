from hilbertcurve.hilbertcurve import HilbertCurve  # pyright: ignore[reportMissingTypeStubs]


def is_valid_tile_coordinate(z: int, x: int, y: int) -> bool:
    if z < 0:
        return False
    tiles_per_dimension = 2**z
    return 0 <= x < tiles_per_dimension and 0 <= y < tiles_per_dimension


def tile_coordinate_to_tile_id(z: int, x: int, y: int) -> int:
    if z == 0:
        return 0
    first_tile_id_at_z = (4**z - 1) // 3
    return first_tile_id_at_z + HilbertCurve(z, 2).distance_from_point([x, y])
