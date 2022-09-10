import osmnx as ox
import os

from geo_utils import get_anchors_df, get_kaggle_pois_data, get_osmnx_graph
from timeline_generator import Device


def main(lat, lng, radius, n_devices, start_time, end_time, export_path, kaggle_username, kaggle_key, graph=None):

    """
    will generate signals timelines for n devices
    :param lat: latitude of the synthetic timeline location
    :param lng: longitude of the synthetic timeline location
    :param radius: radius in meters
    :param n_devices: # of devices with synthetic timeline to generate
    :param start_time: timeline start time - YYYY-MM-DD
    :param end_time: timeline end time - YYYY-MM-DD
    :param export_path: export path to save output data
    :param kaggle_username:
    :param kaggle_key:
    :param graph:
    :return:
    """

    os.system(f'mkdir {export_path}/timelines')
    os.system(f'mkdir {export_path}/signals')

    bbox = ox.utils_geo.bbox_from_point((lat, lng), radius)
    anchors_df = get_anchors_df(bbox)
    pois_df = get_kaggle_pois_data(kaggle_username, kaggle_key, export_path, bbox=bbox)

    if not graph:
        graph = get_osmnx_graph(bbox)

    for i in range(0, n_devices):

      home_info = anchors_df.sample(1).to_dict(orient='records')[0] # pick random home location
      work_info = pois_df.sample(1).to_dict(orient='records')[0] # pick random work location

      device_anchors_df = anchors_df[anchors_df['BlockgroupID']!=home_info['BlockgroupID']].sample(10) # pick 10 anchors from other block groups

      device = Device(i ,graph, home_info, work_info, device_anchors_df, pois_df) # initiate device object
      signals = device.generate_signals_df(start_time, end_time) # generate signals timeline
      signals.to_csv(os.path.join(f'{export_path}/signals', f'{i}.csv'),index=False)
      device.device_timeline.to_csv(os.path.join(f'{export_path}/timelines', f'{i}.csv'),index=False)
      print(f'done with device {i}')