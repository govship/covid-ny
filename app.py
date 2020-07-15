import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input
import pandas as pd
import numpy as np
import plotly.express as px
from urllib.request import urlopen
import json
import merge_counties
import visualization_components as vc
from datetime import datetime as dt

## get New York counties
with urlopen(r'https://raw.githubusercontent.com/rstudio/leaflet/master/docs/json/nycounties.geojson') as ny_response:
    ny_counties: dict = json.load(ny_response)

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

main_df['% cases of total population'] = (main_df['cases'] / main_df['population']) * 100 # ** power_of
main_df['% deaths of total cases'] = (main_df['deaths'] / main_df['cases']) * 100 # ** power_of

main_df['deaths_log'] = np.where(np.log(main_df.deaths) == np.inf, 0,
                                 np.where(np.log(main_df.deaths) == -np.inf, 0, np.log(main_df.deaths)))
main_df['cases_log'] = np.where(np.log(main_df.cases) == np.inf, 0,
                                np.where(np.log(main_df.cases) == -np.inf, 0, np.log(main_df.cases)))

## create New York dataframe
main_df_ny = main_df[main_df['state'] == 'New York'].reset_index(drop=True)
main_df_ny = main_df_ny[main_df_ny['county'] != 'Unknown']

case_rate = []
death_rate = []

for county in np.sort(main_df_ny['county'].unique()):
    df_of_county = main_df_ny[main_df_ny['county']==county].sort_values(by='date').reset_index()
    rate_of_cases = df_of_county.cases.pct_change()
    rate_of_deaths = df_of_county.deaths.pct_change()

    case_rate.append(rate_of_cases)
    death_rate.append(rate_of_deaths)

case_rate = np.array(case_rate)
case_rate = np.concatenate(case_rate)
death_rate = np.array(death_rate)
death_rate = np.concatenate(death_rate)

main_df_ny = main_df_ny.sort_values(by=['county', 'date']).reset_index()
main_df_ny['daily_case_rate'] = case_rate
main_df_ny['daily_case_rate'] = main_df_ny['daily_case_rate'].fillna(0)
main_df_ny['daily_case_rate'] = main_df_ny['daily_case_rate'].replace(np.inf, 0)
main_df_ny['daily_death_rate'] = death_rate
main_df_ny['daily_death_rate'] = main_df_ny['daily_death_rate'].fillna(0)
main_df_ny['daily_death_rate'] = main_df_ny['daily_death_rate'].replace(np.inf, 0)

def days_between(d1, d2):
    d1 = dt.strptime(d1, "%Y-%m-%d")
    d2 = dt.strptime(d2, "%Y-%m-%d")
    return (d2 - d1).days


day_of_first_case = min((main_df_ny.date))
main_df_ny['Days Since First Case'] = (main_df_ny.date.apply(lambda x: dt.strptime(x, "%Y-%m-%d")) - dt.strptime(day_of_first_case, "%Y-%m-%d"))

#main_df_ny = main_df_ny.replace(0, 0.00001)
main_df_ny = main_df_ny.drop(columns='index')
main_df_ny = main_df_ny.sort_values(by=['date'])

#print(main_df_ny[['deaths', 'daily_death_rate']].iloc[0:60])

cases_log = 'cases_log'
deaths_log = 'deaths_log'

options_dict = [{'label': 'Cases', 'value': 'cases_log'},
                {'label': 'Deaths', 'value': 'deaths_log'},
                {'label': '% Cases of Total Population', 'value': '% cases of total population'},
                {'label': '% Deaths of Total Cases', 'value': '% deaths of total cases'},
                {'label': 'Daily Rate of Change in Cases', 'value': 'daily_case_rate'},
                {'label': 'Daily Rate of Change in Deaths', 'value': 'daily_death_rate'}]

unique_counties = np.sort(main_df_ny['county'].unique())
county_list_dict = []
for county in unique_counties:
    county_dict = {'label': county, 'value': county}
    county_list_dict.append(county_dict)

ui_table = main_df_ny[['county', 'cases', 'deaths', 'population',
                       '% cases of total population', '% deaths of total cases']].iloc[-58:]

ui_table['% cases of total population'] = ui_table['% cases of total population']
ui_table['% deaths of total cases'] = ui_table['% deaths of total cases']

#print(main_df_ny[['date', 'Days Since First Case']].iloc[0:60])

app = dash.Dash(__name__)
server = app.server

