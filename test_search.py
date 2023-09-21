import folium
import streamlit as st

from streamlit_folium import st_folium

st.set_page_config(layout="wide")

tiles = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
attr = 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'

# Initialize map
m = folium.Map(
    location=[40.0158, -105.2792],
    zoom_start=12,
    tiles=tiles,
    attr=attr,
)

# call to render Folium map in Streamlit
st_data = st_folium(
    m,
    use_container_width=True,
)

if st_data["last_clicked"]:
    c1, c2 = st.columns(2,)
    with c1:
        st.write(st_data["last_clicked"]["lat"])
    with c2:
        st.write(st_data["last_clicked"]["lng"])
