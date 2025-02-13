# 🚕 Trip Earnings Heatmap

## Overview
The **Trip Earnings Heatmap** is a Streamlit-based web application that visualizes per-trip earnings on an interactive map. The application allows users to upload trip data in CSV format, filter by vehicle model, and analyze earnings using a time-based slider with month-year granularity.

## Features
- 📂 Upload trip data via CSV
- 🌍 Interactive Mapbox-based heatmap
- 📅 Month-Year slider to view earnings trends over time
- 🚚 Dynamic vehicle model selection (not preloaded)
- 🔍 Zoom-in, zoom-out, and pan controls for better map navigation
- 🌡️ Continuous color gradient to show earnings intensity (low: green, high: red)

## Installation
To run the application locally, follow these steps:

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/santosh-desai-bh/analytics.git
cd analytics
```

### 2️⃣ Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run the Streamlit App
```bash
streamlit run app.py
```

## Usage
1. **Upload CSV File**: Drag and drop your trip data CSV file.
2. **Select Vehicle Model**: Choose a vehicle model to filter the data.
3. **View Heatmap**: The interactive map updates based on selections.
4. **Adjust Month-Year Slider**: Explore changes in earnings trends over different months.
5. **Zoom & Pan**: Use built-in map controls to focus on specific regions.

## CSV Format Example
Ensure your CSV file has the following columns:

```csv
trip_id,trip_number,contract_type,actual_end_time,total_distance,total_time,driver,vehicle_model,hub,lat,long,gross_pay,start_datetime,end_datetime,trip_count,per_trip_earning
7,345,230,TRIP-2TJXLMA,Fixed,"January 4, 2025, 5:38 AM",10,308.73,Venkatesh | KA52A6456,Canter 24 Feet,T Begur_JT_LH,13.17,77.34,139999.95,"January 1, 2025","January 15, 2025",15,9333.33
```

## Demo
Live demo deployed at https://bh-analytics.streamlit.app/

## License
This project is open-source and available under the MIT License.

