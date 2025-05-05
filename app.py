import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap, MarkerCluster
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import math

# Page configuration
st.set_page_config(
    page_title="Bengaluru Logistics Network Analyzer",
    page_icon="🚚",
    layout="wide"
)

# Header
st.title("Bengaluru Logistics Network Analyzer")
st.markdown("Network flow analysis based on delivery data")

# Sidebar for data upload
st.sidebar.header("Data Import")

# Direct download links to Metabase
st.sidebar.markdown("""
### Download Data from Metabase
Get the latest data directly from Metabase:
- [Last Mile Delivery Data](https://analytics.blowhorn.com/question/3120-if-network-analysis-last-mile?start=2025-04-01&end=2025-04-30)
- [Pickups Data](https://analytics.blowhorn.com/question/3116-actual-pickups?start=2025-04-01&end=2025-04-30)
- [Costs Data](https://analytics.blowhorn.com/question/3113-if-costs-by-driver?start=2025-04-01&end=2025-04-30)
""")

# File uploaders
last_mile_file = st.sidebar.file_uploader("Upload Last Mile Delivery CSV", type=['csv'])
pickups_file = st.sidebar.file_uploader("Upload Pickups CSV", type=['csv'])
costs_file = st.sidebar.file_uploader("Upload Costs CSV", type=['csv'])

# Analysis type selection
st.sidebar.header("Analysis Settings")
analysis_type = st.sidebar.radio(
    "Select Analysis View",
    ["Network Flow", "Density Analysis", "Weight-Distance Analysis", "Driver Cost Analysis"]
)

# Network type filter - only show when Network Flow is selected
if analysis_type == "Network Flow":
    network_segments = st.sidebar.multiselect(
        "Network Segments to Display",
        ["First Mile", "Middle Mile", "Last Mile"],
        default=["First Mile", "Last Mile"]
    )

# Check if files are uploaded
if not last_mile_file:
    st.info("Please upload the Last Mile Delivery CSV file to begin analysis")
    st.stop()

# Load the last mile data
@st.cache_data
def load_last_mile_data(file):
    df = pd.read_csv(file)
    return df

last_mile_df = load_last_mile_data(last_mile_file)

# Load pickups data if available
if pickups_file:
    @st.cache_data
    def load_pickups_data(file):
        df = pd.read_csv(file)
        return df
    
    pickups_df = load_pickups_data(pickups_file)
else:
    pickups_df = None

# Load costs data if available
if costs_file:
    @st.cache_data
    def load_costs_data(file):
        df = pd.read_csv(file)
        return df
    
    costs_df = load_costs_data(costs_file)
else:
    costs_df = None

# Data summary
st.subheader("Data Summary")
col1, col2, col3 = st.columns(3)

# Display metrics with error handling for missing columns
col1.metric("Total Deliveries", f"{len(last_mile_df):,}")

# Check if 'hub' column exists, otherwise look for alternative columns
if 'hub' in last_mile_df.columns:
    col2.metric("Total Hubs", f"{last_mile_df['hub'].nunique():,}")
else:
    # Look for alternative hub-related columns
    hub_cols = [col for col in last_mile_df.columns if 'hub' in col.lower() and not col.endswith('_lat') and not col.endswith('_long')]
    if hub_cols:
        col2.metric("Total Hubs", f"{last_mile_df[hub_cols[0]].nunique():,}")
    else:
        col2.metric("Total Hubs", "N/A")

# Check if 'driver' column exists
if 'driver' in last_mile_df.columns:
    col3.metric("Total Drivers", f"{last_mile_df['driver'].nunique():,}")
else:
    # Look for alternative driver columns
    driver_cols = [col for col in last_mile_df.columns if 'driver' in col.lower()]
    if driver_cols:
        col3.metric("Total Drivers", f"{last_mile_df[driver_cols[0]].nunique():,}")
    else:
        col3.metric("Total Drivers", "N/A")

# Apply filters
st.sidebar.header("Filters")

# Hub filter - with error handling
if 'hub' in last_mile_df.columns:
    hub_column = 'hub'
else:
    # Look for alternative hub columns
    possible_hub_cols = [col for col in last_mile_df.columns if 'hub' in col.lower() and not col.endswith('_lat') and not col.endswith('_long')]
    hub_column = possible_hub_cols[0] if possible_hub_cols else None

if hub_column:
    hub_options = ["All"] + sorted(last_mile_df[hub_column].unique().tolist())
    selected_hub = st.sidebar.selectbox(f"Select {hub_column.title()}", hub_options)
    
    if selected_hub != "All":
        last_mile_df = last_mile_df[last_mile_df[hub_column] == selected_hub]

# Customer filter - with error handling
if 'customer' in last_mile_df.columns:
    customer_options = ["All"] + sorted(last_mile_df['customer'].unique().tolist())
    selected_customer = st.sidebar.selectbox("Select Customer", customer_options)
    
    if selected_customer != "All":
        last_mile_df = last_mile_df[last_mile_df['customer'] == selected_customer]

# Weight range filter - with error handling
if 'weight' in last_mile_df.columns:
    min_weight = float(last_mile_df['weight'].min())
    max_weight = float(last_mile_df['weight'].max())
    weight_range = st.sidebar.slider(
        "Weight Range (kg)",
        min_weight,
        max_weight,
        (min_weight, max_weight)
    )
    
    last_mile_df = last_mile_df[
        (last_mile_df['weight'] >= weight_range[0]) &
        (last_mile_df['weight'] <= weight_range[1])
    ]

