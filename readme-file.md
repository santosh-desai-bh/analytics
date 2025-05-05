# Bengaluru Logistics Network Analysis Tool

A simple, intuitive tool for analyzing logistics network data on maps to help visualize network flow patterns, delivery density, and weight-distance relationships.

## Features

- **Network Flow Analysis**: Visualize the flow of deliveries from hubs to customers
- **Density Analysis**: See where deliveries are concentrated with heatmaps
- **Weight-Distance Analysis**: Examine the relationship between package weight and delivery distance

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Pip (Python package installer)

### Installation

1. **Clone or download this repository**

2. **Create a virtual environment**

   ```bash
   # Navigate to the project directory
   cd bengaluru-logistics-analyzer

   # Create a virtual environment
   python -m venv venv

   # Activate the virtual environment
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install required packages**

   ```bash
   pip install -r requirements.txt
   ```

   If you don't have a `requirements.txt` file, create one with the following content:

   ```
   streamlit
   pandas
   numpy
   folium
   streamlit-folium
   plotly
   ```

   Or install packages directly:

   ```bash
   pip install streamlit pandas numpy folium streamlit-folium plotly
   ```

### Running the Tool

1. **Activate the virtual environment (if not already activated)**

   ```bash
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Run the Streamlit application**

   ```bash
   streamlit run network_analysis.py
   ```

   This will start the application and open it in your default web browser. If it doesn't open automatically, you can access it at http://localhost:8501

## Using the Tool

1. **Download the required data from Metabase**
   - Last Mile Delivery Data: https://analytics.blowhorn.com/question/3120-if-network-analysis-last-mile?start=2025-05-01&end=2025-05-05
   - Pickups Data: https://analytics.blowhorn.com/question/3116-actual-pickups?start=2025-05-01&end=2025-05-05
   - Costs Data: https://analytics.blowhorn.com/question/3113-if-costs-by-driver

2. **Upload the CSV files to the tool**
   - Use the file uploaders in the sidebar to upload your data

3. **Select an analysis view**
   - Choose between Network Flow, Density Analysis, or Weight-Distance Analysis

4. **Apply filters if needed**
   - Filter by hub, customer, or weight range using the sidebar controls

## Troubleshooting

- **If the map doesn't display properly**: Try refreshing the page
- **If data upload fails**: Ensure your CSV files match the expected format
- **If the application crashes**: Check console output for error messages

## Additional Notes

- The tool works best with Chrome or Firefox browsers
- Large datasets may cause performance issues; consider filtering your data beforehand
- The map visualizations are based on OpenStreetMap data

## Requirements

- streamlit==1.27.0
- pandas==2.0.3
- numpy==1.24.3
- folium==0.14.0
- streamlit-folium==0.13.0
- plotly==5.15.0
