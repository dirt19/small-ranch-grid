#****************************************************************************
#
#         designer:  Joseph.P.Kelly
#             Date:  16-October-2020
#
#****************************************************************************
# NAME          : ***********************************************************
#                 GeoPandas
# DESCRIPTION   : ***********************************************************
#                 WGS84 == EPSG:4326,  World Geodetic System (WGS)
#                 of 1984 is the geographic coordinate reference
#                 system based on European Petroleum Survey Group
#                 (EPSG) 4326 coordinate reference system.
#                 EPSG:4326 (WGS84) measures in degrees
#                 EPSG:2773 (NAD83) measures in 0.1 m
#
# REQUIREMENTS  : ***********************************************************
#
# CODE REFERENCE: ***********************************************************
#
# NOTES         : ***********************************************************
#
################################################################################

import os
import shutil
import fiona
import geopandas as gpd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from zipfile import ZipFile
from shapely.geometry import Polygon,Point
import contextily as ctx


def identify_gdf(gdf):
    """Print some identifying characteristics of the GeoPandas dataframe.

    Args:
        gdf (geopandas dataframe): Pandas dataframe with geopandas seasoning.
    """
    xmin,ymin,xmax,ymax = gdf.total_bounds
    print(f"Dataset CRS    : ", gdf.crs)
    print("Dataset Size    : ", gdf.shape)
    print(f"Dataset Lon-Max: {ymax}\t\tLat-Max: {xmax}\nDataset Lon-Min: {ymin}\t\tLat-Min: {xmin}")
    print("Dataset Head: \n", gdf.head())
    print("\n")


# get_ctx_providers(ctx.providers)
providers = {}
def get_ctx_providers(provider):
    """Retrieves url to reference the contextilly basemap provider
    and populates the providers dictionary

    Args:
        provider (ctx.provider): contextilly basemap provider service
    """
    # Selection:
    if "url" in provider:
        providers[provider['name']] = provider
    else:
        for prov in provider.values():
            get_ctx_providers(prov)


def get_kml_from_kmz(kmz_file, kml_dir=""):
    """[summary]

    Args:
        kmz_file (string): path to KMZ file
        kml_dir (str, optional): path to directory where KML resides or will be written. Defaults to "".

    Returns:
        string: path to KML file
    """
    # https://gis.stackexchange.com/a/291950
    print("get_kml_from_kmz...")
    kml_file_name = 'doc.kml'
    if os.path.exists(kml_file_name):
        os.remove(kml_file_name)
    if os.path.exists(kml_dir):
        shutil.rmtree(kml_dir, ignore_errors=True)
    kmz = ZipFile(kmz_file, 'r')
    kmz.extract(kml_file_name, kml_dir)
    return os.path.join(kml_dir, kml_file_name)


def get_geo_dataframe(kml_file):
    """Reads in KML file and generates a geopandas dataframe

    Args:
        kml_file (string): path to KML file

    Returns:
        geopandas dataframe: Pandas dataframe with geopandas seasoning
    """
    # https://gis.stackexchange.com/a/328554
    print(f"get_geo_dataframe... {kml_file}...")
    gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'r'
    gdf = gpd.GeoDataFrame()
    for layer in fiona.listlayers(kml_file):
        s = gpd.read_file(kml_file, driver='KML', layer=layer)
        gdf = gdf.append(s, ignore_index=True)
    return gdf