# Main analysis display
if analysis_type == "Network Flow":
    st.subheader("Network Flow Analysis")
    
    # Get selected network segments (default selection handled in sidebar)
    display_first_mile = "First Mile" in network_segments
    display_middle_mile = "Middle Mile" in network_segments
    display_last_mile = "Last Mile" in network_segments
    
    # Create folium map centered around Bengaluru
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=11, tiles="CartoDB positron")
    
    # Define an icon function for better visualization
    def get_icon(type):
        icons = {
            "microwarehouse": folium.Icon(icon="home", prefix="fa", color="blue"),
            "customer_hub": folium.Icon(icon="building", prefix="fa", color="purple"),
            "delivery": folium.Icon(icon="shopping-bag", prefix="fa", color="red")
        }
        return icons.get(type, folium.Icon(icon="circle", prefix="fa", color="gray"))
    
    # Add microwarehouses (hubs) 
    hub_column = None
    if 'hub' in last_mile_df.columns:
        hub_column = 'hub'
    else:
        possible_hub_cols = [col for col in last_mile_df.columns if 'hub' in col.lower() and not col.endswith('_lat') and not col.endswith('_long')]
        hub_column = possible_hub_cols[0] if possible_hub_cols else None
    
    if hub_column and 'hub_lat' in last_mile_df.columns and 'hub_long' in last_mile_df.columns:
        hub_group = folium.FeatureGroup(name="Micro-warehouses")
        
        # Group by hub to get counts - using the dynamically determined hub_column
        hub_counts = last_mile_df.groupby([hub_column, 'hub_lat', 'hub_long']).size().reset_index(name='count')
        
        for idx, row in hub_counts.iterrows():
            folium.Marker(
                location=[row['hub_lat'], row['hub_long']],
                popup=f"""
                <b>Micro-warehouse:</b> {row[hub_column]}<br>
                <b>Deliveries:</b> {row['count']}<br>
                <b>Type:</b> Last Mile Distribution Point<br>
                """,
                icon=get_icon("microwarehouse")
            ).add_to(hub_group)
        
        hub_group.add_to(m)
    
    # Add Last Mile data if selected
    if display_last_mile and 'delivered_lat' in last_mile_df.columns and 'delivered_long' in last_mile_df.columns:
        delivery_group = folium.FeatureGroup(name="Last Mile Deliveries")
        
        # Sample a subset of deliveries for better performance
        sample_size = min(200, len(last_mile_df))
        sample_df = last_mile_df.sample(sample_size)
        
        # Cluster the delivery markers for better map performance
        marker_cluster = MarkerCluster(name="Delivery Clusters").add_to(delivery_group)
        
        # Add delivery markers
        for idx, row in sample_df.iterrows():
            folium.CircleMarker(
                location=[row['delivered_lat'], row['delivered_long']],
                radius=3,
                popup=f"""
                <b>Order:</b> {row['number'] if 'number' in row else 'N/A'}<br>
                <b>Weight:</b> {row['weight'] if 'weight' in row else 'N/A'} kg<br>
                <b>Distance:</b> {row['kms'] if 'kms' in row else 'N/A'} km<br>
                <b>Type:</b> Last Mile Delivery<br>
                """,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=0.6
            ).add_to(marker_cluster)
        
        delivery_group.add_to(m)
        
        # Add flow lines from hub to delivery (last mile routes)
        flow_group = folium.FeatureGroup(name="Last Mile Routes")
        
        for idx, row in sample_df.iterrows():
            folium.PolyLine(
                locations=[
                    [row['hub_lat'], row['hub_long']],
                    [row['delivered_lat'], row['delivered_long']]
                ],
                color='green',
                weight=1.5,
                opacity=0.7,
                tooltip=f"Last Mile: {row[hub_column] if hub_column else 'Hub'} → Delivery"
            ).add_to(flow_group)
        
        flow_group.add_to(m)
    
    # Add First Mile data if selected and available
    if display_first_mile and pickups_df is not None:
        # First, add customer hubs
        customer_group = folium.FeatureGroup(name="Customer Hubs (Pickup Points)")
        
        # Check for required columns
        if 'customerlat' in pickups_df.columns and 'customerlong' in pickups_df.columns and 'customer' in pickups_df.columns:
            # Group by customer to get unique pickup locations with counts
            customer_counts = pickups_df.groupby(['customer', 'customerlat', 'customerlong']).size().reset_index(name='pickup_count')
            
            for idx, row in customer_counts.iterrows():
                folium.Marker(
                    location=[row['customerlat'], row['customerlong']],
                    popup=f"""
                    <b>Customer Hub:</b> {row['customer']}<br>
                    <b>Pickups:</b> {row['pickup_count']}<br>
                    <b>Type:</b> First Mile Pickup Point<br>
                    """,
                    icon=get_icon("customer_hub")
                ).add_to(customer_group)
            
            customer_group.add_to(m)
            
            # Add first mile routes from customer hubs to microwarehouses
            first_mile_group = folium.FeatureGroup(name="First Mile Routes")
            
            # Sample pickups for better performance
            pickup_sample_size = min(100, len(pickups_df))
            pickup_sample = pickups_df.sample(pickup_sample_size)
            
            for idx, row in pickup_sample.iterrows():
                # Add flow line from customer to microwarehouse
                folium.PolyLine(
                    locations=[
                        [row['customerlat'], row['customerlong']],
                        [row['microwarehouselat'], row['microwarehouselong']]
                    ],
                    color='blue',
                    weight=2,
                    opacity=0.7,
                    dash_array='5',
                    tooltip=f"First Mile: {row['customer']} → {row['microwarehouse'] if 'microwarehouse' in row else 'Warehouse'}"
                ).add_to(first_mile_group)
            
            first_mile_group.add_to(m)
            
            # Add a First Mile Summary
            if display_first_mile and st.checkbox("Show First Mile Summary", value=True):
                st.subheader("First Mile Pickup Summary")
                
                # Calculate avg pickups per customer hub
                avg_pickups = customer_counts['pickup_count'].mean()
                
                # Calculate total number of orders picked up
                total_pickups = pickups_df['num_orders'].sum() if 'num_orders' in pickups_df.columns else len(pickups_df)
                
                # Create metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Customer Hubs", f"{len(customer_counts):,}")
                col2.metric("Avg Pickups per Hub", f"{avg_pickups:.1f}")
                col3.metric("Total Orders Picked", f"{total_pickups:,}")
                
                # Create pickup time distribution if available
                if 'pickedup_at' in pickups_df.columns:
                    try:
                        # Convert to datetime and extract hour
                        pickups_df['pickup_hour'] = pd.to_datetime(pickups_df['pickedup_at']).dt.hour
                        
                        # Create hour distribution chart
                        hour_counts = pickups_df.groupby('pickup_hour').size().reset_index(name='count')
                        
                        fig = px.line(
                            hour_counts,
                            x='pickup_hour',
                            y='count',
                            title='Pickup Distribution by Hour of Day',
                            labels={'pickup_hour': 'Hour of Day', 'count': 'Number of Pickups'}
                        )
                        
                        fig.update_xaxes(tickmode='linear', tick0=0, dtick=1)
                        st.plotly_chart(fig)
                    except:
                        st.write("Could not parse pickup time distribution")
    
    # Add Middle Mile data if selected
    if display_middle_mile and pickups_df is not None:
        if 'microwarehouselat' in pickups_df.columns and 'microwarehouselong' in pickups_df.columns:
            # Create a middle mile group for visualization
            middle_mile_group = folium.FeatureGroup(name="Middle Mile Transfers")
            
            # Get unique microwarehouses
            if 'microwarehouse' in pickups_df.columns:
                microwarehouse_field = 'microwarehouse'
            else:
                microwarehouse_field = None
            
            # Create connections between microwarehouses (simplified representation)
            # In a real implementation, you'd use actual middle mile trip data
            warehouses = pickups_df.drop_duplicates(['microwarehouselat', 'microwarehouselong'])
            
            if len(warehouses) > 1:
                # Create a simple network connecting warehouses
                for i, warehouse1 in warehouses.iterrows():
                    for j, warehouse2 in warehouses.iterrows():
                        if i < j:  # Only connect each pair once
                            folium.PolyLine(
                                locations=[
                                    [warehouse1['microwarehouselat'], warehouse1['microwarehouselong']],
                                    [warehouse2['microwarehouselat'], warehouse2['microwarehouselong']]
                                ],
                                color='orange',
                                weight=3,
                                opacity=0.6,
                                dash_array='10,10',
                                tooltip="Middle Mile Transfer Route"
                            ).add_to(middle_mile_group)
            
            middle_mile_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display the map
    folium_static(m)
    
    # Display legend explaining the map elements
    st.markdown("""
    ### Map Legend
    - 🏠 **Blue Markers**: Micro-warehouses (distribution hubs)
    - 🏢 **Purple Markers**: Customer Pickup Hubs
    - 🔴 **Red Circles**: Last Mile Delivery Points
    - 🟦 **Blue Dashed Lines**: First Mile Routes (Customer Hub → Micro-warehouse)
    - 🟧 **Orange Dashed Lines**: Middle Mile Routes (Micro-warehouse → Micro-warehouse)
    - 🟩 **Green Lines**: Last Mile Routes (Micro-warehouse → Delivery Point)
    """)
    
    # Display flow statistics based on selected network segments
    if display_last_mile:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Last Mile Delivery Stats")
            if 'kms' in last_mile_df.columns:
                st.write(f"Average Delivery Distance: {last_mile_df['kms'].mean():.2f} km")
                st.write(f"Max Delivery Distance: {last_mile_df['kms'].max():.2f} km")
                st.write(f"Min Delivery Distance: {last_mile_df['kms'].min():.2f} km")
                
                # Histogram of delivery distances
                fig = px.histogram(
                    last_mile_df, 
                    x='kms',
                    nbins=20,
                    title='Distribution of Last Mile Delivery Distances',
                    labels={'kms': 'Distance (km)', 'count': 'Number of Deliveries'}
                )
                st.plotly_chart(fig)
            else:
                st.write("Distance data not available in the uploaded file.")
        
        with col2:
            st.subheader("Hub Activity")
            
            if hub_column:
                # Bar chart of deliveries per hub
                hub_delivery_counts = last_mile_df.groupby(hub_column).size().reset_index(name='count')
                hub_delivery_counts = hub_delivery_counts.sort_values('count', ascending=False)
                
                fig = px.bar(
                    hub_delivery_counts,
                    x=hub_column,
                    y='count',
                    title='Deliveries per Micro-warehouse',
                    labels={hub_column: 'Micro-warehouse', 'count': 'Number of Deliveries'}
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig)
            else:
                st.write("Hub data not available in the uploaded file.")
    
    # Add customer-hub breakdown
    if 'customer' in last_mile_df.columns and hub_column:
        st.subheader("Customer-Hub Breakdown")
        
        # Create a pivot table of customer vs hub
        customer_hub_breakdown = pd.pivot_table(
            last_mile_df,
            values='number' if 'number' in last_mile_df.columns else None,
            index='customer',
            columns=hub_column,
            aggfunc='count',
            fill_value=0
        )
        
        # Display the pivot table
        st.dataframe(customer_hub_breakdown)
        
        # Visualize as a heatmap
        fig = px.imshow(
            customer_hub_breakdown,
            labels=dict(x=hub_column, y="Customer", color="Deliveries"),
            title=f"Delivery Count by Customer and {hub_column}",
            color_continuous_scale="Viridis"
        )
        fig.update_layout(height=600)
        st.plotly_chart(fig)
        
        # If weight is available, show weight distribution
        if 'weight' in last_mile_df.columns:
            # Create a pivot table of customer vs hub for total weight
            customer_hub_weight = pd.pivot_table(
                last_mile_df,
                values='weight',
                index='customer',
                columns=hub_column,
                aggfunc='sum',
                fill_value=0
            )
            
            st.subheader("Weight Distribution by Customer and Hub")
            
            # Visualize as a heatmap
            fig = px.imshow(
                customer_hub_weight,
                labels=dict(x=hub_column, y="Customer", color="Total Weight (kg)"),
                title=f"Total Weight by Customer and {hub_column}",
                color_continuous_scale="Reds"
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig)

