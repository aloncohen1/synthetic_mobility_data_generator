import os
import json
import datetime
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.geometry import Point
import logging
from keplergl import KeplerGl

ox.config(use_cache=True, log_console=True)

ARCGIS_REST_URL = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/MSBFP2/FeatureServer/0/query?f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry={"ymax":%s,"ymin":%s,"xmax":%s,"xmin":%s,"spatialReference":{"wkid":4326}}&geometryType=esriGeometryEnvelope&outSR=4326'

US_GEO_CELLS = (
    "bk", "bs", "bu", "b7", "be", "bg", "b6", "bd", "bf", "b3",
    "b9", "bc", "c0", "c1", "c2", "c8", "cb", "f0", "f2", "f8",
    "fb", "9p", "9r", "9x", "9z", "dp", "dr", "dx", "9n", "9q",
    "9w", "9y", "dn", "dq", "9m", "9t", "9v", "9k", "9s", "9u",
    "dj", "dm", "dh", "dk", "8k", "8s", "87", "8e", "b1", "c4",
    "b4"
)


def get_residence_df(bbox):

    """
    get bbox and return pandas df of buildings locations (the query returns maximum of 2000 records)
    :param bbox:
    :return:
    """

    logging.info('query arcgis rest url - START')

    residence_df = gpd.read_file(ARCGIS_REST_URL % bbox)

    residence_df['lat'] = residence_df['geometry'].centroid.y
    residence_df['lng'] = residence_df['geometry'].centroid.x
    residence_df['area'] = residence_df.area

    logging.info('query arcgis rest url - END')

    return residence_df


def export_timeline_viz(signals, timeline, mobile_id, export_path):

    """
    Will generate an kepler.gl html file with mobile device signals and timeline
    :param signals: signals df (locations and timestamp)
    :param timeline: timeline_df locations and times intervals
    :param mobile_id: unique mobile_id
    :param export_path: local path for export
    :return:
    """


    with open('./kepler_config.json') as json_file:

        config = json.load(json_file)

    config['config']['mapState']['latitude'] = signals['lat1'].mean()
    config['config']['mapState']['longitude'] = signals['lng1'].mean()

    signals['timestamp'] = signals['timestamp'].astype(str)

    timeline['start_time'] = timeline['start_time'].astype(str)
    timeline['end_time'] = timeline['end_time'].astype(str)

    kepler_map = KeplerGl(data={"timeline": timeline,
                                "signals": signals},
                          config=config)


    file_name = f'{mobile_id}.html'

    kepler_map.save_to_html(file_name=os.path.join(export_path, file_name))


def get_kaggle_pois_data(kaggle_username, kaggle_key, export_path, bbox=None):

    """
    downloads public pois data from kaggle and return pandas object of pois
    to generate kaggle username and key, see here - https://www.kaggle.com/docs/api
    :param kaggle_username: your kaggle username
    :param kaggle_key: your kaggle key
    :param export_path: path to export the data
    :param bbox: if passed, will filter to pois within bbox only
    :return:
    """

    logging.info('getting pois data from Kaggle - START')

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
    if bbox:
        pois_df = pois_df[pois_df.apply(lambda x: isin_box(x['lat'], x['lng'], bbox), axis=1)]
    pois_df['id'] = pois_df.index
    pois_df['geometry'] = pois_df.apply(lambda x: Point(x['lng'], x['lat']), axis=1)
    pois_df = gpd.GeoDataFrame(pois_df)

    logging.info('getting pois data from Kaggle - END')

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


def get_osmnx_graph(bbox=None, geo_str=None, import_gpickle_path=None, export_path=None):

    """
    will query osm for all roads by bbox or geo_str and return MultiDiGraph object
    :param bbox: bounding box to query
    :param geo_str: name of the are, for example - "Rhode Island",'Massachusetts'
    :param import_gpickle_path: if passed, will load gpickle
    :param export_path: local path to export G pickle
    :return:
    """

    assert bbox or import_gpickle_path, "function massed receive bbox, geo_str import_gpickle_path"

    assert not (bbox and geo_str) or (bbox and import_gpickle_path) or (geo_str, import_gpickle_path), "please pass only one param of 'bbox' ,'geo_str', 'import_gpickle_path'"

    G = None

    if bbox:
        G = ox.graph_from_bbox(*bbox, network_type="drive", retain_all=True, truncate_by_edge=True)

    elif geo_str:
        G = ox.graph_from_place(geo_str, network_type="drive", retain_all=True, truncate_by_edge=True)

    elif import_gpickle_path:
        G = nx.read_gpickle(import_gpickle_path)


    G = ox.speed.add_edge_speeds(G)
    G = ox.speed.add_edge_travel_times(G)


    if export_path:
        file_name = datetime.datetime.now().isoformat() + '_G.gpickle'
        nx.write_gpickle(G, os.path.join(export_path, file_name))

    return G

