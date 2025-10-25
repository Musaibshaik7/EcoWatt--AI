import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ---------- Page Config ----------
st.set_page_config(
    page_title="EcoWatt AI | Renewable Energy Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styles ----------
st.markdown("""
<style>
.title {
    background: linear-gradient(90deg, #00ffb3, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 50px;
    font-weight: 900;
    text-align:center;
    margin-bottom: -10px;
}
.subtitle {
    font-size: 18px;
    color: #bcded2;
    text-align:center;
    margin-bottom: 20px;
}
.metric-container {
    padding: 10px;
    background-color: #0b1a1f;
    border-radius: 10px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="title">⚡ EcoWatt AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Intelligent Renewable Energy Optimization Platform</div>', unsafe_allow_html=True)
st.divider()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Controls")
    st.markdown("**Select a preset city or enter custom coordinates**")
    city = st.selectbox("City:", ["Select city...", "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Custom"])
    if city == "Custom":
        lat = st.number_input("Latitude", value=28.6139, format="%.6f")
        lon = st.number_input("Longitude", value=77.2090, format="%.6f")
    else:
        coords = {
            "Delhi": (28.6139, 77.2090),
            "Mumbai": (19.0760, 72.8777),
            "Bangalore": (12.9716, 77.5946),
            "Chennai": (13.0827, 80.2707),
            "Hyderabad": (17.3850, 78.4867),
            "Kolkata": (22.5726, 88.3639)
        }
        lat, lon = coords.get(city, (28.6139, 77.2090))
    st.markdown("---")
    st.checkbox("Show Debug API Output", key="debug")
    st.markdown("---")
    st.markdown("**Tip:** Click 'Analyze Renewable Potential' to generate charts. ✅")
    st.markdown("---")

# ---------- Helper Function ----------
def fetch_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,wind_speed_10m_max,shortwave_radiation_sum",
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# ---------- Main ----------
if st.button("Analyze Renewable Potential"):
    with st.spinner("Fetching data..."):
        try:
            data = fetch_data(lat, lon)
        except Exception as e:
            st.error(f"API request failed: {e}")
            st.stop()

        if st.session_state.get("debug"):
            st.write("DEBUG:", data)

        daily = data.get("daily")
        if not daily or "time" not in daily:
            st.error("No daily data returned. Try another location.")
            st.stop()

        df = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "solar": daily.get("shortwave_radiation_sum", [0]*len(daily["time"])),
            "wind": daily.get("wind_speed_10m_max", [0]*len(daily["time"])),
            "temp_max": daily.get("temperature_2m_max", [None]*len(daily["time"]))
        })
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

        # ---------- Layout ----------
        left, right = st.columns([2, 1])

        # ----------- Left: Charts -----------
        with left:
            st.subheader(f"📈 Forecast for coordinates: {lat:.4f}, {lon:.4f}")

            # Solar Chart
            fig_solar = px.line(df, x="date_str", y="solar",
                                title="☀️ Daily Solar (MJ/m²)",
                                color_discrete_sequence=["#00ffb3"])
            fig_solar.update_layout(plot_bgcolor='#0b1a1f', paper_bgcolor='#0b1a1f', font_color='#e6f6f1', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            fig_solar.update_traces(mode='lines+markers', hovertemplate='Date: %{x}<br>Solar: %{y:.2f} MJ/m²')
            st.plotly_chart(fig_solar, use_container_width=True)

            # Wind Chart
            fig_wind = px.line(df, x="date_str", y="wind",
                               title="💨 Daily Max Wind Speed (m/s)",
                               color_discrete_sequence=["#0077ff"])
            fig_wind.update_layout(plot_bgcolor='#0b1a1f', paper_bgcolor='#0b1a1f', font_color='#e6f6f1', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            fig_wind.update_traces(mode='lines+markers', hovertemplate='Date: %{x}<br>Wind: %{y:.2f} m/s')
            st.plotly_chart(fig_wind, use_container_width=True)

            # Temperature Chart
            fig_temp = px.line(df, x="date_str", y="temp_max",
                               title="🌡️ Max Daily Temperature (°C)",
                               color_discrete_sequence=["#ffaa00"])
            fig_temp.update_layout(plot_bgcolor='#0b1a1f', paper_bgcolor='#0b1a1f', font_color='#e6f6f1', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            fig_temp.update_traces(mode='lines+markers', hovertemplate='Date: %{x}<br>Temp: %{y:.2f} °C')
            st.plotly_chart(fig_temp, use_container_width=True)

            # CSV download
            csv = df[["date_str", "solar", "wind", "temp_max"]].to_csv(index=False)
            st.download_button("⬇️ Download CSV", csv, file_name="ecowatt_forecast.csv", mime="text/csv")

        # ----------- Right: AI Suggestion & Metrics -----------
        with right:
            st.subheader("🧠 AI Suggestion & Summary")
            avg_solar = df["solar"].mean()
            avg_wind = df["wind"].mean()
            avg_temp = df["temp_max"].dropna().mean() if df["temp_max"].notna().any() else None
                        # ---------- EcoWatt Score ----------
            # Normalize solar and wind into a 0–100 index
            solar_score = min((avg_solar / 300) * 100, 100)   # assuming 300 MJ/m² is excellent
            wind_score = min((avg_wind / 12) * 100, 100)      # assuming 12 m/s is excellent
            eco_watt_score = (0.6 * solar_score) + (0.4 * wind_score)  # weighted blend

            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(90deg, #00ffb3, #00d4ff);
                    padding:20px;
                    border-radius:15px;
                    color:#000;
                    font-weight:bold;
                    font-size:20px;
                    text-align:center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                ">
                ⚡ EcoWatt Score: {eco_watt_score:.1f}/100
                </div>
                """,
                unsafe_allow_html=True
            )
            # Metrics in styled containers
            st.markdown(f'<div class="metric-container">Avg. Solar (MJ/m²): {avg_solar:.1f}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-container">Avg. Wind (m/s): {avg_wind:.2f}</div>', unsafe_allow_html=True)
            if avg_temp is not None:
                st.markdown(f'<div class="metric-container">Avg. Max Temp (°C): {avg_temp:.1f}</div>', unsafe_allow_html=True)

            # Colored suggestion card
            if avg_solar > 250:
                suggestion_color = "#00ffb3"
                suggestion_text = "🌞 High solar potential — recommend solar PV installation."
                text_color = "#000"
            elif avg_wind > 6:
                suggestion_color = "#0077ff"
                suggestion_text = "💨 Strong wind potential — consider wind turbines."
                text_color = "#fff"
            else:
                suggestion_color = "#ffaa00"
                suggestion_text = "🔋 Hybrid solar-wind with storage is recommended."
                text_color = "#000"

            st.markdown(
                f"""
                <div style="
                    background-color:{suggestion_color};
                    padding:20px;
                    border-radius:15px;
                    color:{text_color};
                    font-weight:bold;
                    font-size:16px;
                    text-align:center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                    transition: transform 0.3s;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                {suggestion_text}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("### 🌱 Sustainability Impact")
            st.markdown("""
            - Reduces carbon footprint
            - Data-driven renewable decisions
            - Supports UN SDG 7 & 13
            """)

        # Last updated timestamp
        st.markdown(f"<div style='color:#9fbfb4;font-size:13px;'>Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>", unsafe_allow_html=True)
