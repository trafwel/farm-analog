"""Local data preview. The planned production app uses React and FastAPI."""
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Farm Analog · Palouse", layout="wide")
st.title("Farm Analog")
st.write("Explore soil moisture in the Palouse, Washington.")
st.caption("Historical sample · July 1–7, 2025 · NASA SMAP L4")

sample = Path(__file__).resolve().parents[1] / "data/samples/palouse_smap_2025-07-01_2025-07-08.csv"
try:
    data = pd.read_csv(sample, parse_dates=["timestamp_utc"])
    metadata = json.loads(sample.with_suffix(".json").read_text())
except (OSError, ValueError) as exc:
    st.error(f"Could not load the included SMAP sample: {exc}")
    st.stop()

west, south, east, north = metadata["bounds_west_south_east_north"]
polygon = [[west, south], [east, south], [east, north], [west, north], [west, south]]
left, right = st.columns([3, 2])
with left:
    st.subheader("Our sample area")
    st.pydeck_chart(pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=(south+north)/2, longitude=(west+east)/2, zoom=7),
        layers=[pdk.Layer("PolygonLayer", data=[{"polygon": polygon, "name": "Palouse sample area"}],
                          get_polygon="polygon", get_fill_color=[41, 127, 95, 45],
                          get_line_color=[28, 106, 76], stroked=True, filled=True,
                          line_width_min_pixels=3, pickable=True)],
        tooltip={"text": "{name}"},
    ), height=430)
    st.caption("Outline = the approximate area averaged in this sample, not a field boundary or moisture heatmap. Map © CARTO / OpenStreetMap contributors.")
with right:
    st.subheader("Water in the soil")
    st.metric("Average surface moisture · top 5 cm", f"{data.sm_surface_mean.mean()*100:.1f}%")
    st.metric("Average root-zone moisture · top 100 cm", f"{data.sm_rootzone_mean.mean()*100:.1f}%")
    st.write("These percentages describe water volume divided by soil volume. For example, 20% means roughly 20 litres of water per 100 litres of soil—not 20% of the water a crop needs.")
    st.info("Regional estimates combining satellite observations and a land model. They do not measure an individual field or establish whether a crop is stressed.")

st.subheader("How moisture changed during the week")
chart = data.set_index("timestamp_utc")[["sm_surface_mean", "sm_rootzone_mean"]].mul(100)
chart.columns = ["Surface · 0–5 cm", "Root zone · 0–100 cm"]
st.line_chart(chart, x_label="Time (UTC)", y_label="Water volume / soil volume (%)", height=300)
st.caption(f"{len(data)} readings, three hours apart. Each line is an average across the outlined region. This is historical data, not live conditions or a 2050 projection.")
with st.expander("Source and sample data"):
    st.markdown(f"[NASA SMAP L4, version 8]({metadata['source']}) · Native grid: 9 km; reprojected by Earth Engine.")
    st.dataframe(data, hide_index=True)
    st.download_button("Download sample CSV", sample.read_bytes(), file_name=sample.name, mime="text/csv")

climate_path = sample.parent / 'palouse_climate_ACCESS-CM2_ssp245_2050.csv'
if climate_path.exists():
    st.divider()
    st.subheader('A first look at the Palouse around 2050')
    st.caption('ACCESS-CM2 model · SSP2-4.5 scenario · 2041–2060 compared with 1995–2014')
    climate = pd.read_csv(climate_path)
    labels = {'baseline': '1995–2014 modeled baseline', 'future': '2041–2060 projection'}
    climate['Period'] = climate['period'].map(labels)
    temp, rain = st.columns(2)
    with temp:
        st.write('**Average temperature by month**')
        st.line_chart(climate.pivot(index='month', columns='Period', values='temperature_c'),
                      x_label='Month (1 = January)', y_label='Temperature (°C)')
    with rain:
        st.write('**Average precipitation by month**')
        st.bar_chart(climate.pivot(index='month', columns='Period', values='precipitation_mm'),
                     x_label='Month (1 = January)', y_label='Precipitation (mm)', stack=False)
    st.info('This is one model under one emissions scenario, not a prediction of exact weather in 2050. The baseline is also modeled. We still need multiple models and current-climate comparisons before identifying reliable analog regions.')
    st.download_button('Download climate comparison', climate_path.read_bytes(), file_name=climate_path.name, mime='text/csv')

