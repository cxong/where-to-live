import logging
from dataclasses import dataclass
from math import radians, sin, cos, atan2, sqrt

import dateutil
import googlemaps
import pandas as pd
from munch import munchify, Munch


@dataclass
class LatLong:
    lat: float
    long: float

    @classmethod
    def from_g(cls, g: Munch):
        return cls(g.lat, g.lng)

    @classmethod
    def from_suburb(cls, suburb: pd.Series):
        return cls(suburb.lat, suburb.lon)

    @property
    def tuple(self):
        return self.lat, self.long


def find_locales_inside(gmaps: googlemaps.Client, au_suburbs: pd.DataFrame, address: str):
    target = munchify(gmaps.geocode(address)[0])
    bounds = target.geometry.bounds
    return au_suburbs.loc[
        (au_suburbs.lat >= bounds.southwest.lat) &
        (au_suburbs.lat <= bounds.northeast.lat) &
        (au_suburbs.lon >= bounds.southwest.lng) &
        (au_suburbs.lon <= bounds.northeast.lng)
    ]


# approximate radius of earth in km
R = 6373.0


def distance_km(p1: LatLong, p2: LatLong):
    """
    https://stackoverflow.com/a/19412565/2038264
    """
    lat1 = radians(p1.lat)
    lon1 = radians(p1.long)
    lat2 = radians(p2.lat)
    lon2 = radians(p2.long)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


class GSuburbFinder:
    # https://developers.google.com/maps/documentation/distance-matrix/usage-and-billing
    MAX_ORIGINS_DESTS = 25

    def __init__(self, gm_key: str):
        self._gmaps = googlemaps.Client(key=gm_key)
        self.suburbs = self._load_au_suburbs()

    def apply_filter(self, label: str, f: Munch) -> pd.DataFrame:
        coords = LatLong.from_g(munchify(self._gmaps.geocode(f.address)[0]).geometry.location)

        self.suburbs = self._filter_distance(label, f, coords)
        self.suburbs = self._filter_commute(label, f, coords)

        return self.suburbs

    def _filter_distance(self, label: str, f: Munch, coords: LatLong):
        if "distance_km" in f:
            self.suburbs[f"{label}_distance"] = self.suburbs.apply(
                lambda x: distance_km(coords, LatLong.from_suburb(x)),
                axis=1
            )
            self.suburbs = self.suburbs.loc[
                (self.suburbs[f"{label}_distance"] >= f.distance_km[0]) &
                (self.suburbs[f"{label}_distance"] <= f.distance_km[1])
            ]
        return self.suburbs

    def _filter_commute(self, label: str, f: Munch, coords: LatLong):
        if "commute" in f:
            arrival_time = dateutil.parser.parse(f.commute.arrival_time) if "arrival_time" in f.commute else None
            for mode_name, mode in f.commute.modes.items():
                suburbs = list(zip(self.suburbs.lat, self.suburbs.lon))
                transit_mode = None
                if mode_name.startswith("transit:"):
                    mode_name, transit_mode = mode_name.split(":")
                results = []
                for suburbs_chunked in chunk(suburbs, self.MAX_ORIGINS_DESTS - 1):
                    if f.commute.is_origin:
                        origins = suburbs_chunked
                        destinations = coords.tuple
                    else:
                        origins = coords.tuple
                        destinations = suburbs_chunked
                    # https://github.com/googlemaps/google-maps-services-python/blob/master/googlemaps/distance_matrix.py
                    result = googlemaps.distance_matrix.distance_matrix(
                        self._gmaps,
                        origins,
                        destinations,
                        mode=mode_name,
                        avoid=mode.get("avoid"),
                        # TODO: departure time
                        arrival_time=arrival_time,
                        transit_mode=transit_mode,
                        transit_routing_preference=mode.get("transit_routing_preference")
                    )
                    if f.commute.is_origin:
                        results += [row["elements"][0] for row in result['rows']]
                    else:
                        results += result['rows'][0]['elements']
                results_df = pd.DataFrame([{
                    "distance_m": row["distance"]["value"],
                    "duration_s": row["duration"]["value"]
                } for row in results])
                mode_label = transit_mode or mode_name
                if len(self.suburbs) != len(results_df):
                    logging.error("Cannot find valid commute results for %s (%s:%s)", label, mode_name, transit_mode)
                    continue
                self.suburbs[f"{label}_{mode_label}_distance_km"] = results_df.distance_m.values / 1000
                self.suburbs[f"{label}_{mode_label}_duration_mins"] = results_df.duration_s.values / 60

                # filter
                self.suburbs = self.suburbs.loc[
                    (self.suburbs[f"{label}_{mode_label}_duration_mins"] >= mode.minutes[0]) &
                    (self.suburbs[f"{label}_{mode_label}_duration_mins"] <= mode.minutes[1])
                ]
                if len(self.suburbs) == 0:
                    break
        return self.suburbs

    @staticmethod
    def _load_au_suburbs() -> pd.DataFrame:
        df = pd.read_csv("Australian_Post_Codes_Lat_Lon.csv", converters={"type": lambda x: x.strip()})
        # Sanitise
        df = df.loc[df.type == "Delivery Area"]
        del df["type"]
        del df["dc"]
        return df


# https://stackoverflow.com/a/312464/2038264
def chunk(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
