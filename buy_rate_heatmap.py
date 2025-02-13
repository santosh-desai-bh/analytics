import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid

def initialize_session():
    """Initialize the session state with a unique identifier."""
    if 'run_id' not in st.session_state:
        st.session_state.run_id = str(uuid.uuid4())
    if 'fig' not in st.session_state:
        st.session_state.fig = None

def load_data(uploaded_file):
    """Load and clean data from the uploaded CSV file."""
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        else:
            st.error("❌ No file uploaded. Please upload a valid CSV file.")
            return None

        # Convert datetime columns
        for col in ["actual_end_time", "start_datetime", "end_datetime"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")

        # Convert lat, long, per_trip_earning to numeric
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["long"] = pd.to_numeric(df["long"], errors="coerce")
        df["per_trip_earning"] = (
            df["per_trip_earning"]
            .astype(str)
            .str.replace(",", "", regex=True)
            .astype(float, errors="ignore")
        )

        # Drop rows with missing critical values
        df.dropna(subset=["lat", "long", "actual_end_time", "per_trip_earning", "vehicle_model"], inplace=True)

        # Ensure per_trip_earning values are non-negative
        df = df[df["per_trip_earning"] >= 0]

        return df

    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return None

def process_data(df):
    """Process the data to extract month-year and initialize filters."""
    df["trip_month"] = df["actual_end_time"].dt.to_period("M")
    month_labels = {m: m.strftime("%b-%Y") for m in df["actual_end_time"].dt.to_period("M").unique()}
    unique_months = sorted(month_labels.keys())
    return df, month_labels, unique_months

def initialize_heatmap(df, month_labels, selected_month_label, center_lat, center_long):
    """Initialize the heatmap based on the selected month."""
    selected_month = [k for k, v in month_labels.items() if v == selected_month_label][0]
    filtered_df = df[(df["trip_month"] == selected_month)]
    
    fig = go.Figure(go.Scattermapbox(
        lat=filtered_df["lat"],
        lon=filtered_df["long"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=10,  # Fixed size
            color=filtered_df["per_trip_earning"],
            colorscale='Viridis',
            showscale=True
        ),
        text=filtered_df.apply(lambda row: f"Trip Number: {row['trip_number']}<br>Driver: {row['driver']}<br>Vehicle Model: {row['vehicle_model']}<br>Hub: {row['hub']}<br>Per Trip Earning: {row['per_trip_earning']}", axis=1)
    ))

    fig.update_layout(
        title=f"🚕 Trip Earnings Heatmap - {selected_month_label}",
        mapbox_style="open-street-map",
        mapbox=dict(
            center=dict(lat=center_lat, lon=center_long),
            zoom=10
        ),
        height=650,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

def update_heatmap(fig, df, month_labels, selected_month_label, selected_models, earnings_range):
    """Update the heatmap markers based on the selected month, vehicle models, and earnings range."""
    selected_month = [k for k, v in month_labels.items() if v == selected_month_label][0]
    filtered_df = df[(df["trip_month"] == selected_month)]
    if selected_models:
        filtered_df = filtered_df[filtered_df["vehicle_model"].isin(selected_models)]
    
    # Filter by earnings range
    filtered_df = filtered_df[(filtered_df["per_trip_earning"] >= earnings_range[0]) & (filtered_df["per_trip_earning"] <= earnings_range[1])]
    
    fig.data[0].lat = filtered_df["lat"]
    fig.data[0].lon = filtered_df["long"]
    fig.data[0].marker.color = filtered_df["per_trip_earning"]
    fig.data[0].text = filtered_df.apply(lambda row: f"Trip Number: {row['trip_number']}<br>Driver: {row['driver']}<br>Vehicle Model: {row['vehicle_model']}<br>Hub: {row['hub']}<br>Per Trip Earning: {row['per_trip_earning']}", axis=1)
    fig.update_layout(title=f"🚕 Trip Earnings Heatmap - {selected_month_label}")

    return fig

def main():
    """Main function to run the Streamlit app."""
    st.title("🚕 Trip Earnings Heatmap")

    # Initialize a unique session identifier
    initialize_session()

    # File uploader
    uploaded_file = st.file_uploader("Upload Trip Data CSV", type=["csv"])

    # Load Data
    df = load_data(uploaded_file)

    if df is not None:
        try:
            # Process Data
            df, month_labels, unique_months = process_data(df)

            if len(unique_months) == 0:
                st.warning("⚠️ No valid date data found. Please check your file.")
            else:
                # Vehicle Model Filter (Initially empty)
                all_vehicle_models = df["vehicle_model"].unique().tolist()
                selected_models = st.multiselect("🚛 Select Vehicle Models", all_vehicle_models)

                # Default to the latest available month
                default_month = unique_months[-1]
                default_month_label = month_labels[default_month]

                # Initial Filter
                filtered_df = df[(df["trip_month"] == default_month)]
                if selected_models:
                    filtered_df = filtered_df[filtered_df["vehicle_model"].isin(selected_models)]

                # Earnings range slider
                min_earning = df["per_trip_earning"].min()
                max_earning = df["per_trip_earning"].max()
                earnings_range = st.slider("Select Earnings Range", min_value=min_earning, max_value=max_earning, value=(min_earning, max_earning))

                # Auto-zoom to focus area
                if not filtered_df.empty:
                    center_lat, center_long = filtered_df["lat"].mean(), filtered_df["long"].mean()

                    # Initialize plot if not already initialized
                    if st.session_state.fig is None:
                        st.session_state.fig = initialize_heatmap(df, month_labels, default_month_label, center_lat, center_long)
                    
                    # Display plot
                    plotly_chart = st.plotly_chart(st.session_state.fig, use_container_width=True, key=f"init-{st.session_state.run_id}")

                    # Trip month slider
                    selected_month_label = st.select_slider("Trip Month", options=list(month_labels.values()), value=default_month_label)

                    # Update heatmap based on selected month, vehicle models, and earnings range
                    st.session_state.fig = update_heatmap(st.session_state.fig, df, month_labels, selected_month_label, selected_models, earnings_range)
                    plotly_chart.plotly_chart(st.session_state.fig, use_container_width=True, key=f"update-{selected_month_label}-{st.session_state.run_id}")

        except Exception as e:
            st.error(f"❌ Error generating heatmap: {e}")

if __name__ == "__main__":
    main()