def generate_grid(gdf):
    """Provided a geopandas dataframe of polygonal shape, generate a grid overlay

    Args:
        gdf (geopandas dataframe): Pandas dataframe with geopandas seasoning

    Returns:
        geopandas dataframe: grid geopandas dataframe from originally provided gdf
    """
    # https://gis.stackexchange.com/a/316460
    # https://gis.stackexchange.com/a/291117
    # http://epsg.io/2773 # EPSG:2773 NAD83(HARN) / Colorado Central
    print("generate grid...")
    ref_crs = gdf.crs
    meters_gdf = gdf.to_crs('epsg:2773')
    xmin,ymin,xmax,ymax = meters_gdf.total_bounds
    meters_on_side_of_acre = 64   #  appr. sqrt(4,046.8564 m^2)
    int_xmin = int(np.floor(xmin))
    int_ymin = int(np.floor(ymin))
    int_xmax = int(np.floor(xmax))
    int_ymax = int(np.floor(ymax))

    cols = list(range(int_xmin, int_xmax, meters_on_side_of_acre))
    rows = list(range(int_ymin, int_ymax, meters_on_side_of_acre))
    rows.reverse()

    polygons = []
    for x in cols:
        for y in rows:
            polygons.append(
                Polygon([
                    (x,y),
                    (x+meters_on_side_of_acre, y),
                    (x+meters_on_side_of_acre, y-meters_on_side_of_acre),
                    (x, y-meters_on_side_of_acre)
                ])
            )

    #TODO: Truncate to within original shape?

    grid_gdf = gpd.GeoDataFrame({'geometry':polygons})
    grid_gdf.crs = 'epsg:2773'

    grid_gdf = grid_gdf.to_crs(ref_crs)
    return grid_gdf


def plot_geo_dataframe(geodf, grid_gdf=None):
    """Provided a geopandas dataframe, plot it with a basemap. If grid gdf is present, plot that too

    Args:
        geodf (geopandas dataframe): basic gdf to generate plot with
        grid_gdf (geopandas dataframe, optional): grid, or secondary gdf to plot with first. Defaults to None.
    """
    # https://stackoverflow.com/a/58110049/604456
    print("plot geo dataframe...")

    # Selection : Esri.WorldImagery, OpenTopoMap
    basemap_source = ctx.providers.Esri.WorldImagery
    output_file_name = f"{basemap_source.name}.jpg"

    ax = grid_gdf.plot(
                facecolor="none",
                linewidth=1,
                figsize=(28,14),
                edgecolor='Red',
                alpha=0.5
                )
    geodf.plot(ax=ax,
                color='Green',
                linewidth=2,
                figsize=(28,14),
                edgecolor='Red'
                )
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    ax.set(title="Some Title Here")

    if "Topo" in basemap_source.name:
        #Add north arrow
        x, y, arrow_length = 0.98, 0.10, 0.07
        ax.annotate('N',
                    xy=(x, y),
                    xytext=(x, y-arrow_length),
                    arrowprops=dict(facecolor='black', width=5, headwidth=15),
                    ha='center',
                    va='center',
                    fontsize=20,
                    xycoords=ax.transAxes)

    #Add scale-bar
    # https://stackoverflow.com/questions/32333870/how-can-i-show-a-km-ruler-on-a-cartopy-matplotlib-plot/63494503#63494503
    # x, y, scale_len = 0.20, 0.10, 0.14
    # scale_rect = matplotlib.patches.Rectangle(
    #                     (x,y),
    #                     scale_len,
    #                     200,
    #                     linewidth=1,
    #                     edgecolor='k',
    #                     facecolor='k')
    # ax.add_patch(scale_rect)
    # plt.text(x+scale_len/2, y+400, s='100 M', fontsize=15, horizontalalignment='center')

    # Add basemap
    ctx.add_basemap(
                ax,
                crs=geodf.crs.to_string(),
                source=basemap_source
                )

    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(output_file_name, dpi=600)


def main():
    """Primary run function
    """
    # map_source_kmz = "MapSource.kmz"
    # map_source_kml = get_kml_from_kmz(map_source_kmz)
    map_source_kml = "property_lines.kml"
    map_source_gdf = get_geo_dataframe(map_source_kml)
    identify_gdf(map_source_gdf)
    grid_gdf = generate_grid(map_source_gdf)
    plot_geo_dataframe(map_source_gdf, grid_gdf)


if __name__ == '__main__':
    main()
