import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import numpy as np
from shapely.geometry import Point

st.set_page_config(
    page_title="LM Order Location Map",
    layout="wide"
)

st.title("LM Order Locations Map")
st.caption("Visualize order deliveries with clustering by hub, customer, driver, or vehicle")

# File uploader for GeoJSON and CSV files
with st.sidebar:
    st.header("Upload Data")
    geojson_file = st.file_uploader("Upload GeoJSON file", type=["geojson", "json"])
    csv_file = st.file_uploader("Upload CSV with order coordinates", type=["csv"])
    
    st.subheader("Map Settings")
    use_markers = st.checkbox("Use Map Markers", value=True)
    
    # Cluster settings
    st.subheader("Clustering Options")
    enable_clustering = st.checkbox("Enable Clustering", value=True)
    cluster_by = st.selectbox(
        "Cluster By",
        options=["None", "hub", "customer", "driver", "vehicle_model"],
        index=0
    )
    
    if enable_clustering and cluster_by != "None":
        cluster_radius = st.slider("Cluster Radius", min_value=50, max_value=500, value=100)
    
    point_radius = st.slider("Point/Marker Size", min_value=10, max_value=200, value=50)
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

# Utility function to convert hex color to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)] + [255]

# Function to process data and create map
def create_map(geojson_data, csv_data, point_radius, point_color, boundary_color, map_style, use_markers=True, enable_clustering=False, cluster_by=None, cluster_radius=100):
    # Load the boundaries from GeoJSON
    try:
        gdf_boundaries = gpd.read_file(geojson_data)
    except Exception as e:
        st.error(f"Error reading GeoJSON file: {str(e)}")
        return None
    
    # Load the order points from CSV with explicit parsing options
    try:
        df_orders = pd.read_csv(csv_data, encoding='utf-8', sep=',', quotechar='"', escapechar='\\')
        
        # Check if data was loaded correctly
        if df_orders.empty or len(df_orders.columns) <= 1:
            st.error("No data or single column found in CSV. Check file format.")
            return None
            
        st.success(f"Successfully loaded {len(df_orders)} orders with {len(df_orders.columns)} columns")
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        return None
    
    # Use the specific column names from the provided CSV structure
    lat_col = 'delivered_lat'
    lon_col = 'delivered_long'
    
    if lat_col not in df_orders.columns or lon_col not in df_orders.columns:
        # Fall back to automatic detection if the specific columns aren't found
        lat_col = next((col for col in df_orders.columns if 'lat' in col.lower()), None)
        lon_col = next((col for col in df_orders.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
        
        if not lat_col or not lon_col:
            st.error("Could not identify latitude and longitude columns. Expected 'delivered_lat' and 'delivered_long'.")
            return None
    
    # Calculate the center of the map based on order points
    center_lat = df_orders[lat_col].mean()
    center_lon = df_orders[lon_col].mean()
    
    # Create layers based on visualization settings
    layers = []
    
    # Add the GeoJSON layer for boundaries
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
    layers.append(geojson_layer)
    
    # Choose the appropriate layer for the order points
    if use_markers:
        # Icon layer for markers
        icon_data = df_orders.copy()
        # Add a column for the icon mapping
        icon_data['icon'] = 'marker'
        
        if enable_clustering and cluster_by and cluster_by in df_orders.columns:
            # Group by the selected column for clustering
            cluster_groups = df_orders.groupby(cluster_by)
            
            # Create a color palette for different clusters
            unique_values = df_orders[cluster_by].unique()
            color_palette = {}
            
            # Generate unique colors for each cluster
            for i, value in enumerate(unique_values):
                # Create a rainbow-like palette
                hue = i / len(unique_values)
                r, g, b = [int(c * 255) for c in colorsys_hsv_to_rgb(hue, 0.8, 0.9)]
                color_palette[value] = [r, g, b, 255]
            
            # Add color based on cluster
            icon_data['color'] = icon_data[cluster_by].map(color_palette)
            
            # For the legend
            st.sidebar.subheader(f"Cluster Legend ({cluster_by})")
            for value, color in color_palette.items():
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                st.sidebar.markdown(f"<div style='display: flex; align-items: center;'><div style='background-color: {hex_color}; width: 15px; height: 15px; margin-right: 10px;'></div> {value}</div>", unsafe_allow_html=True)
            
            # Create the icon layer with cluster colors
            orders_layer = pdk.Layer(
                "IconLayer",
                data=icon_data,
                get_position=[lon_col, lat_col],
                get_icon="icon",
                get_size=point_radius,
                get_color="color",
                pickable=True,
                icon_mapping={
                    "marker": {"x": 0, "y": 0, "width": 128, "height": 128, "anchorY": 128, "mask": True}
                },
                icon_atlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
            )
        else:
            # Regular icon layer without clustering
            orders_layer = pdk.Layer(
                "IconLayer",
                data=icon_data,
                get_position=[lon_col, lat_col],
                get_icon="icon",
                get_size=point_radius,
                get_color=hex_to_rgb(point_color),
                pickable=True,
                icon_mapping={
                    "marker": {"x": 0, "y": 0, "width": 128, "height": 128, "anchorY": 128, "mask": True}
                },
                icon_atlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
            )
    else:
        # ScatterplotLayer for points
        if enable_clustering and cluster_by and cluster_by in df_orders.columns:
            # Group by the selected column
            cluster_groups = df_orders.groupby(cluster_by)
            
            # Create a color palette for different clusters
            unique_values = df_orders[cluster_by].unique()
            color_palette = {}
            
            # Generate unique colors for each cluster
            for i, value in enumerate(unique_values):
                # Create a rainbow-like palette
                hue = i / len(unique_values)
                r, g, b = [int(c * 255) for c in colorsys_hsv_to_rgb(hue, 0.8, 0.9)]
                color_palette[value] = [r, g, b, 255]
            
            # Create a new DataFrame with color information
            scatter_data = df_orders.copy()
            scatter_data['color'] = scatter_data[cluster_by].map(color_palette)
            
            # For the legend
            st.sidebar.subheader(f"Cluster Legend ({cluster_by})")
            for value, color in color_palette.items():
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                st.sidebar.markdown(f"<div style='display: flex; align-items: center;'><div style='background-color: {hex_color}; width: 15px; height: 15px; margin-right: 10px;'></div> {value}</div>", unsafe_allow_html=True)
            
            orders_layer = pdk.Layer(
                "ScatterplotLayer",
                data=scatter_data,
                get_position=[lon_col, lat_col],
                get_radius=point_radius,
                get_fill_color="color",
                pickable=True,
            )
        else:
            # Regular scatterplot without clustering
            orders_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_orders,
                get_position=[lon_col, lat_col],
                get_radius=point_radius,
                get_fill_color=hex_to_rgb(point_color),
                pickable=True,
            )
    
    layers.append(orders_layer)
    
    # Create the view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10,
        pitch=0,
    )
    
    # Create tooltip based on available columns
    tooltip_html = "<b>Location:</b> {" + lat_col + "}, {" + lon_col + "}"
    
    # Add useful columns to tooltip
    useful_cols = ['number', 'customer', 'hub', 'driver', 'vehicle_model', 'postcode', 'weight', 'kms', 'created_date', 'day']
    for col in useful_cols:
        if col in df_orders.columns:
            tooltip_html += f"<br><b>{col.title()}:</b> {{{col}}}"
    
    # Create the final deck
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=map_style,
        tooltip={
            "html": tooltip_html,
            "style": {
                "backgroundColor": "white",
                "color": "black"
            }
        }
    )
    
    return r