elif analysis_type == "Density Analysis":
    st.subheader("Delivery Density Analysis")
    
    # Create density map
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=11, tiles="CartoDB positron")
    
    # Add hub markers
    for idx, row in last_mile_df.drop_duplicates(['hub_lat', 'hub_long']).iterrows():
        if 'hub' in last_mile_df.columns:
            hub_name = row['hub']
        else:
            hub_name = f"Hub at {row['hub_lat']:.4f}, {row['hub_long']:.4f}"
            
        folium.CircleMarker(
            location=[row['hub_lat'], row['hub_long']],
            radius=8,
            popup=f"Hub: {hub_name}",
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.7
        ).add_to(m)
    
    # Prepare data for heatmap - weight by package weight if available
    if 'weight' in last_mile_df.columns:
        heat_data = []
        for idx, row in last_mile_df.iterrows():
            # Use weight to determine intensity (normalize weight to be useful for heatmap)
            weight_factor = min(1.0, row['weight'] / 20)  # Cap at 1.0, assuming 20kg is "heavy"
            heat_data.append([row['delivered_lat'], row['delivered_long'], weight_factor])
    else:
        heat_data = last_mile_df[['delivered_lat', 'delivered_long']].values.tolist()
    
    # Add heatmap layer
    HeatMap(
        heat_data,
        radius=15,
        gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'},
        blur=13,
        max_zoom=13
    ).add_to(m)
    
    # Display the map
    folium_static(m)
    
    # Display density metrics by customer if customer column exists
    if 'customer' in last_mile_df.columns:
        st.subheader("Customer Delivery Analysis")
        
        # Group data by customer
        customer_stats = last_mile_df.groupby('customer').agg(
            delivery_count=('number', 'count'),
            total_weight=('weight', 'sum') if 'weight' in last_mile_df.columns else ('number', 'count'),
            avg_distance=('kms', 'mean') if 'kms' in last_mile_df.columns else None,
            total_distance=('kms', 'sum') if 'kms' in last_mile_df.columns else None
        ).reset_index()
        
        # Remove any None columns
        customer_stats = customer_stats.dropna(axis=1)
        
        # Calculate weight-distance product if both available
        if 'total_weight' in customer_stats.columns and 'total_distance' in customer_stats.columns:
            customer_stats['weight_distance_product'] = customer_stats['total_weight'] * customer_stats['total_distance']
            customer_stats['avg_weight_per_km'] = customer_stats['total_weight'] / customer_stats['total_distance']
        
        # Sort by delivery count
        customer_stats = customer_stats.sort_values('delivery_count', ascending=False)
        
        # Show total weight vs total distance chart
        if 'total_weight' in customer_stats.columns and 'total_distance' in customer_stats.columns:
            st.subheader("Weight vs. Distance by Customer")
            
            fig = px.scatter(
                customer_stats,
                x='total_distance',
                y='total_weight',
                size='delivery_count',
                color='customer',
                hover_name='customer',
                title='Total Weight vs. Total Distance by Customer',
                labels={
                    'total_distance': 'Total Distance (km)', 
                    'total_weight': 'Total Weight (kg)',
                    'delivery_count': 'Number of Deliveries'
                }
            )
            st.plotly_chart(fig)
        
        # Show the customer stats table
        st.subheader("Customer Metrics")
        st.dataframe(customer_stats)
    
    # Display area-based metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Postcode Distribution")
        
        if 'postcode' in last_mile_df.columns:
            # Bar chart of top postcodes by weight if available
            if 'weight' in last_mile_df.columns:
                postcode_stats = last_mile_df.groupby('postcode').agg(
                    count=('number', 'count'),
                    total_weight=('weight', 'sum')
                ).reset_index()
                
                top_postcodes = postcode_stats.sort_values('total_weight', ascending=False).head(15)
                
                fig = px.bar(
                    top_postcodes,
                    x='postcode',
                    y='total_weight',
                    title='Top 15 Postcodes by Total Weight',
                    labels={'postcode': 'Postcode', 'total_weight': 'Total Weight (kg)'}
                )
                st.plotly_chart(fig)
            else:
                # Simple count if weight not available
                postcode_counts = last_mile_df.groupby('postcode').size().reset_index(name='count')
                top_postcodes = postcode_counts.sort_values('count', ascending=False).head(15)
                
                fig = px.bar(
                    top_postcodes,
                    x='postcode',
                    y='count',
                    title='Top 15 Postcodes by Delivery Count',
                    labels={'postcode': 'Postcode', 'count': 'Number of Deliveries'}
                )
                st.plotly_chart(fig)
    
    with col2:
        st.subheader("Delivery Time Distribution")
        
        if 'created_date' in last_mile_df.columns:
            try:
                last_mile_df['hour'] = pd.to_datetime(last_mile_df['created_date']).dt.hour
                
                # Create hour distribution chart with average weight if available
                if 'weight' in last_mile_df.columns:
                    hour_stats = last_mile_df.groupby('hour').agg(
                        count=('number', 'count'),
                        avg_weight=('weight', 'mean')
                    ).reset_index()
                    
                    fig = px.line(
                        hour_stats,
                        x='hour',
                        y='count',
                        title='Delivery Distribution by Hour of Day',
                        labels={'hour': 'Hour of Day', 'count': 'Number of Deliveries'}
                    )
                    
                    # Add a secondary y-axis for average weight
                    fig.add_trace(
                        go.Scatter(
                            x=hour_stats['hour'],
                            y=hour_stats['avg_weight'],
                            name='Avg Weight',
                            yaxis='y2',
                            line=dict(color='orange', width=2, dash='dash')
                        )
                    )
                    
                    fig.update_layout(
                        yaxis2=dict(
                            title='Average Weight (kg)',
                            overlaying='y',
                            side='right'
                        )
                    )
                else:
                    # Simple count by hour if weight not available
                    hour_counts = last_mile_df.groupby('hour').size().reset_index(name='count')
                    
                    fig = px.line(
                        hour_counts,
                        x='hour',
                        y='count',
                        title='Delivery Distribution by Hour of Day',
                        labels={'hour': 'Hour of Day', 'count': 'Number of Deliveries'}
                    )
                
                fig.update_xaxes(tickmode='linear', tick0=0, dtick=1)
                st.plotly_chart(fig)
            except:
                st.write("Could not parse datetime from created_date column")