analog_path = sample.parent / 'palouse_analog_candidates.csv'
if analog_path.exists():
    st.divider()
    st.subheader('Where could the Palouse’s future climate have a match?')
    analogs = pd.read_csv(analog_path)
    summary = json.loads((sample.parent / 'palouse_analog_summary.json').read_text())
    st.caption(f"First regional search · {len(analogs)} sampled locations · ACCESS-CM2 / SSP2-4.5")
    st.warning('Exploratory climate matches only. These compare projected 2041–2060 conditions with PRISM’s 1995–2014 reference climate—not today’s weather. Soil and crop suitability have not been checked.')
    chosen_rank = st.selectbox('Compare a candidate', analogs.head(20)['rank'].tolist(),
        format_func=lambda rank: f"#{rank} · {analogs.iloc[rank-1].latitude:.3f}° N, {abs(analogs.iloc[rank-1].longitude):.3f}° W · {analogs.iloc[rank-1].sigma:.2f} sigma")
    selected = analogs[analogs['rank']==chosen_rank].iloc[0]
    points = analogs.head(50).copy()
    points['color'] = points['rank'].apply(lambda rank: [12,48,115,220] if rank<=10 else [72,139,214,150])
    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        initial_view_state=pdk.ViewState(latitude=46.3,longitude=-118.5,zoom=6),
        layers=[
            pdk.Layer('PolygonLayer',data=[{'polygon':polygon}],get_polygon='polygon',get_fill_color=[41,127,95,45],get_line_color=[28,106,76],stroked=True,line_width_min_pixels=3),
            pdk.Layer('ScatterplotLayer',data=points,get_position='[longitude, latitude]',get_fill_color='color',get_radius=4500,pickable=True),
            pdk.Layer('ScatterplotLayer',data=[selected.to_dict()],get_position='[longitude, latitude]',get_fill_color=[245,157,43],get_radius=5500,pickable=True),
        ],tooltip={'text':'Candidate #{rank}\nSigma dissimilarity: {sigma}'}),height=440)
    st.caption('Green: Palouse target area. Blue: 50 closest sampled climates (darker = top 10). Orange: selected candidate. Points are sampled climate cells, not farms. Map © CARTO / OpenStreetMap contributors.')
    comparison=[]
    for q,quarter in enumerate(summary['quarters']):
        for kind,unit in [('temperature','°C'),('precipitation','mm')]:
            key=f'{kind}_{q}'
            comparison.append({'Period':quarter,'Measure':f'{kind.title()} ({unit})',
                'Palouse reference':round(summary['target_observed'][key],1),
                'Palouse projected':round(summary['target_future'][key],1),
                'Candidate reference':round(float(selected[key]),1)})
    st.dataframe(pd.DataFrame(comparison),hide_index=True)
    st.write(f"**Climate distance: {selected.sigma:.2f} sigma.** Lower means closer for the eight climate measures used. This is not a probability of success or a crop recommendation.")
    with st.expander('How the matches were calculated'):
        st.write(summary['method'])
        st.write(summary['spatial_support'])
        st.write(summary['limitations'])
        st.markdown('[PRISM / Oregon State University](https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_ANm) · [NASA NEX-GDDP-CMIP6](https://developers.google.com/earth-engine/datasets/catalog/NASA_GDDP-CMIP6)')
        st.download_button('Download candidate rankings',analog_path.read_bytes(),file_name=analog_path.name,mime='text/csv')
