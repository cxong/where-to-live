import os

import googlemaps
import pandas as pd
from datetime import datetime
from munch import munchify


def load_au_suburbs() -> pd.DataFrame:
    df = pd.read_csv("Australian_Post_Codes_Lat_Lon.csv", converters={"type": lambda x: x.strip()})
    # Sanitise
    df = df.loc[df["type"] == "Delivery Area"]
    del df["type"]
    del df["dc"]
    return df


def find_locales_inside(gmaps: googlemaps.Client, au_suburbs: pd.DataFrame, address: str):
    target = munchify(gmaps.geocode(address))
    bounds = target[0].geometry.bounds
    return au_suburbs.loc[
        (au_suburbs['lat'] >= bounds.southwest.lat) &
        (au_suburbs['lat'] <= bounds.northeast.lat) &
        (au_suburbs['lon'] >= bounds.southwest.lng) &
        (au_suburbs['lon'] <= bounds.northeast.lng)
    ]


def main(gm_key: str):
    gmaps = googlemaps.Client(key=gm_key)
    au_suburbs = load_au_suburbs()

    # Find suburbs in city
    suburbs = find_locales_inside(gmaps, au_suburbs, "Sydney NSW Australia")
    print(suburbs)

    """
    # Look up an address with reverse geocoding
    reverse_geocode_result = gmaps.reverse_geocode((40.714224, -73.961452))
    print(reverse_geocode_result)

    # Request directions via public transit
    now = datetime.now()
    directions_result = gmaps.directions("Sydney Town Hall",
                                         "Parramatta, NSW",
                                         mode="transit",
                                         departure_time=now)
    print(directions_result)
    """


if __name__ == "__main__":
    main(os.environ['GOOGLE_MAPS_KEY'])
