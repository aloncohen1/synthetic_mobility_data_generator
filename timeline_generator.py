import pandas as pd
import numpy as np
import logging
from datetime import timedelta
import taxicab as tc

from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import transform, linemerge, nearest_points, snap


class MobilePhone:

    def __init__(self, mobile_id, graph, home_info, work_info, mobile_residence_df, pois_df):

        """
        :param mobile_id: unique str / float/ int identifier of the mobile device
        :param graph: MultiDiGraph objects
        :param home_info: # home info dict
        :param work_info: # work info dict
        :param mobile_residence_df: pandas df of residence locations
        :param pois_df: pandas df of pois locations
        """

        self.G = graph
        self.mobile_id = mobile_id
        self.mobile_type = np.random.choice(['iOS', 'Android'])
        self.home_info = home_info
        self.work_info = work_info
        self.mobile_residence_df = mobile_residence_df
        self.pois_df = pois_df
        self.mobile_timeline = pd.DataFrame()
        self.mobile_routs = {}
        self.mobile_signals = None

    def generate_signals_df(self, start_date, end_date, max_residences=2, max_pois=2):

        """
        function will build signals timeline based on the output of generate_mobile_timeline
        :param start_date: format - YYYY-MM-DD
        :param end_date: format - YYYY-MM-DD
        :param max_residences: max residence locations to be visit in a given day
        :param max_pois: max pois visits in a day
        :return:
        """

        signals_dfs = []

        if self.mobile_timeline.empty:
            self.generate_mobile_timeline(start_date, end_date, max_residences=max_residences, max_pois=max_pois)

        drive_end = None
        # build all routs
        for row in self.mobile_timeline \
                .join(self.mobile_timeline[['lat', 'lng']].shift(-1), lsuffix='_orig', rsuffix='_dest') \
                .dropna(subset=['lat_orig', 'lng_orig', 'lat_dest', 'lng_dest'], how='any').itertuples():

            if not drive_end:
                drive_end = row.start_time

            static_signals = self.generate_static_signals(row.lat_orig, row.lng_orig, drive_end, row.end_time)
            signals_dfs.append(static_signals)

            self.calc_route((row.lat_orig, row.lng_orig), (row.lat_dest, row.lng_dest))
            route_geo = self.mobile_routs.get(((row.lat_orig, row.lng_orig), (row.lat_dest, row.lng_dest)))

            if route_geo != 'no_rout':

                drive_signals, drive_end = self.generate_route_signals(route_geo, row.end_time, 45)
                signals_dfs.append(drive_signals)

            else:
                drive_end = row.end_time

        self.mobile_signals = pd.concat(signals_dfs, ignore_index=True) \
            .sort_values('timestamp')
        self.mobile_signals['mobile_type'] = self.mobile_type
        self.mobile_signals['mobile_id'] = self.mobile_id

        self.mobile_signals = self.mobile_signals.join(self.mobile_signals[['lat', 'lng']].shift(-1), lsuffix='1',
                                                       rsuffix='2')

        return self.mobile_signals

    def calc_route(self, orig, dest):
        """
        will try to get route from mobile_routs. if not exists will calculate using get_route_geometry
        :param orig: lat,lng tuple of origin location
        :param dest: lat,lng tuple of destination location
        :return:
        """
        if not self.mobile_routs.get((orig, dest)):
            try:
                route = tc.distance.shortest_path(self.G, orig, dest)
                route_geo = self.get_route_geometry(route, orig, dest)
                self.mobile_routs[(orig, dest)] = route_geo
                self.mobile_routs[(dest, orig)] = self.reverse_geom(route_geo)
            except Exception as e:
                logging.info(f'faild to create route! {orig} -> {dest} reason: {e}')
                self.mobile_routs[(orig, dest)] = 'no_rout'
                self.mobile_routs[(dest, orig)] = 'no_rout'


    def reverse_geom(self, geom):

        """
        will reverse linestring geometry
        :param geom: linestring object
        :return:
        """
        def _reverse(x, y, z=None):
            if z:
                return x[::-1], y[::-1], z[::-1]
            return x[::-1], y[::-1]

        return transform(_reverse, geom)


    def generate_static_signals(self, lat, lng, start_time, end_time, sampling_rate=600):
        """
        function that returns location and timestamps nearby the selected location
        :param lat: location latitude
        :param lng: location longitude
        :param start_time: stay start time
        :param end_time: stay end time
        :param sampling_rate: time diff between each two signals in seconds
        :return:
        """

        signals_list = []
        signal_time = start_time + timedelta(
            seconds=int(np.random.choice([5, 10, 15])))  # start sample couple of second after stay start

        noise_list = np.linspace(0.9999997, 1.000003)  # noise factor

        while end_time > signal_time:
            signals_list.append({'lat': lat * np.random.choice(noise_list),
                                 'lng': lng * np.random.choice(noise_list),
                                 'timestamp': signal_time})
            signal_time += timedelta(seconds=sampling_rate -
                                             int(np.random.choice(range(0, 59))))

        return pd.DataFrame(signals_list).sort_values('timestamp')


    def generate_route_signals(self, route_geo, start_time, sampling_rate=45, points_per_segment=10):

        """
        function that get route linestring and returns signals with timestamps upon this line
        :param route_geo: linestring object (output of get_route_geometry)
        :param start_time: format YYYY-MM-DD
        :param sampling_rate: time diff between each two signals in seconds
        :param points_per_segment: will signals out of n random points
        :return:
        """

        end_time = start_time + timedelta(minutes=int(np.random.choice(range(15, 50))))

        n_points = round((end_time - start_time).total_seconds() / sampling_rate)

        noise_list = np.linspace(0.9999999, 1.000001)  # add noise to points
        signal_time = start_time - timedelta(seconds=int(np.random.choice([5, 10, 15])))

        timestamps_list = []

        for i in range(0, n_points):
            timestamps_list.append(signal_time)
            signal_time += timedelta(seconds=sampling_rate + int(np.random.choice(range(0, 9))))

        line_to_points = np.array(
            [
                {'lat': y * np.random.choice(noise_list), 'lng': x * np.random.choice(noise_list)}
                for p1, p2 in zip(route_geo.coords, route_geo.coords[1:])  # iterate through line segments
                for x, y in zip(
                np.linspace(p1[0], p2[0], points_per_segment),
                np.linspace(p1[1], p2[1], points_per_segment),
            )
            ])

        indexes = np.sort(np.random.choice(range(0, len(line_to_points)), replace=False,
                                           size=min(n_points, len(line_to_points))))
        random_points = line_to_points[indexes]

        signals_df = pd.DataFrame([i for i in random_points])
        signals_df['timestamp'] = timestamps_list[:len(signals_df)]

        return signals_df, signal_time

    def get_route_geometry(self, route, orig, dest):

        """
        function that get's taxicab shortest_path and returns liststring object
        :param route: route (output of taxicab shortest_path)
        :param orig: lat,lng tuple of origin location
        :param dest: lat,lng tuple of destination location
        :return:
        """

        x, y = [], []
        for u, v in zip(route[tc.constants.BODY][:-1], route[tc.constants.BODY][1:]):
            # if there are parallel edges, select the shortest in length
            data = min(self.G.get_edge_data(u, v).values(), key=lambda d: d["length"])
            if "geometry" in data:
                # if geometry attribute exists, add all its coords to list
                xs, ys = data["geometry"].xy
                x.extend(xs)
                y.extend(ys)
            else:
                # otherwise, the edge is a straight line from node to node
                x.extend((self.G.nodes[u]["x"], self.G.nodes[v]["x"]))
                y.extend((self.G.nodes[u]["y"], self.G.nodes[v]["y"]))

        final_route = []

        if route[2]:

            final_route.append(LineString([Point(orig[1], orig[0]),
                                           nearest_points(Point(orig[1], orig[0]), route[2])[1]]))
            final_route.append(route[2])

        else:
            final_route.append(LineString([Point(orig[1], orig[0]), Point(x[0], y[0])]))

        final_route.append(LineString([Point(lng, lat) for lng, lat in list(zip(x, y))]))

        if route[3]:
            final_route.append(route[3])
            final_route.append(LineString([nearest_points(Point(dest[1], dest[0]), route[3])[1],
                                           Point(dest[1], dest[0])]))

        else:
            final_route.append(LineString([Point(x[-1], y[-1]),
                                           Point(dest[1], dest[0])]))

        final_route_geo = linemerge(final_route)
        if isinstance(final_route_geo, MultiLineString):
            final_route_geo = linemerge([snap(i, j, 0.000001) for i, j in zip(final_route, final_route[1:])])
            if isinstance(final_route_geo, MultiLineString):
                final_route_geo = list(final_route_geo)[
                    np.argmax(np.array([len(i.coords) for i in list(final_route_geo)]))]

        return final_route_geo

    def generate_mobile_timeline(self, start_time, end_time, max_residences, max_pois):

        """
        function that generate the mobile timeline.
        will generate a home, work, residence and pois stays with times intervals

        :param start_time: format - YYYY-MM-DD
        :param end_time: format - YYYY-MM-DD
        :param max_residences: max residence locations to be visit in a given day
        :param max_pois: max pois visits in a day
        :return:
        """

        self.mobile_timeline = []

        stays_counter = 0
        for day in pd.date_range(start_time, end_time):

            n_residences = np.random.choice(range(1, max_residences))
            n_pois = np.random.choice(range(1, max_pois))

            levaing_hour = np.random.choice([6, 7, 8])
            start_time = day
            end_time = day + timedelta(hours=int(levaing_hour))

            self.mobile_timeline.append({'stay_id': stays_counter,
                                         "start_time": start_time,
                                         "end_time": end_time,
                                         'poi_id': 'home',
                                         'poi_name': 'home',
                                         'poi_type': 'home',
                                         'lat': self.home_info['lat'],
                                         'lng': self.home_info['lng']})
            stays_counter += 1

            if day.weekday() not in [5, 6]:  # if working day
                working_hours = np.random.choice([7, 8, 9])
                start_time = end_time
                end_time += timedelta(hours=int(working_hours))

                self.mobile_timeline.append({'stay_id': stays_counter,
                                             "start_time": start_time,
                                             "end_time": end_time,
                                             "poi_id": 'work',
                                             'poi_name': 'work',
                                             'poi_type': 'work',
                                             'lat': self.work_info['lat'],
                                             'lng': self.work_info['lng']})
                stays_counter += 1

            time_left = 24 - end_time.hour
            if n_residences != 0 or n_pois != 0:
                time_left -= 1  # leave 1 hour to stay at home at the end of the timeline
                time_per_stay = np.floor(time_left / (n_residences + n_pois))

                if n_residences != 0:
                    for row in self.mobile_residence_df.sample(n_residences).itertuples():
                        start_time = end_time
                        end_time += timedelta(hours=int(time_per_stay))
                        time_left -= time_per_stay

                        self.mobile_timeline.append({'stay_id': stays_counter,
                                                     "start_time": start_time,
                                                     "end_time": end_time,
                                                     'poi_name': row.Index,
                                                     'poi_type': 'residence',
                                                     'poi_id': row.Index,
                                                     'lat': row.lat,
                                                     'lng': row.lng})
                        stays_counter += 1

                if n_pois != 0:
                    for row in self.pois_df.sample(n_pois).itertuples():
                        start_time = end_time
                        end_time += timedelta(hours=int(time_per_stay))
                        time_left -= time_per_stay

                        self.mobile_timeline.append({'stay_id': stays_counter,
                                                     "start_time": start_time,
                                                     "end_time": end_time,
                                                     'poi_name': row.poi_name,
                                                     'poi_type': 'store',
                                                     'poi_id': row.Index,
                                                     'lat': row.lat,
                                                     'lng': row.lng})
                        stays_counter += 1

            start_time = end_time
            end_time += timedelta(hours=int(time_left))
            self.mobile_timeline.append({'stay_id': stays_counter,
                                         "start_time": start_time,
                                         "end_time": end_time + timedelta(hours=abs(end_time.hour - 24)),
                                         'poi_id': 'home',
                                         'poi_name': 'home',
                                         'poi_type': 'home',
                                         'lat': self.home_info['lat'],
                                         'lng': self.home_info['lng']})
            stays_counter += 1
        self.mobile_timeline = pd.DataFrame(self.mobile_timeline)