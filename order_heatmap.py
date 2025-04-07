import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import numpy as np
from shapely.geometry import Point

st.set_page_config(
    page_title="Order Location Map",
    layout="wide"
)

st.title("Order Locations Overlay Map")

# File uploader for GeoJSON and CSV files
with st.sidebar:
    st.header("Upload Data")
    geojson_file = st.file_uploader("Upload GeoJSON file", type=["geojson", "json"])
    csv_file = st.file_uploader("Upload CSV with order coordinates", type=["csv"])
    
    st.subheader("Map Settings")
    point_radius = st.slider("Point Size", min_value=10, max_value=200, value=50)
    point_color = st.color_picker("Point Color", "#FF4B4B")
    boundary_color = st.color_picker("Boundary Color", "#0080FF")
    
    map_style = st.selectbox(
        "Map Style",
        options=[
            "mapbox://styles/mapbox/light-v10",
            "mapbox://styles/mapbox/dark-v10",
            "mapbox://styles/mapbox/streets-v11",
            "mapbox://styles/mapbox/satellite-v9",
        ],
        index=0,
    )

# Function to process data and create map
def create_map(geojson_data, csv_data, point_radius, point_color, boundary_color, map_style):
    # Load the boundaries from GeoJSON
    gdf_boundaries = gpd.read_file(geojson_data)
    
    # Load the order points from CSV
    df_orders = pd.read_csv(csv_data)
    
    # Create GeoDataFrame from order points
    # Try to automatically detect latitude/longitude column names
    lat_col = next((col for col in df_orders.columns if 'lat' in col.lower()), None)
    lon_col = next((col for col in df_orders.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
    
    if not lat_col or not lon_col:
        st.error("Could not identify latitude and longitude columns. Please rename them to 'latitude' and 'longitude'.")
        return None
    
    # Calculate the center of the map based on order points
    center_lat = df_orders[lat_col].mean()
    center_lon = df_orders[lon_col].mean()
    
    # Create a layer for the orders
    orders_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_orders,
        get_position=[lon_col, lat_col],
        get_radius=point_radius,
        get_fill_color=hex_to_rgb(point_color),
        pickable=True,
    )
    
    # Create a layer for the GeoJSON boundaries
    geojson_layer = pdk.Layer(
        'GeoJsonLayer',
        data=gdf_boundaries.to_json(),
        opacity=0.8,
        stroked=True,
        filled=True,
        extruded=False,
        wireframe=True,
        get_line_color=hex_to_rgb(boundary_color),
        get_fill_color=[0, 0, 0, 0],
        line_width_min_pixels=1,
    )
    
    # Create the view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10,
        pitch=0,
    )
    
    # Create the final deck
    r = pdk.Deck(
        layers=[geojson_layer, orders_layer],
        initial_view_state=view_state,
        map_style=map_style,
        tooltip={
            "html": "<b>Order ID:</b> {order_id}<br><b>Latitude:</b> {" + lat_col + "}<br><b>Longitude:</b> {" + lon_col + "}",
            "style": {
                "backgroundColor": "white",
                "color": "black"
            }
        }
    )
    
    return r

# Utility function to convert hex color to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)] + [255]

# Display the map if files are uploaded
if geojson_file and csv_file:
    try:
        # Create the map
        deck = create_map(geojson_file, csv_file, point_radius, point_color, boundary_color, map_style)
        
        if deck:
            # Display the map
            st.pydeck_chart(deck)
            
            # Display data statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Order Data Preview")
                df_orders = pd.read_csv(csv_file)
                st.dataframe(df_orders.head())
                st.text(f"Total orders: {len(df_orders)}")
            
            with col2:
                st.subheader("Boundary Data Info")
                gdf_boundaries = gpd.read_file(geojson_file)
                st.text(f"Number of boundaries: {len(gdf_boundaries)}")
                st.text(f"Geometry types: {set([geom.geom_type for geom in gdf_boundaries.geometry])}")
    
    except Exception as e:
        st.error(f"Error creating map: {str(e)}")
else:
    # Show placeholder content when no files are uploaded
    st.info("👈 Please upload your GeoJSON and CSV files in the sidebar to create the map.")
    
    # Show example of expected data format
    st.subheader("Expected Data Format:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Example CSV structure:**")
        example_csv = pd.DataFrame({
            'order_id': [1001, 1002, 1003],
            'latitude': [37.7749, 37.7833, 37.7694],
            'longitude': [-122.4194, -122.4167, -122.4862],
            'customer': ['John', 'Sarah', 'Michael'],
            'order_value': [125.99, 89.50, 245.00]
        })
        st.dataframe(example_csv)
    
    with col2:
        st.markdown("**Example GeoJSON structure:**")
        st.code("""
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Area 1"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-122.4194, 37.7749],
            [-122.4167, 37.7833],
            [-122.4862, 37.7694],
            [-122.4194, 37.7749]
          ]
        ]
      }
    }
  ]
}
        """)

# Add instructions and info
with st.expander("How to Use This App"):
    st.markdown("""
    1. Upload your GeoJSON file containing boundary data
    2. Upload your CSV file containing order coordinates (needs latitude and longitude columns)
    3. Adjust map settings in the sidebar to customize the visualization
    4. Explore the map by zooming, panning, and hovering over points
    
    **Tips:**
    - Make sure your CSV has columns containing the words 'lat' and 'lon'/'lng' for automatic detection
    - You can download the visualization by right-clicking on the map
    - Try different map styles for better visibility depending on your data
    """)
