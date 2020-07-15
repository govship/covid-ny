from urllib.request import urlopen
from shapely.geometry import asShape
from shapely.ops import unary_union
from geojson import Feature
import json

def merge_counties():
    with urlopen(
            r'https://raw.githubusercontent.com/rstudio/leaflet/master/docs/json/nycounties.geojson') as ny_response:
        ny_counties = json.load(ny_response)

    indices = [56, 58, 59, 60, 61]
    nyc_polygons = [asShape(ny_counties['features'][i]['geometry']) for i in indices]

    # get the metadata for the first county
    properties = ny_counties['features'][indices[0]]['properties']
    properties['county'] = 'New York City'
    properties['id'] = 36998
    properties['pop'] = 8443713

    # get the union of the polygons
    joined = unary_union(nyc_polygons)

    # delete the merged counties
    counties_ny = ny_counties
    for i in reversed(sorted(indices)):
        del counties_ny['features'][i]

    # add the new polygon to the features
    feature = Feature(geometry=joined, properties=properties)
    counties_ny['features'].append(feature)

    ny_counties = []
    for i in range(len(counties_ny['features'])):
        current_county = counties_ny['features'][i]['properties']['county']
        county_dict = {'label': current_county, 'value': current_county}
        ny_counties.append(county_dict)

    ny_counties = sorted(ny_counties, key=lambda k: k['label'])
    ny_counties_list = []
    for i in range(len(ny_counties)):
        ny_counties_list.append(ny_counties[i]['value'])

    return counties_ny