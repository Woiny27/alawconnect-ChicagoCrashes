import streamlit as st
import pandas as pd
import requests
import asyncio
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Chicago Crashes Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🚗 Chicago Crashes Dashboard")
st.markdown("Real-time crash data analysis with AI-powered risk detection")

# Sidebar
st.sidebar.header("Dashboard Controls")
data_source = st.sidebar.radio(
    "Data Source",
    ["Chicago Open Data", "Upload CSV"]
)

# API Configuration
API_BASE_URL = "http://localhost:8000"
CHICAGO_API = "https://data.cityofchicago.org/resource/85ca-t3if.json"

# Helper functions
@st.cache_data
def fetch_chicago_crashes(limit: int = 50):
    """Fetch crash data from Chicago Open Data API."""
    try:
        response = requests.get(CHICAGO_API, params={"$limit": limit})
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def analyze_crash_risk(record_id: str, magnitude: float):
    """Call the risk analysis API endpoint."""
    try:
        payload = {
            "record_id": record_id,
            "magnitude": magnitude,
            "latitude": 41.8781,
            "longitude": -87.6298,
            "timestamp": int(datetime.now().timestamp())
        }
        response = requests.post(
            f"{API_BASE_URL}/risk/analyze/usgs",
            json=payload
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Error calling risk API: {e}")
        return None

# Main content
if data_source == "Chicago Open Data":
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Recent Crash Data")
    
    with col2:
        limit = st.number_input("Limit", min_value=5, max_value=500, value=50)
    
    # Fetch data
    with st.spinner("Fetching crash data..."):
        df = fetch_chicago_crashes(limit)
    
    if df is not None and len(df) > 0:
        st.success(f"✅ Loaded {len(df)} crash records")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Crashes", len(df))
        
        with col2:
            total_injuries = df['injuries_total'].sum() if 'injuries_total' in df.columns else 0
            st.metric("Total Injuries", int(total_injuries))
        
        with col3:
            fatal_injuries = df['injuries_fatal'].sum() if 'injuries_fatal' in df.columns else 0
            st.metric("Fatal Injuries", int(fatal_injuries))
        
        with col4:
            avg_damage = df['damage'].value_counts().index[0] if 'damage' in df.columns else "N/A"
            st.metric("Most Common Damage", str(avg_damage)[:20])
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["Data Table", "Statistics", "Risk Analysis", "Map"])
        
        with tab1:
            st.subheader("Crash Records")
            
            # Select columns to display
            display_cols = st.multiselect(
                "Select columns to display",
                df.columns.tolist(),
                default=['crash_date', 'street_name', 'crash_type', 'most_severe_injury', 'weather_condition']
            )
            
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True)
        
        with tab2:
            st.subheader("Crash Statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'crash_type' in df.columns:
                    st.write("**Crash Types**")
                    crash_types = df['crash_type'].value_counts().head(10)
                    st.bar_chart(crash_types)
            
            with col2:
                if 'weather_condition' in df.columns:
                    st.write("**Weather Conditions**")
                    weather = df['weather_condition'].value_counts().head(10)
                    st.bar_chart(weather)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'prim_contributory_cause' in df.columns:
                    st.write("**Contributing Causes**")
                    causes = df['prim_contributory_cause'].value_counts().head(10)
                    st.bar_chart(causes)
            
            with col2:
                if 'most_severe_injury' in df.columns:
                    st.write("**Injury Severity**")
                    injuries = df['most_severe_injury'].value_counts()
                    st.bar_chart(injuries)
        
        with tab3:
            st.subheader("AI Risk Analysis")
            
            st.info("Select a crash record to analyze its risk score with our AI system")
            
            if 'crash_record_id' in df.columns and 'injuries_total' in df.columns:
                selected_idx = st.selectbox(
                    "Select a crash to analyze",
                    range(len(df)),
                    format_func=lambda i: f"Crash {i+1}: {df.iloc[i].get('street_name', 'N/A')}"
                )
                
                if selected_idx is not None:
                    crash = df.iloc[selected_idx]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Crash Details**")
                        st.write(f"Date: {crash.get('crash_date', 'N/A')}")
                        st.write(f"Location: {crash.get('street_name', 'N/A')}")
                        st.write(f"Type: {crash.get('crash_type', 'N/A')}")
                        st.write(f"Injuries: {crash.get('injuries_total', 0)}")
                    
                    with col2:
                        if st.button("🤖 Analyze Risk", key="analyze_btn"):
                            with st.spinner("Analyzing risk..."):
                                # Use injuries as a proxy for severity (0-10 scale)
                                severity_score = min(float(crash.get('injuries_total', 0)) / 10.0, 10.0)
                                
                                analysis = analyze_crash_risk(
                                    crash.get('crash_record_id', 'unknown'),
                                    severity_score
                                )
                                
                                if analysis:
                                    st.success("✅ Analysis Complete")
                                    st.json(analysis)
                                else:
                                    st.warning("⚠️ Risk API unavailable. Ensure the API server is running on port 8000.")
        
        with tab4:
            st.subheader("Crash Locations Map")
            
            if 'latitude' in df.columns and 'longitude' in df.columns:
                # Prepare map data
                map_data = df[['latitude', 'longitude']].dropna()
                map_data.columns = ['lat', 'lon']
                
                st.write("Map data types:", map_data.dtypes)
                
                st.map(map_data, zoom=10)
                
                st.write(f"📍 {len(map_data)} crash locations plotted")
            else:
                st.warning("Location data not available")
    
    else:
        st.error("No data available")

else:  # Upload CSV
    st.subheader("📁 Upload Crash Data")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded {len(df)} records")
        st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    **ChicagoCrashes Dashboard** | Powered by FastAPI + Streamlit
    
    Data source: [Chicago Open Data Portal](https://data.cityofchicago.org/)
    """
)
