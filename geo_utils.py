import matplotlib.pyplot as plt
import os
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
from shapely.ops import transform, linemerge, nearest_points