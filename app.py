import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import pandas as pd
import numpy as np
import plotly.express as px
from urllib.request import urlopen
import json
import merge_counties
import plotly.graph_objects as go

## get New York counties
with urlopen(r'https://raw.githubusercontent.com/rstudio/leaflet/master/docs/json/nycounties.geojson') as ny_response:
    ny_counties = json.load(ny_response)

## merge 5 nyc boroughs into 1
ny_counties = merge_counties.merge_counties()

## get all other usa counties for future
# with urlopen(r'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
#     counties = json.load(response)


# get basic census data (population)
census_json_url = 'https://raw.githubusercontent.com/Zoooook/CoronavirusTimelapse/master/static/population.json'
df_census = pd.read_json(
    census_json_url,
    dtype={"us_county_fips": str})
df_census = df_census.rename(columns={'us_county_fips': 'fips'})
df_census['state_county'] = df_census['region'] + '_' + df_census['subregion']

## get covid-19 data
df = pd.read_csv(r'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
                 dtype={"fips": str})
df['state_county'] = df['state'] + '_' + df['county']
df = df.sort_values(by=['date'])

## join census data with corona data on state + county name
main_df = pd.merge(df, df_census, on='state_county', how='left')
main_df['fips'] = main_df['fips_y']
main_df = main_df.drop(columns=['fips_x', 'fips_y', 'state_county',
                                'us_state_fips', 'region', 'subregion', 'nyt_population'])

## aggregate days into weeks and week count of the year
main_df['new_date'] = pd.to_datetime(main_df['date'])
main_df['Year-Week'] = main_df['new_date'].dt.strftime('%Y-%U')

#power_of = 1 / 100

main_df['% cases of total population'] = (main_df['cases'] / main_df['population']) #** power_of
main_df['% deaths of total population'] = (main_df['deaths'] / main_df['population'])# ** power_of

main_df['deaths_log'] = np.where(np.log(main_df.deaths) == np.inf, 0,
                                 np.where(np.log(main_df.deaths) == -np.inf, 0, np.log(main_df.deaths)))
main_df['cases_log'] = np.where(np.log(main_df.cases) == np.inf, 0,
                                np.where(np.log(main_df.cases) == -np.inf, 0, np.log(main_df.cases)))

main_df = main_df.sort_values(by=['Year-Week'])

## create New York dataframe
main_df_ny = main_df[main_df['state'] == 'New York'].reset_index(drop=True)

cases_log = 'cases_log'
deaths_log = 'deaths_log'

print(main_df_ny.columns)

options_dict = [{'label': 'Cases', 'value': 'cases_log'},
                {'label': 'Deaths', 'value': 'deaths_log'},
                {'label': '% Cases of Total Population', 'value': '% cases of total population'},
                {'label': '% Deaths of Total Population', 'value': '% deaths of total population'}]


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

    html.Br(),

    dcc.Dropdown(id='data_selector',
                 options=options_dict,
                 multi=False,
                 value='cases_log'
                 ),

    html.Div(id='output_container', children=[]),
    html.Br(),

    html.Div([
        html.Div([
            dcc.Graph(
                id='map',
                config={'displayModeBar': False}
           )
        ], className='six columns'),

    ], className='row'),

])


@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='data_selector', component_property='value')]
)


def update_fig(selected_dropdown_value):

    df = main_df_ny

    fig = px.choropleth(df,
                        geojson=ny_counties,
                        locations="fips",
                        featureidkey="properties.id",
                        color=selected_dropdown_value,
                        color_continuous_scale='Reds',
                        hover_name="county",
                        hover_data=['deaths', 'cases', 'population'],
                        range_color=[0, max(df[selected_dropdown_value])],
                        scope='usa',
                        animation_frame="Year-Week"
                        )



    fig["layout"].pop("updatemenus")
    fig.update_geos(fitbounds="locations", visible=False)
    #fig.update_layout(coloraxis_colorbar=dict(title='Deaths', tickprefix='1.e'))


    return fig

if __name__ == '__main__':
    app.run_server(debug=True)