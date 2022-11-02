import osmnx as ox
import os
import logging
import fire
from geolib import geohash

import warnings

from utils import get_residence_df, get_kaggle_pois_data, get_osmnx_graph, export_timeline_viz, US_GEO_CELLS
from timeline_generator import MobilePhone


def main(lat, lng, radius, n_mobiles, start_date, end_date, export_path, kaggle_username, kaggle_key, graph=None, viz_timeline=False):

    """
    will generate signals timelines for n mobile devices (supports US only)
    :param lat: latitude of the synthetic timeline location
    :param lng: longitude of the synthetic timeline location
    :param radius: radius in meters
    :param n_mobiles: # of mobile devices with synthetic timeline to generate
    :param start_date: timeline start time - YYYY-MM-DD
    :param end_date: timeline end time - YYYY-MM-DD
    :param export_path: export path to save output data
    :param kaggle_username: your kaggle username
    :param kaggle_key: your kaggle key
    :param graph: MultiDiGraph object
    :param viz_timeline: if True, will export Kepler with mobile_phone timeline
    :return:
    """

    assert geohash.encode(lat, lng,2) in US_GEO_CELLS, f"function supports US only, {lat,lng} is out bounds"

    os.system(f'mkdir {export_path}/timelines')
    os.system(f'mkdir {export_path}/signals')
    if viz_timeline:
        os.system(f'mkdir {export_path}/viz')

    bbox = ox.utils_geo.bbox_from_point((lat, lng), radius)
    residence_df = get_residence_df(bbox)
    pois_df = get_kaggle_pois_data(kaggle_username, kaggle_key, export_path, bbox=bbox)

    if not graph:
        graph = get_osmnx_graph(bbox)

    for i in range(0, n_mobiles):

      home_info = residence_df.sample(1).to_dict(orient='records')[0] # pick random home location
      work_info = pois_df.sample(1).to_dict(orient='records')[0] # pick random work location

      mobile_residence_df = residence_df[residence_df['BlockgroupID']!=home_info['BlockgroupID']].sample(10) # pick 10 buildings from other block groups

      mobile_phone = MobilePhone(i, graph, home_info, work_info, mobile_residence_df, pois_df) # initiate CellPhone object

      signals = mobile_phone.generate_signals_df(start_date, end_date) # generate signals timeline
      signals.to_csv(os.path.join(f'{export_path}/signals', f'signals_{i}.csv'),index=False) # save signals data

      timeline = mobile_phone.mobile_timeline
      timeline.to_csv(os.path.join(f'{export_path}/timelines', f'timeline_{i}.csv'),index=False) # save timeline data

      if viz_timeline:
          export_timeline_viz(signals, timeline, i , export_path)

      logging.info(f'done generating mobile_phone {i} signals')



if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    warnings.filterwarnings('ignore')

    fire.Fire(main)
