import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import uuid
import branca.colormap as cm

def initialize_session():
    """Initialize the session state with a unique identifier."""
    if 'run_id' not in st.session_state:
        st.session_state.run_id = str(uuid.uuid4())
    if 'fig' not in st.session_state:
        st.session_state.fig = None

@st.cache_data
def load_data(uploaded_file):
    """Load and clean data from the uploaded CSV file."""
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        else:
            st.error("❌ No file uploaded. Please upload a valid CSV file.")
            return None

        df["actual_end_time"] = pd.to_datetime(df["actual_end_time"], errors="coerce")
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["long"] = pd.to_numeric(df["long"], errors="coerce")
        df["per_trip_earning"] = (
            df["per_trip_earning"]
            .astype(str)
            .str.replace(",", "", regex=True)
            .astype(float, errors="ignore")
        )
        df.dropna(subset=["lat", "long", "actual_end_time", "per_trip_earning", "vehicle_model"], inplace=True)
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

    map_center = [center_lat, center_long]
    m = folium.Map(location=map_center, zoom_start=10)

    colormap = cm.LinearColormap(colors=['green', 'orange', 'red'], vmin=filtered_df["per_trip_earning"].min(), vmax=filtered_df["per_trip_earning"].max(), caption='Per Trip Earning')

    for idx, row in filtered_df.iterrows():
        folium.Marker(
            location=[row['lat'], row['long']],
            popup=(
                f"Trip Number: {row['trip_number']}<br>"
                f"Driver: {row['driver']}<br>"
                f"Vehicle Model: {row['vehicle_model']}<br>"
                f"Hub: {row['hub']}<br>"
                f"Per Trip Earning: {row['per_trip_earning']}"
            ),
            icon=folium.Icon(color='blue', icon_color=colormap(row['per_trip_earning'])),
            tooltip=f"Per Trip Earning: {row['per_trip_earning']}"
        ).add_to(m)

    colormap.add_to(m)

    return m

def update_heatmap(m, df, month_labels, selected_month_label, selected_models):
    """Update the heatmap markers based on the selected month and vehicle models."""
    selected_month = [k for k, v in month_labels.items() if v == selected_month_label][0]
    filtered_df = df[(df["trip_month"] == selected_month)]
    if selected_models:
        filtered_df = filtered_df[filtered_df["vehicle_model"].isin(selected_models)]

    return initialize_heatmap(filtered_df, month_labels, selected_month_label, filtered_df["lat"].mean(), filtered_df["long"].mean())

def main():
    """Main function to run the Streamlit app."""
    st.title("🚕 Trip Earnings Heatmap")

    initialize_session()

    uploaded_file = st.file_uploader("Upload Trip Data CSV", type=["csv"])

    df = load_data(uploaded_file)

    if df is not None:
        try:
            df, month_labels, unique_months = process_data(df)

            if len(unique_months) == 0:
                st.warning("⚠️ No valid date data found. Please check your file.")
            else:
                all_vehicle_models = df["vehicle_model"].unique().tolist()
                selected_models = st.multiselect("🚛 Select Vehicle Models", all_vehicle_models)

                default_month = unique_months[-1]
                default_month_label = month_labels[default_month]

                filtered_df = df[(df["trip_month"] == default_month)]
                if selected_models:
                    filtered_df = filtered_df[filtered_df["vehicle_model"].isin(selected_models)]

                if not filtered_df.empty:
                    center_lat, center_long = filtered_df["lat"].mean(), filtered_df["long"].mean()

                    if st.session_state.fig is None:
                        st.session_state.fig = initialize_heatmap(df, month_labels, default_month_label, center_lat, center_long)

                    st_folium(st.session_state.fig, width=700, height=500)

                    selected_month_label = st.select_slider("Trip Month", options=list(month_labels.values()), value=default_month_label)

                    st.session_state.fig = update_heatmap(st.session_state.fig, df, month_labels, selected_month_label, selected_models)
                    st_folium(st.session_state.fig, width=700, height=500)

        except Exception as e:
            st.error(f"❌ Error generating heatmap: {e}")

if __name__ == "__main__":
    main()
