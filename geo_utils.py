import matplotlib.pyplot as plt
import os
import json
import datetime
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import timedelta
from functools import partial

import geopandas as gpd
import osmnx as ox
import networkx as nx
import taxicab as tc
import pyproj
from geolib import geohash

from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import transform, linemerge, nearest_points, snap


ARCGIS_REST_URL = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/MSBFP2/FeatureServer/0/query?f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry={"ymax":%s,"ymin":%s,"xmax":%s,"xmin":%s,"spatialReference":{"wkid":4326}}&geometryType=esriGeometryEnvelope&outSR=4326'


def get_buildings_polygons(bbox):

    anchors_polygons = gpd.read_file(ARCGIS_REST_URL % bbox)

    anchors_polygons['lat'] = anchors_polygons['geometry'].centroid.y
    anchors_polygons['lng'] = anchors_polygons['geometry'].centroid.x
    anchors_polygons['area'] = anchors_polygons.area

    return anchors_polygons


def get_kaggle_pois_data(kaggle_username, kaggle_key, export_path, bbox):

    os.system('mkdir ~/.kaggle')
    os.system('touch ~/.kaggle/kaggle.json')
    api_token = {"username": kaggle_username, "key": kaggle_key}

    with open('/root/.kaggle/kaggle.json', 'w') as file:
        json.dump(api_token, file)

    os.system('chmod 600 ~/.kaggle / kaggle.json')
    os.system(f'mkdir /{export_path}/pois_data/')

    os.system(f'kaggle datasets download -d kukuroo3/starbucks-locations-worldwide-2021-version -p /{export_path}/pois_data/starbucks --unzip')
    os.system(f'kaggle datasets download -d jeffreybraun/chipotle-locations/chipotle -p /{export_path}/pois_data/chipotle --unzip')
    os.system(f'kaggle datasets download -d timmofeyy/-pizza-hut-restaurants-locations-in-us -p /{export_path}/pois_data/pizza-hut --unzip')
    os.system(f'kaggle datasets download -d timmofeyy/-walmart-stores-location -p /{export_path}/pois_data/walmart --unzip')
    os.system(f'kaggle datasets download -d appleturnovers/dunkin-locations -p /{export_path}/pois_data/dunkin --unzip')
    os.system(f'kaggle datasets download -d timmofeyy/-subway-locations-in-us -p /{export_path}/pois_data/subway --unzip')
    os.system(f'kaggle datasets download -d saejinmahlauheinert/cava-locations -p /{export_path}/pois_data/cava --unzip')
    os.system(f'kaggle datasets download -d robikscube/foursquare-location-matching-parquet -p /{export_path}/fs --unzip')

    fs_df = pd.read_parquet(f'/{export_path}/fs/pairs.parquet')
    fs_df = fs_df.rename(columns={'name_1': 'poi_name',
                                  'latitude_1': 'lat',
                                  'longitude_1': 'lng', })[['poi_name', 'lat', 'lng']]

    pois_dfs = [fs_df]

    for chain_name in os.listdir('/content/pois_data'):
        chain_file = [i for i in os.listdir(f'/{export_path}/pois_data/{chain_name}') if i.endswith('.csv')][0]
        chain_df = pd.read_csv(os.path.join(f'/{export_path}/pois_data', chain_name, chain_file))
        chain_df['poi_name'] = chain_name
        chain_df = chain_df.rename(columns={'latitude': 'lat',
                                            'longitude': 'lng',
                                            'lon': 'lng',
                                            'loc_lat': 'lat',
                                            'loc_long': 'lng',
                                            'Latitude': 'lat',
                                            'Longitude': 'lng'})[['poi_name', 'lat', 'lng']]

        chain_df['lat'], chain_df['lng'] = chain_df['lat'].astype(float), chain_df['lng'].astype(float)
        pois_dfs.append(chain_df)

    pois_df = pd.concat(pois_dfs, ignore_index=True)
    pois_df = pois_df.dropna(subset=['lat', 'lng'], how='any')
    pois_df = pois_df[pois_df.apply(lambda x: isin_box(x['lat'], x['lng'], bbox), axis=1)]
    pois_df['id'] = pois_df.index
    pois_df['geometry'] = pois_df.apply(lambda x: Point(x['lng'], x['lat']), axis=1)
    pois_df = gpd.GeoDataFrame(pois_df)
    return pois_df


def isin_box(lat, lng, bounds):

    """
    approximate if a location is within a given bounding box
    :param lat: latitude
    :param lng: longitude
    :param bounds: bounding box params
    :return:
    """

    ymax, ymin, xmax, xmin = bounds

    within = False

    if xmin < lng < xmax:
        if ymin < lat < ymax:
            within = True

    return within