# Define colorsys HSV to RGB conversion (since colorsys might not be available)
def colorsys_hsv_to_rgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q

    # Display the map if files are uploaded
if geojson_file and csv_file:
    try:
        # Debug information
        st.write(f"GeoJSON file: {geojson_file.name}, size: {geojson_file.size} bytes")
        st.write(f"CSV file: {csv_file.name}, size: {csv_file.size} bytes")
        
        # Preview first few lines of CSV for debugging
        csv_preview = pd.read_csv(csv_file, nrows=3)
        st.write("CSV Preview (first 3 rows):")
        st.dataframe(csv_preview)
        
        # Reset file pointer after preview
        csv_file.seek(0)
        
        # Create the map
        deck = create_map(
            geojson_file, 
            csv_file, 
            point_radius, 
            point_color, 
            boundary_color, 
            map_style,
            use_markers=use_markers,
            enable_clustering=enable_clustering,
            cluster_by=cluster_by if enable_clustering else None,
            cluster_radius=cluster_radius if 'cluster_radius' in locals() else 100
        )
        
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
                
                if cluster_by != "None" and cluster_by in df_orders.columns:
                    st.subheader(f"Clusters by {cluster_by}")
                    cluster_counts = df_orders[cluster_by].value_counts().reset_index()
                    cluster_counts.columns = [cluster_by, 'Count']
                    st.dataframe(cluster_counts)
            
            with col2:
                st.subheader("Boundary Data Info")
                gdf_boundaries = gpd.read_file(geojson_file)
                st.text(f"Number of boundaries: {len(gdf_boundaries)}")
                st.text(f"Geometry types: {set([geom.geom_type for geom in gdf_boundaries.geometry])}")
                
                # Show additional statistics and visualizations
                st.subheader("Order Distribution")
                
                # Show distribution by day if available
                if 'day' in df_orders.columns:
                    day_counts = df_orders['day'].value_counts().reset_index()
                    day_counts.columns = ['Day', 'Count']
                    st.bar_chart(day_counts.set_index('Day'))
                
                # Show distribution by vehicle model
                if 'vehicle_model' in df_orders.columns:
                    vehicle_counts = df_orders['vehicle_model'].value_counts().reset_index()
                    vehicle_counts.columns = ['Vehicle Type', 'Count']
                    st.bar_chart(vehicle_counts.set_index('Vehicle Type'))
                
                # Show average distance by hub or driver if available
                if 'kms' in df_orders.columns and 'hub' in df_orders.columns:
                    st.text("Average Distance (km) by Hub:")
                    avg_kms_by_hub = df_orders.groupby('hub')['kms'].mean().reset_index()
                    avg_kms_by_hub.columns = ['Hub', 'Avg Distance (km)']
                    st.dataframe(avg_kms_by_hub)
    
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
            'number': ['SH-2V4VQT5', 'SH-2VRC7VZ', 'SH-2V4RCNO'],
            'created_date': ['March 1, 2025, 4:21 PM', 'March 24, 2025, 12:38 PM', 'March 1, 2025, 12:01 PM'],
            'driver': ['Madesh A', 'Chandan M', 'Vishwanatha M G'],
            'registration_certificate_number': ['KA01KD5128', 'KA250103', 'KA02AE2238'],
            'vehicle_model': ['Bike', 'Bike', 'Auto Rickshaw'],
            'hub': ['Koramangala NGV [ BH Micro warehouse ]', 'Banashankari [ BH Micro warehouse ]', 'Chandra Layout [ BH Micro warehouse ]'],
            'customer': ['Herbalife Nutrition', 'Supertails', 'Herbalife Nutrition'],
            'postcode': [560046, 560108, 560079],
            'hub_long': [77.62, 77.6, 77.52],
            'hub_lat': [12.93, 12.91, 12.96],
            'delivered_long': [77.61, 77.57, 77.53],
            'delivered_lat': [13.0, 12.87, 12.98],
            'weight': [0.7, 0.8, 1.96],
            'kms': [7.97, 5.52, 2.45]
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
    4. Choose marker type and clustering options
    5. Explore the map by zooming, panning, and hovering over points
    
    **Tips:**
    - Make sure your CSV has columns containing the words 'lat' and 'lon'/'lng' for automatic detection
    - For clustering, make sure your CSV has 'hub' or 'customer' columns, or select a different column
    - Use markers for a more traditional map look, or points for a data visualization style
    - You can download the visualization by right-clicking on the map
    - Try different map styles for better visibility depending on your data
    """)
