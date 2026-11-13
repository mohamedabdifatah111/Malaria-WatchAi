"""5 km equal-area prediction grid (Africa Albers Equal Area, ESRI:102022).

A cell belongs to the grid when its centre falls inside a study country.
Each cell gets ADM0/ADM1/ADM2 ids by centre-in-polygon; cells whose centre
falls in a gap between ADM1/ADM2 layers take the nearest labelled cell in the
same country.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from affine import Affine
from pyproj import Transformer
from rasterio.features import rasterize
from scipy import ndimage

from ml.src import config
from ml.src.data import boundaries


@dataclass(frozen=True)
class GridSpec:
    transform: Affine
    width: int
    height: int
    crs: str
    res: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width

    def rowcol(self, x, y) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        col = np.floor((x - self.transform.c) / self.res).astype(int)
        row = np.floor((self.transform.f - y) / self.res).astype(int)
        return row, col

    def inside(self, row, col) -> np.ndarray:
        return (row >= 0) & (row < self.height) & (col >= 0) & (col < self.width)

    def to_dict(self) -> dict:
        return {"transform": list(self.transform)[:6], "width": self.width, "height": self.height,
                "crs": self.crs, "res": self.res}


def make_spec() -> GridSpec:
    res = config.grid_resolution_m()
    adm0 = boundaries.level("ADM0").to_crs(config.crs_area())
    xmin, ymin, xmax, ymax = adm0.total_bounds
    xmin = np.floor(xmin / res) * res
    ymin = np.floor(ymin / res) * res
    xmax = np.ceil(xmax / res) * res
    ymax = np.ceil(ymax / res) * res
    w = int(round((xmax - xmin) / res))
    h = int(round((ymax - ymin) / res))
    return GridSpec(Affine(res, 0.0, xmin, 0.0, -res, ymax), w, h, config.crs_area(), res)


def _label(level: str, spec: GridSpec) -> tuple[np.ndarray, pd.DataFrame]:
    g = boundaries.level(level).to_crs(spec.crs).reset_index(drop=True)
    arr = rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)), out_shape=spec.shape,
                    transform=spec.transform, fill=0, dtype="int32")
    return arr, g


def _fill_from_nearest(lab: np.ndarray, valid: np.ndarray) -> np.ndarray:
    missing = valid & (lab == 0)
    if not missing.any():
        return lab
    _, (ri, ci) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
    out = lab.copy()
    out[missing] = lab[ri[missing], ci[missing]]
    return out


def build_grid(spec: GridSpec | None = None) -> tuple[pd.DataFrame, GridSpec]:
    spec = spec or make_spec()
    a0, g0 = _label("ADM0", spec)
    valid = a0 > 0
    a1, g1 = _label("ADM1", spec)
    a2, g2 = _label("ADM2", spec)
    a1 = _fill_from_nearest(a1, valid)
    a2 = _fill_from_nearest(a2, valid)
    rows, cols = np.nonzero(valid)
    x = spec.transform.c + (cols + 0.5) * spec.res
    y = spec.transform.f - (rows + 0.5) * spec.res
    lon, lat = Transformer.from_crs(spec.crs, "EPSG:4326", always_xy=True).transform(x, y)

    def ids(arr, g, col):
        idx = arr[rows, cols]
        vals = np.where(idx > 0, g[col].to_numpy()[np.maximum(idx - 1, 0)], None)
        return vals

    df = pd.DataFrame({
        "cell_id": (rows.astype(np.int64) * spec.width + cols).astype(np.int64),
        "row": rows, "col": cols, "x": x, "y": y, "lon": lon, "lat": lat,
        "country": ids(a0, g0, "country"),
        "adm0_id": ids(a0, g0, "region_id"),
        "adm1_id": ids(a1, g1, "region_id"),
        "adm2_id": ids(a2, g2, "region_id"),
    })
    # A nearest-fill must not borrow a label from a neighbouring country.
    rt = boundaries.region_table().set_index("region_id")["country"]
    for c in ("adm1_id", "adm2_id"):
        wrong = df[c].map(rt) != df["country"]
        df.loc[wrong, c] = None
    return df, spec


def cell_polygons(df: pd.DataFrame, spec: GridSpec):
    """Square cell polygons in EPSG:4326 for map display."""
    import geopandas as gpd
    from shapely import box

    h = spec.res / 2
    geoms = box(df["x"] - h, df["y"] - h, df["x"] + h, df["y"] + h)
    return gpd.GeoSeries(geoms, crs=spec.crs).to_crs("EPSG:4326")
