import os

import googlemaps
from datetime import datetime


def main(gm_key: str):
    gmaps = googlemaps.Client(key=gm_key)

    # Geocoding an address
    geocode_result = gmaps.geocode('1600 Amphitheatre Parkway, Mountain View, CA')
    print(geocode_result)

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


if __name__ == "__main__":
    main(os.environ['GOOGLE_MAPS_KEY'])
