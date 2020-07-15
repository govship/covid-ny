import plotly.express as px

def chloropleth_map_ny(df, geojson, data_analyzing, color_continuous_scale):
    fig = px.choropleth(df,
                        geojson=geojson,
                        locations="fips",
                        featureidkey="properties.id",
                        color=data_analyzing,
                        color_continuous_scale=color_continuous_scale,
                        hover_name="county",
                        hover_data=['deaths', 'cases', 'population'],
                        range_color=[0, max(df[data_analyzing])],
                        scope='usa',
                        animation_frame="date",
                        title='Geographic Density of Metric'
                        )

    fig["layout"].pop("updatemenus")
    fig.update_geos(fitbounds="locations", visible=False)
    #fig.update_layout(coloraxis_colorbar=dict(title='Deaths', tickprefix='1.e'))

    return fig

def bar_graph_counts(df, count, counties, color):
    fig = px.bar(df, x=count, y=counties, orientation='h', color_continuous_scale=color, log_x=True,
                 hover_data=['county', 'deaths', 'cases', 'population'])
    return fig