import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import pandas as pd
import numpy as np
import plotly.express as px
from urllib.request import urlopen
import json
from shapely.geometry import asShape
from shapely.ops import unary_union
from geojson import Feature

with urlopen(r'https://raw.githubusercontent.com/rstudio/leaflet/master/docs/json/nycounties.geojson') as ny_response:
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

app = dash.Dash(
    __name__,
    external_stylesheets=[
        'https://codepen.io/chriddyp/pen/bWLwgP.css'
    ]
)

app.layout = html.Div([
    # html.Div([
    #     dcc.Input(id='covid_input', value='New York', type='text')
    # ]),

    html.Div([
        html.H1('COVID-19 NY'),
        html.Img(src='/assets/covid_logo.png')
    ], className='banner'),

    html.Div(
        dcc.Dropdown(
            options=ny_counties
        )
    ),

    html.Div([
        html.Div([
            dcc.Graph(
                id='cases'
           )
        ], className='six columns'),

    ], className='row'),

])

# app.css.append_css({
#     'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
# })

@app.callback(dash.dependencies.Output('cases', 'figure'),
              [dash.dependencies.Input('covid_input', 'value')]
              )

def update_fig():
    with urlopen(r'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
        counties = json.load(response)

    df_census = pd.read_json(
        'https://raw.githubusercontent.com/Zoooook/CoronavirusTimelapse/master/static/population.json',
        dtype={"us_county_fips": str})
    df_census = df_census.rename(columns={'us_county_fips': 'fips'})
    df_census['state_county'] = df_census['region'] + '_' + df_census['subregion']
    df = pd.read_csv(r'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
                     dtype={"fips": str})
    df['state_county'] = df['state'] + '_' + df['county']
    df = df.sort_values(by=['date'])
    df_ny = df[df['county'] == 'Nassau']

    with urlopen(r'https://raw.githubusercontent.com/rstudio/leaflet/master/docs/json/nycounties.geojson') as ny_response:
        ny_counties = json.load(ny_response)

    main_df = pd.merge(df, df_census, on='state_county', how='left')
    main_df = main_df.drop(columns=['fips_x', 'state_county', 'us_state_fips', 'region', 'subregion', 'nyt_population'])
    main_df['new_date'] = pd.to_datetime(main_df['date'])
    main_df['Year-Week'] = main_df['new_date'].dt.strftime('%Y-%U')

    #power_of = 1 / 100

    main_df['% cases of total population'] = (main_df['cases'] / main_df['population']) #** power_of
    main_df['% deaths of total population'] = (main_df['deaths'] / main_df['population'])# ** power_of

    main_df['deaths_log'] = np.where(np.log2(main_df.deaths) == np.inf, 0,
                                     np.where(np.log2(main_df.deaths) == -np.inf, 0, np.log2(main_df.deaths)))
    main_df['cases_log'] = np.where(np.log2(main_df.cases) == np.inf, 0,
                                    np.where(np.log2(main_df.cases) == -np.inf, 0, np.log2(main_df.cases)))
    main_df['% population cases_log'] = np.where(np.log2(main_df.cases) == np.inf, 0,
                                                 np.where(np.log2(main_df.cases) == -np.inf, 0, np.log2(main_df.cases)))
    # df_us_week['deaths_log'] = np.log(df_us_week['deaths'])
    # df_us_week[df_us_week['county']=='Nassau'][df_us_week['date']=='2020-05-18']['deaths_log']
    main_df = main_df.sort_values(by=['Year-Week'])
    main_df[main_df['county'] == 'New York City']
    main_df_ny = main_df[main_df['state'] == 'New York']

    cases_log = 'cases_log'
    deaths_log = 'deaths_log'

    data_cases = []

    fig_cases = px.choropleth(main_df_ny,
                              geojson=ny_counties,
                              locations="fips_y",
                              featureidkey="properties.id",
                              color=cases_log,
                              color_continuous_scale='Reds',
                              hover_name="county",
                              hover_data=['deaths', 'cases', 'population'],
                              range_color=[0, max(main_df_ny['cases'])],
                              scope='usa',
                              animation_frame="Year-Week"
                              )
    fig_cases["layout"].pop("updatemenus")
    fig_cases.update_geos(fitbounds="locations", visible=False)
    # fig.update_layout(coloraxis_colorbar=dict(title='Deaths', tickprefix='1.e'))

    return fig_cases

if __name__ == '__main__':
    app.run_server(debug=True)