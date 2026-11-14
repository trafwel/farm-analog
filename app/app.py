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
