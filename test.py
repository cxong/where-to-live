import os
from dataclasses import dataclass
from math import radians, sin, cos, atan2, sqrt

import click
import googlemaps
import pandas as pd
from datetime import datetime
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
        return cls(suburb["lat"], suburb["lon"])


def load_au_suburbs() -> pd.DataFrame:
    df = pd.read_csv("Australian_Post_Codes_Lat_Lon.csv", converters={"type": lambda x: x.strip()})
    # Sanitise
    df = df.loc[df["type"] == "Delivery Area"]
    del df["type"]
    del df["dc"]
    return df


def find_locales_inside(gmaps: googlemaps.Client, au_suburbs: pd.DataFrame, address: str):
    target = munchify(gmaps.geocode(address)[0])
    bounds = target.geometry.bounds
    return au_suburbs.loc[
        (au_suburbs['lat'] >= bounds.southwest.lat) &
        (au_suburbs['lat'] <= bounds.northeast.lat) &
        (au_suburbs['lon'] >= bounds.southwest.lng) &
        (au_suburbs['lon'] <= bounds.northeast.lng)
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


@click.command()
@click.option("--work", default="200 Barangaroo Avenue, Sydney NSW 2000")
@click.option("--work-max-km", default=10)
@click.option("--work-commute", type=click.DateTime())
def main(work: str, work_max_km: int, work_commute: datetime):
    gm_key = os.environ['GOOGLE_MAPS_KEY']
    gmaps = googlemaps.Client(key=gm_key)
    au_suburbs = load_au_suburbs()

    # Find suburbs in city
    # city_suburbs = find_locales_inside(gmaps, au_suburbs, city)

    work_addr = munchify(gmaps.geocode(work)[0])

    # Filter by distance
    work_suburbs = au_suburbs[au_suburbs.apply(
        lambda x: distance_km(
            LatLong.from_g(work_addr.geometry.location),
            LatLong.from_suburb(x)
        ) < work_max_km,
        axis=1
    )]
    print(work_suburbs)

    # Search public transit

    """
    # Request directions via public transit
    now = datetime.now()
    directions_result = gmaps.directions("Sydney Town Hall",
                                         "Parramatta, NSW",
                                         mode="transit",
                                         departure_time=now)
    print(directions_result)
    """


if __name__ == "__main__":
    main()
