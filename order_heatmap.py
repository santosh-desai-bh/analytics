import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(
    page_title="LM Order Location Map",
    layout="wide"
)

st.title("LM Order Locations Map")
st.caption("Simple map of order locations with hub centroids")

# File uploader for CSV file
csv_file = st.file_uploader("Upload CSV with order coordinates", type=["csv"])

# Map settings in the sidebar
with st.sidebar:
    st.header("Map Settings")
    
    # Point sizes
    order_point_size = st.slider("Order Point Size", min_value=10, max_value=100, value=30)
    hub_point_size = st.slider("Hub Point Size", min_value=50, max_value=200, value=100)
    
    # Point colors
    order_color = st.color_picker("Order Point Color", "#FF4B4B")
    hub_color = st.color_picker("Hub Point Color", "#00FF00")
    
    # Map style
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

# Create the map
def create_map(csv_data, order_point_size, hub_point_size, order_color, hub_color, map_style):
    try:
        # Load the order points from CSV with explicit parsing options
        df_orders = pd.read_csv(csv_data, encoding='utf-8')
        
        # Check if data was loaded correctly
        if df_orders.empty or len(df_orders.columns) <= 1:
            st.error("No data or single column found in CSV. Check file format.")
            return None
            
        st.success(f"Successfully loaded {len(df_orders)} orders with {len(df_orders.columns)} columns")
        
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
        
        layers = []
        
        # Create a layer for the orders
        orders_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_orders,
            get_position=[lon_col, lat_col],
            get_radius=order_point_size,
            get_fill_color=hex_to_rgb(order_color),
            pickable=True,
        )
        layers.append(orders_layer)
        
        # Add a layer for hub locations if present in the data
        if 'hub_lat' in df_orders.columns and 'hub_long' in df_orders.columns:
            # Extract unique hubs to avoid duplicate markers
            hub_data = df_orders[['hub', 'hub_lat', 'hub_long']].drop_duplicates().reset_index(drop=True)
            
            hub_layer = pdk.Layer(
                "ScatterplotLayer",
                data=hub_data,
                get_position=['hub_long', 'hub_lat'],
                get_radius=hub_point_size,
                get_fill_color=hex_to_rgb(hub_color),
                pickable=True,
                stroked=True,
                get_line_color=[0, 0, 0],
                line_width_min_pixels=2,
            )
            layers.append(hub_layer)
        
        # Create the view state
        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10,
            pitch=0,
        )
        
        # Create the final deck
        r = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            map_style=map_style,
            tooltip={
                "html": "<b>Type:</b> {hub_long ? 'Hub' : 'Order'}<br>"
                        + "<b>Location:</b> {" + lat_col + "}, {" + lon_col + "}<br>"
                        + "{number ? '<b>Order:</b> ' + number : ''}<br>"
                        + "{hub ? '<b>Hub:</b> ' + hub : ''}",
                "style": {
                    "backgroundColor": "white",
                    "color": "black"
                }
            }
        )
        
        return r
    
    except Exception as e:
        st.error(f"Error creating map: {str(e)}")
        return None

# Display the map if CSV file is uploaded
if csv_file:
    # Create the map
    deck = create_map(
        csv_file, 
        order_point_size, 
        hub_point_size, 
        order_color, 
        hub_color, 
        map_style
    )
    
    if deck:
        # Display the map
        st.pydeck_chart(deck)
        
        # Display data statistics
        st.subheader("Data Preview")
        df_orders = pd.read_csv(csv_file)
        st.dataframe(df_orders.head())
        
        # Count orders by hub
        if 'hub' in df_orders.columns:
            st.subheader("Orders by Hub")
            hub_counts = df_orders['hub'].value_counts().reset_index()
            hub_counts.columns = ['Hub', 'Count']
            st.dataframe(hub_counts)
else:
    # Show placeholder content when no file is uploaded
    st.info("Please upload your CSV file with order data to create the map.")
    
    # Show example of expected data format
    st.subheader("Expected CSV Format:")
    example_csv = pd.DataFrame({
        'number': ['SH-2V4VQT5', 'SH-2VRC7VZ', 'SH-2V4RCNO'],
        'created_date': ['March 1, 2025, 4:21 PM', 'March 24, 2025, 12:38 PM', 'March 1, 2025, 12:01 PM'],
        'driver': ['Madesh A', 'Chandan M', 'Vishwanatha M G'],
        'hub': ['Koramangala NGV', 'Banashankari', 'Chandra Layout'],
        'customer': ['Herbalife Nutrition', 'Supertails', 'Herbalife Nutrition'],
        'delivered_long': [77.61, 77.57, 77.53],
        'delivered_lat': [13.0, 12.87, 12.98],
        'hub_long': [77.62, 77.6, 77.52],
        'hub_lat': [12.93, 12.91, 12.96],
    })
    st.dataframe(example_csv)