elif analysis_type == "Weight-Distance Analysis":
    st.subheader("Weight-Distance Analysis")
    
    # Ensure required columns exist
    if 'weight' not in last_mile_df.columns or 'kms' not in last_mile_df.columns:
        st.error("Weight-Distance Analysis requires both 'weight' and 'kms' columns in your data.")
        st.stop()
    
    # Scatterplot of weight vs distance
    fig = px.scatter(
        last_mile_df,
        x='weight',
        y='kms',
        color='hub' if 'hub' in last_mile_df.columns else None,
        title='Delivery Weight vs. Distance',
        labels={'weight': 'Weight (kg)', 'kms': 'Distance (km)', 'hub': 'Hub'},
        opacity=0.7,
        size='weight' if 'weight' in last_mile_df.columns else None,
        size_max=15,
        hover_data=['number'] if 'number' in last_mile_df.columns else None
    )
    st.plotly_chart(fig)
    
    # Weight category analysis
    st.subheader("Weight Category Analysis")
    
    # Create weight categories
    weight_bins = [0, 1, 5, 10, 20, 50, 100, float('inf')]
    weight_labels = ['0-1kg', '1-5kg', '5-10kg', '10-20kg', '20-50kg', '50-100kg', '100kg+']
    
    last_mile_df['weight_category'] = pd.cut(
        last_mile_df['weight'], 
        bins=weight_bins, 
        labels=weight_labels,
        right=False
    )
    
    # Display metrics by weight category
    col1, col2 = st.columns(2)
    
    with col1:
        # Count deliveries per weight category
        weight_category_counts = last_mile_df.groupby('weight_category').size().reset_index(name='count')
        
        # Create bar chart for delivery counts
        fig = px.bar(
            weight_category_counts,
            x='weight_category',
            y='count',
            title='Deliveries by Weight Category',
            labels={'weight_category': 'Weight Category', 'count': 'Number of Deliveries'}
        )
        st.plotly_chart(fig)
    
    with col2:
        # Calculate average distance by weight category
        weight_distance = last_mile_df.groupby('weight_category').agg(
            avg_distance=('kms', 'mean'),
            total_distance=('kms', 'sum'),
            delivery_count=('number', 'count')
        ).reset_index()
        
        # Create bar chart for average distance
        fig = px.bar(
            weight_distance,
            x='weight_category',
            y='avg_distance',
            title='Average Delivery Distance by Weight Category',
            labels={'weight_category': 'Weight Category', 'avg_distance': 'Average Distance (km)'}
        )
        st.plotly_chart(fig)
    
    # Customer weight-distance analysis
    if 'customer' in last_mile_df.columns:
        st.subheader("Customer Weight-Distance Analysis")
        
        # Calculate metrics by customer
        customer_metrics = last_mile_df.groupby('customer').agg(
            delivery_count=('number', 'count'),
            total_weight=('weight', 'sum'),
            avg_weight=('weight', 'mean'),
            total_distance=('kms', 'sum'),
            avg_distance=('kms', 'mean')
        ).reset_index()
        
        # Add weight-distance efficiency metrics
        customer_metrics['weight_distance_product'] = customer_metrics['total_weight'] * customer_metrics['avg_distance']
        customer_metrics['kg_per_km'] = customer_metrics['total_weight'] / customer_metrics['total_distance']
        
        # Sort by total weight
        customer_metrics = customer_metrics.sort_values('total_weight', ascending=False)
        
        # Round numerical columns for display
        for col in ['avg_weight', 'avg_distance', 'kg_per_km']:
            customer_metrics[col] = customer_metrics[col].round(2)
        
        # Create bubble chart for customer weight-distance
        fig = px.scatter(
            customer_metrics,
            x='total_distance',
            y='total_weight',
            size='delivery_count',
            color='customer',
            hover_name='customer',
            text='customer',
            title='Customer Weight-Distance Analysis',
            labels={
                'total_distance': 'Total Distance (km)',
                'total_weight': 'Total Weight (kg)',
                'delivery_count': 'Number of Deliveries'
            }
        )
        
        # Add kg/km reference lines
        max_x = customer_metrics['total_distance'].max() * 1.1
        max_y = customer_metrics['total_weight'].max() * 1.1
        
        # Add reference lines for kg/km
        for kg_per_km in [0.5, 1, 2, 5, 10]:
            fig.add_trace(
                go.Scatter(
                    x=[0, max_x],
                    y=[0, max_x * kg_per_km],
                    mode='lines',
                    line=dict(dash='dash', width=1, color='rgba(100,100,100,0.3)'),
                    name=f'{kg_per_km} kg/km',
                    hoverinfo='name'
                )
            )
        
        fig.update_layout(height=600)
        st.plotly_chart(fig)
        
        # Display customer metrics table
        st.subheader("Customer Weight-Distance Metrics")
        st.dataframe(customer_metrics)

