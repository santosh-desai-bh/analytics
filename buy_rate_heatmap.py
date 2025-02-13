import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

def initialize_session():
    """Initialize the session state with a unique identifier."""
    if 'run_id' not in st.session_state:
        st.session_state.run_id = str(uuid.uuid4())

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

def update_heatmap(df, month_labels, selected_month_label, selected_models, center_lat, center_long):
    """Update the heatmap based on the selected month and vehicle models."""
    selected_month = [k for k, v in month_labels.items() if v == selected_month_label][0]
    filtered_df = df[(df["trip_month"] == selected_month)]
    if selected_models:
        filtered_df = filtered_df[filtered_df["vehicle_model"].isin(selected_models)]
    
    fig = px.scatter_mapbox(
        filtered_df,
        lat="lat",
        lon="long",
        color="per_trip_earning",
        size="per_trip_earning",
        hover_data=["trip_number", "driver", "vehicle_model", "hub", "per_trip_earning"],
        title=f"🚕 Trip Earnings Heatmap - {selected_month_label}",
        color_continuous_scale="viridis",  # Green → Yellow → Purple
        mapbox_style="open-street-map",  # Clearer base map
        zoom=10,  # Dynamic Zoom
        center={"lat": center_lat, "lon": center_long},  # Center Map
        opacity=0.7
    )

    # Enable zoom, pan, and make the map full width
    fig.update_layout(
        height=650,  # Make map bigger
        dragmode="pan",  # Allow dragging
        margin=dict(l=0, r=0, t=40, b=0)  # Remove extra margins
    )

    st.plotly_chart(fig, use_container_width=True, key=f"{selected_month_label}-{st.session_state.run_id}")

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

                # Auto-zoom to focus area
                if not filtered_df.empty:
                    center_lat, center_long = filtered_df["lat"].mean(), filtered_df["long"].mean()

                    # Initial plot
                    update_heatmap(df, month_labels, default_month_label, selected_models, center_lat, center_long)

                    # Move Month-Year Slider BELOW the map
                    selected_month_label = st.select_slider("📅 Select a Month-Year", options=[month_labels[m] for m in unique_months], value=default_month_label)
                    update_heatmap(df, month_labels, selected_month_label, selected_models, center_lat, center_long)

                else:
                    st.warning(f"⚠️ No trips found for {default_month_label} and selected vehicle models.")

        except Exception as e:
            st.error(f"❌ Error generating heatmap: {e}")

if __name__ == "__main__":
    main()