# Create app layout
app.layout = html.Div(
    [
        html.Div(id='output-clientside'),
        html.Div(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url('covid_logo.png'),
                            id='covid-logo',
                            style={
                                'height': '60px',
                                'width': 'auto',
                                'margin-bottom': '25px',
                            },
                        )
                    ],
                    className='one-third column'
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    'COVID-19 New York State',
                                    style={'margin-bottom': '0px'},
                                ),
                                html.H5(
                                    'By Counties',
                                    style={'margin-top': '0px'}
                                ),
                            ]
                        )
                    ],
                    className='one-half column',
                    id='title',
                ),
                html.Div(
                    [
                        html.A(
                            html.Button('Learn More', id='learn-more-button'),
                            href='https://www.health.ny.gov/',
                        )
                    ],
                    className='one-third column',
                    id='button',
                ),
            ],
            id='header',
            className='row flex-display',
            style={'margin-buttom': '25px'},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P(
                            'Choose Metric:',
                            className='control_label',
                        ),
                        dcc.Dropdown(
                            id='data_selector',
                            options=options_dict,
                            multi=False,
                            placeholder='Select Data to Explore',
                            value='cases_log',
                            className='dcc_control',
                        ),
                        html.P(
                            'Filter by county names:',
                            className='control_label'
                        ),
                        dcc.Dropdown(
                            id='county_selector',
                            options=county_list_dict,
                            multi=True,
                            placeholder='Select Counties',
                            value=unique_counties,
                            className='dcc_control',
                        ),
                    ],
                    className='pretty_container four columns',
                    id='cross-filter-options'
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id='total_cases'), html.P('No. of Cases')],
                                    id='amount_cases',
                                    className='mini_container',
                                ),
                                html.Div(
                                    [html.H6(id='total_deaths'), html.P('No. of Deaths')],
                                    id='amount_deaths',
                                    className='mini_container',
                                ),
                                html.Div(
                                    [html.H6(id='cases_rate'), html.P('Cases Rate')],
                                    id='percent_cases',
                                    className='mini_container',
                                ),
                                html.Div(
                                    [html.H6(id='mortality_rate'), html.P('Mortality Rate')],
                                    id='percent_mortality',
                                    className='mini_container',
                                ),
                            ],
                            id='info-container',
                            className='row container-display',
                        ),
                        html.Div(
                            [dcc.Graph(id='map')],
                            id='map_container',
                            className='pretty_container',
                        ),
                    ],
                    id='right-column',
                    className='eight columns'
                ),
            ],
            className='row flex-display'
        ),
        html.Div(
            [
                html.Div(
                    children=[
                        html.H4(children='Flattening the Curve'),
                        dcc.Graph(id='line_graph'),
                    ],
                    className='pretty_container twelve columns'
                )
            ],
            className='row flex-display',
        ),
        html.Div(
            [
                html.Div(
                    children=[
                        html.H4(children='Most Recent Stats by County'),
                        dash_table.DataTable(
                            id='link_table',
                            columns=[{'name': i, 'id': i} for i in ui_table],
                            data=ui_table.to_dict('records'),
                            export_format='xlsx',
                            export_headers='display',
                            page_size=6,
                            filter_action='native',
                            sort_action='native',
                            row_selectable='multi',
                            row_deletable=True
                        )
                    ],
                    className='pretty_container twelve columns'
                ),
                html.Div(id='datatable-interactivity-container'),
            ],
            className='row flex-display',
        )
    ],
    id='mainContainer',
    style={'display': 'flex', 'flex-direction': 'column'},
)


@app.callback([
        Output(component_id="total_cases", component_property='children'),
        Output(component_id="total_deaths", component_property='children'),
        Output(component_id="cases_rate", component_property='children'),
        Output(component_id="mortality_rate", component_property='children'),
],
    [
        Input(component_id='county_selector', component_property='value'),
    ]
)
def update_numbers(county_selector):
    dff = ui_table.copy()
    dff = dff[dff['county'].isin(county_selector)]
    num_cases = dff['cases'].sum()
    num_deaths = dff['deaths'].sum()
    cases_rate = str(round((num_cases / (dff['population'].sum())) * 100, 2)) + '%'
    mortality_rate = str(round((num_deaths / num_cases) * 100, 2)) + '%'

    return [num_cases, num_deaths, cases_rate, mortality_rate]


@app.callback(
    [Output(component_id='map', component_property='figure'),
    Output(component_id='line_graph', component_property='figure')],
    [Input(component_id='data_selector', component_property='value'),
     Input(component_id='county_selector', component_property='value')]
)


def update_fig(selected_dropdown_value, counties_selected):

    df = main_df_ny

    df = df[df['county'].isin(counties_selected)]

    #df_by_selected_value = df.sort_values(by=selected_dropdown_value, ascending=False)

    #counties = df_by_selected_value['county'].unique()

    if selected_dropdown_value == 'cases_log':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Reds')
        # fig_bar = vc.bar_graph_counts(df, 'cases', counties, 'Reds')
    elif selected_dropdown_value == 'deaths_log':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Purples')
        # fig_bar = vc.bar_graph_counts(df, 'deaths', counties, 'Purples')
    elif selected_dropdown_value == '% cases of total population':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Reds')
        # fig_bar = vc.bar_graph_counts(df, selected_dropdown_value, counties, 'Reds')
    elif selected_dropdown_value == '% deaths of total cases':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Purples')
        # fig_bar = vc.bar_graph_counts(df, selected_dropdown_value, counties, 'Purples')
    elif selected_dropdown_value == 'daily_case_rate':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Reds')
        fig_map = fig_map.update_layout(coloraxis_colorbar=dict(title='Daily Case Rate', ticksuffix='00%'))
        # fig_bar = vc.bar_graph_counts(df, selected_dropdown_value, counties, 'Purples')
    elif selected_dropdown_value == 'daily_death_rate':
        fig_map = vc.chloropleth_map_ny(df, ny_counties, selected_dropdown_value, 'Purples')
        fig_map = fig_map.update_layout(coloraxis_colorbar=dict(title='Daily Death Rate', ticksuffix='00%'))
        # fig_bar = vc.bar_graph_counts(df, selected_dropdown_value, counties, 'Purples')

    cumulative_fig = px.line(df, x='date', y=selected_dropdown_value, color='county')

    return [fig_map, cumulative_fig]

if __name__ == '__main__':
    app.run_server(debug=True)