elif analysis_type == "Driver Cost Analysis":
    st.subheader("Driver Cost & Efficiency Analysis")
    
    # Check if costs data is available
    if costs_df is None:
        st.error("Please upload the Driver Costs CSV file to perform cost analysis.")
        st.stop()
    
    # Setup tabs for different analysis views
    cost_tabs = st.tabs(["Driver Overview", "Hub Cost Analysis", "Customer Cost Analysis", "Vehicle Analysis"])
    
    with cost_tabs[0]:
        st.subheader("Driver Efficiency Overview")
        
        # Clean and prepare data
        # First, identify the driver ID column
        driver_id_col = None
        for col in costs_df.columns:
            if 'driver_id' in col.lower():
                driver_id_col = col
                break
        
        if driver_id_col is None:
            st.error("Could not find driver_id column in costs data.")
        else:
            # Extract key metrics
            try:
                # Select relevant columns - be flexible about column names
                relevant_cols = [driver_id_col]
                
                # Find name column
                name_col = None
                for col in costs_df.columns:
                    if col.lower() == 'driver':
                        name_col = col
                        break
                
                if name_col:
                    relevant_cols.append(name_col)
                
                # Find vehicle/model columns
                vehicle_col = None
                for col in costs_df.columns:
                    if 'vehicle' in col.lower() or 'model' in col.lower() or 'registration' in col.lower():
                        vehicle_col = col
                        relevant_cols.append(col)
                
                # Find cost column
                cost_col = None
                for col in costs_df.columns:
                    if 'cost' in col.lower() and 'total' in col.lower():
                        cost_col = col
                        relevant_cols.append(col)
                        break
                
                # Find order columns
                order_cols = []
                for col in costs_df.columns:
                    if ('first_mile' in col.lower() or 'last_mile' in col.lower() or 'mid_mile' in col.lower()) and 'total' in col.lower():
                        order_cols.append(col)
                        relevant_cols.append(col)
                
                # Find total orders column
                total_orders_col = None
                for col in costs_df.columns:
                    if 'total_orders' in col.lower():
                        total_orders_col = col
                        relevant_cols.append(col)
                        break
                
                # Find CPO column
                cpo_col = None
                for col in costs_df.columns:
                    if 'cpo' in col.lower() and 'overall' in col.lower():
                        cpo_col = col
                        relevant_cols.append(col)
                        break
                
                # Create driver summary dataframe
                driver_summary = costs_df[relevant_cols].copy()
                
                # Convert cost columns to numeric (they might be strings)
                for col in driver_summary.columns:
                    if 'cost' in col.lower() or 'cpo' in col.lower() or 'total' in col.lower():
                        try:
                            driver_summary[col] = pd.to_numeric(driver_summary[col], errors='coerce')
                        except:
                            st.warning(f"Could not convert {col} to numeric values.")
                
                # Sort by total cost
                if cost_col:
                    driver_summary = driver_summary.sort_values(cost_col, ascending=False)
                
                # Display top drivers by cost
                st.subheader("Top Drivers by Cost")
                st.dataframe(driver_summary.head(10))
                
                # Create visualization of driver costs
                if cost_col and name_col:
                    # Create bar chart for top 15 drivers by cost
                    top_drivers = driver_summary.sort_values(cost_col, ascending=False).head(15)
                    
                    fig = px.bar(
                        top_drivers,
                        x=name_col,
                        y=cost_col,
                        title="Top 15 Drivers by Total Cost",
                        labels={name_col: "Driver", cost_col: "Total Cost"}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig)
                
                # Create efficiency metrics
                if total_orders_col and cost_col:
                    # Calculate orders per rupee
                    driver_summary['orders_per_rupee'] = driver_summary[total_orders_col] / driver_summary[cost_col]
                    
                    # Show most efficient drivers (orders per rupee)
                    st.subheader("Most Efficient Drivers (Orders per Rupee)")
                    efficient_drivers = driver_summary.sort_values('orders_per_rupee', ascending=False).head(10)
                    st.dataframe(efficient_drivers[[name_col, total_orders_col, cost_col, 'orders_per_rupee']])
                    
                    # Handle NaN values in the size parameter
                    driver_summary_clean = driver_summary.copy()
                    if total_orders_col in driver_summary_clean.columns:
                        # Replace NaN values with 0 or min value for size
                        min_size = driver_summary_clean[total_orders_col].min()
                        driver_summary_clean[total_orders_col] = driver_summary_clean[total_orders_col].fillna(min_size if pd.notna(min_size) else 1)
                    
                    # Visualize efficiency
                    fig = px.scatter(
                        driver_summary_clean,
                        x=cost_col,
                        y=total_orders_col,
                        hover_name=name_col if name_col else None,
                        title="Driver Efficiency (Orders vs Cost)",
                        labels={cost_col: "Total Cost", total_orders_col: "Total Orders"},
                        color='orders_per_rupee',
                        color_continuous_scale="Viridis",
                        size=total_orders_col,
                        size_max=20
                    )
                    
                    # Add reference lines for orders per rupee
                    max_cost = driver_summary[cost_col].max() * 1.1
                    
                    for opr in [0.05, 0.1, 0.2, 0.5]:
                        fig.add_trace(
                            go.Scatter(
                                x=[0, max_cost],
                                y=[0, max_cost * opr],
                                mode='lines',
                                line=dict(dash='dash', width=1, color='rgba(100,100,100,0.3)'),
                                name=f'{opr} orders per rupee',
                                hoverinfo='name'
                            )
                        )
                    
                    st.plotly_chart(fig)
            except Exception as e:
                st.error(f"Error processing driver data: {e}")
                st.write("Costs dataframe preview:")
                st.write(costs_df.head())
    
    with cost_tabs[1]:
        st.subheader("Hub Cost Analysis")
        
        # Check if we have both hub information and costs
        if last_mile_df is None:
            st.error("Last mile data required for hub cost analysis.")
        else:
            # Try to identify hub column
            hub_column = None
            if 'hub' in last_mile_df.columns:
                hub_column = 'hub'
            else:
                possible_hub_cols = [col for col in last_mile_df.columns if 'hub' in col.lower() and not col.endswith('_lat') and not col.endswith('_long')]
                hub_column = possible_hub_cols[0] if possible_hub_cols else None
            
            # Try to identify driver column in last_mile_df
            driver_col_lm = None
            for col in last_mile_df.columns:
                if col.lower() == 'driver' or col.lower() == 'driver_id':
                    driver_col_lm = col
                    break
            
            if hub_column and driver_col_lm and driver_id_col:
                try:
                    # Create a mapping from driver to hub
                    driver_hub_map = last_mile_df.groupby(driver_col_lm)[hub_column].agg(lambda x: x.value_counts().index[0]).reset_index()
                    driver_hub_map.columns = [driver_col_lm, 'primary_hub']
                    
                    # Merge costs data with driver-hub mapping
                    # First, ensure driver columns are compatible
                    if driver_col_lm != driver_id_col:
                        # Try to convert one to match the other
                        merged_costs = costs_df.merge(driver_hub_map, left_on=driver_id_col, right_on=driver_col_lm, how='left')
                    else:
                        merged_costs = costs_df.merge(driver_hub_map, on=driver_col_lm, how='left')
                    
                    # Group by hub
                    if cost_col and total_orders_col:
                        hub_costs = merged_costs.groupby('primary_hub').agg(
                            total_cost=(cost_col, 'sum'),
                            total_orders=(total_orders_col, 'sum'),
                            driver_count=(driver_id_col, 'nunique')
                        ).reset_index()
                        
                        # Calculate efficiency metrics
                        hub_costs['cost_per_order'] = hub_costs['total_cost'] / hub_costs['total_orders']
                        hub_costs['orders_per_driver'] = hub_costs['total_orders'] / hub_costs['driver_count']
                        
                        # Sort by total cost
                        hub_costs = hub_costs.sort_values('total_cost', ascending=False)
                        
                        # Display hub cost table
                        st.dataframe(hub_costs)
                        
                        # Create hub cost charts
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Bar chart of total cost by hub
                            fig = px.bar(
                                hub_costs,
                                x='primary_hub',
                                y='total_cost',
                                title="Total Cost by Hub",
                                labels={'primary_hub': "Hub", 'total_cost': "Total Cost"}
                            )
                            fig.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig)
                        
                        with col2:
                            # Bar chart of cost per order by hub
                            fig = px.bar(
                                hub_costs,
                                x='primary_hub',
                                y='cost_per_order',
                                title="Cost per Order by Hub",
                                labels={'primary_hub': "Hub", 'cost_per_order': "Cost per Order"}
                            )
                            fig.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig)
                        
                        # Handle NaN values in the size parameter
                        hub_costs_clean = hub_costs.copy()
                        hub_costs_clean['driver_count'] = hub_costs_clean['driver_count'].fillna(1)
                        
                        # Bubble chart showing the relationship between total orders, drivers, and cost
                        fig = px.scatter(
                            hub_costs_clean,
                            x='total_orders',
                            y='total_cost',
                            size='driver_count',
                            color='cost_per_order',
                            hover_name='primary_hub',
                            title="Hub Efficiency Analysis",
                            labels={
                                'total_orders': "Total Orders", 
                                'total_cost': "Total Cost",
                                'driver_count': "Number of Drivers",
                                'cost_per_order': "Cost per Order"
                            }
                        )
                        st.plotly_chart(fig)
                except Exception as e:
                    st.error(f"Error in hub cost analysis: {e}")
            else:
                st.error("Required columns for hub cost analysis not found.")
    
    with cost_tabs[2]:
        st.subheader("Customer Cost Analysis")
        
        # Check if we have customer information
        if 'customer' not in last_mile_df.columns:
            st.error("Customer column not found in last mile data.")
        elif driver_col_lm is None:
            st.error("Driver column not found in last mile data.")
        else:
            try:
                # Create a mapping from driver to customer
                driver_customer_map = last_mile_df.groupby(driver_col_lm)['customer'].apply(list).reset_index()
                driver_customer_map['customer_count'] = driver_customer_map['customer'].apply(lambda x: len(set(x)))
                driver_customer_map['primary_customer'] = driver_customer_map['customer'].apply(
                    lambda x: max(set(x), key=x.count) if x else None
                )
                
                # Merge with costs data
                if driver_col_lm != driver_id_col:
                    # Try to convert one to match the other
                    merged_costs = costs_df.merge(driver_customer_map[[driver_col_lm, 'primary_customer', 'customer_count']], 
                                                 left_on=driver_id_col, right_on=driver_col_lm, how='left')
                else:
                    merged_costs = costs_df.merge(driver_customer_map[[driver_col_lm, 'primary_customer', 'customer_count']], 
                                                 on=driver_col_lm, how='left')
                
                # Group by customer
                if cost_col and total_orders_col:
                    customer_costs = merged_costs.groupby('primary_customer').agg(
                        total_cost=(cost_col, 'sum'),
                        total_orders=(total_orders_col, 'sum'),
                        driver_count=(driver_id_col, 'nunique')
                    ).reset_index()
                    
                    # Calculate efficiency metrics
                    customer_costs['cost_per_order'] = customer_costs['total_cost'] / customer_costs['total_orders']
                    customer_costs['orders_per_driver'] = customer_costs['total_orders'] / customer_costs['driver_count']
                    
                    # Sort by total cost
                    customer_costs = customer_costs.sort_values('total_cost', ascending=False)
                    
                    # Display customer cost table
                    st.dataframe(customer_costs)
                    
                    # Create customer cost charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Bar chart of total cost by customer
                        fig = px.bar(
                            customer_costs.head(10),
                            x='primary_customer',
                            y='total_cost',
                            title="Total Cost by Customer (Top 10)",
                            labels={'primary_customer': "Customer", 'total_cost': "Total Cost"}
                        )
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig)
                    
                    with col2:
                        # Bar chart of cost per order by customer
                        fig = px.bar(
                            customer_costs.head(10),
                            x='primary_customer',
                            y='cost_per_order',
                            title="Cost per Order by Customer (Top 10)",
                            labels={'primary_customer': "Customer", 'cost_per_order': "Cost per Order"}
                        )
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig)
                    
                    # Handle NaN values in the size parameter
                    customer_costs_clean = customer_costs.copy()
                    customer_costs_clean['driver_count'] = customer_costs_clean['driver_count'].fillna(1)
                    
                    # Bubble chart showing the relationship between total orders, drivers, and cost
                    fig = px.scatter(
                        customer_costs_clean,
                        x='total_orders',
                        y='total_cost',
                        size='driver_count',
                        color='cost_per_order',
                        hover_name='primary_customer',
                        title="Customer Cost Efficiency Analysis",
                        labels={
                            'total_orders': "Total Orders", 
                            'total_cost': "Total Cost",
                            'driver_count': "Number of Drivers",
                            'cost_per_order': "Cost per Order"
                        }
                    )
                    st.plotly_chart(fig)
            except Exception as e:
                st.error(f"Error in customer cost analysis: {e}")
    
    with cost_tabs[3]:
        st.subheader("Vehicle Analysis")
        
        # Identify vehicle/model column
        vehicle_col = None
        for col in costs_df.columns:
            if 'registration' in col.lower() or 'vehicle' in col.lower() or 'model' in col.lower():
                vehicle_col = col
                break
        
        if vehicle_col and cost_col and total_orders_col:
            try:
                # Group by vehicle type
                vehicle_metrics = costs_df.groupby(vehicle_col).agg(
                    total_cost=(cost_col, 'sum'),
                    total_orders=(total_orders_col, 'sum'),
                    driver_count=(driver_id_col, 'nunique')
                ).reset_index()
                
                # Calculate efficiency metrics
                vehicle_metrics['cost_per_order'] = vehicle_metrics['total_cost'] / vehicle_metrics['total_orders']
                vehicle_metrics['orders_per_driver'] = vehicle_metrics['total_orders'] / vehicle_metrics['driver_count']
                vehicle_metrics['cost_per_driver'] = vehicle_metrics['total_cost'] / vehicle_metrics['driver_count']
                
                # Sort by total cost
                vehicle_metrics = vehicle_metrics.sort_values('total_cost', ascending=False)
                
                # Display vehicle metrics table
                st.dataframe(vehicle_metrics)
                
                # Create vehicle comparison charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Bar chart of cost per order by vehicle
                    fig = px.bar(
                        vehicle_metrics,
                        x=vehicle_col,
                        y='cost_per_order',
                        title="Cost per Order by Vehicle Type",
                        labels={vehicle_col: "Vehicle Type", 'cost_per_order': "Cost per Order"}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig)
                
                with col2:
                    # Bar chart of orders per driver by vehicle
                    fig = px.bar(
                        vehicle_metrics,
                        x=vehicle_col,
                        y='orders_per_driver',
                        title="Orders per Driver by Vehicle Type",
                        labels={vehicle_col: "Vehicle Type", 'orders_per_driver': "Orders per Driver"}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig)
                
                # Handle NaN values in the size parameter
                vehicle_metrics_clean = vehicle_metrics.copy()
                vehicle_metrics_clean['driver_count'] = vehicle_metrics_clean['driver_count'].fillna(1)
                
                # Vehicle efficiency bubble chart
                fig = px.scatter(
                    vehicle_metrics_clean,
                    x='cost_per_driver',
                    y='orders_per_driver',
                    size='driver_count',
                    color='cost_per_order',
                    hover_name=vehicle_col,
                    text=vehicle_col,
                    title="Vehicle Type Efficiency Analysis",
                    labels={
                        'cost_per_driver': "Cost per Driver", 
                        'orders_per_driver': "Orders per Driver",
                        'driver_count': "Number of Drivers",
                        'cost_per_order': "Cost per Order"
                    }
                )
                st.plotly_chart(fig)
                
                # Driver efficiency by vehicle type
                if 'model_name' in costs_df.columns and name_col:
                    # Create a scatter plot of driver efficiency by vehicle type
                    costs_df['orders_per_rupee'] = costs_df[total_orders_col] / costs_df[cost_col]
                    
                    fig = px.box(
                        costs_df,
                        x='model_name',
                        y='orders_per_rupee',
                        title="Driver Efficiency Distribution by Vehicle Type",
                        labels={
                            'model_name': "Vehicle Type", 
                            'orders_per_rupee': "Orders per Rupee"
                        }
                    )
                    st.plotly_chart(fig)
                    
                    # Show top drivers for each vehicle type
                    st.subheader("Top Drivers by Vehicle Type")
                    
                    # Get unique vehicle types
                    vehicle_types = costs_df['model_name'].unique()
                    
                    for vehicle in vehicle_types:
                        # Get top 3 most efficient drivers for this vehicle type
                        top_drivers = costs_df[costs_df['model_name'] == vehicle].sort_values('orders_per_rupee', ascending=False).head(3)
                        
                        if len(top_drivers) > 0:
                            st.write(f"**{vehicle}**")
                            st.dataframe(top_drivers[[name_col, total_orders_col, cost_col, 'orders_per_rupee']])
            except Exception as e:
                st.error(f"Error in vehicle analysis: {e}")
        else:
            st.error("Required columns for vehicle analysis not found.")

# Add explanation of the visualizations
with st.expander("About this tool"):
    st.markdown("""
    ## Network Analysis Tool Guide
    
    This tool provides factual visualizations of your logistics network data without making recommendations.
    
    ### Network Components
    - **First Mile**: Pickups from customer locations to micro-warehouses (purple markers, blue dashed lines)
    - **Middle Mile**: Transfers between micro-warehouses (not explicitly shown in current visualization)
    - **Last Mile**: Deliveries from micro-warehouses to end consumers (red markers, green lines)
    - **Micro-warehouses**: Hub locations that store and process shipments (blue markers)
    
    ### Network Flow View
    Visualizes the flow of deliveries from hubs to customers, showing the actual network structure.
    
    ### Density Analysis
    Shows where deliveries are concentrated using a heatmap. Denser areas have more deliveries.
    
    ### Weight-Distance Analysis
    Examines the relationship between package weight and delivery distance. The weight-distance ratio 
    can be used as an efficiency metric.
    
    ### Data Filters
    Use the sidebar filters to focus on specific hubs, customers, or weight ranges.
    """)
