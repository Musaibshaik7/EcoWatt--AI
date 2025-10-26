import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------------ PAGE CONFIGURATION ------------------ #
st.set_page_config(
    page_title="EcoWatt AI | Renewable Energy Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------ THEME TOGGLE ------------------ #
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

theme = st.session_state.theme
dark_mode = theme == "dark"

# ------------------ STYLES ------------------ #
if dark_mode:
    bg_color = "#0b1a1f"
    text_color = "#e6f6f1"
    subtext_color = "#bcded2"
else:
    bg_color = "#f6fbff"
    text_color = "#1b1b1b"
    subtext_color = "#385e6a"

st.markdown(f"""
<style>
body {{
    background-color: {bg_color};
}}
.title {{
    background: linear-gradient(90deg, #00ffb3, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 50px;
    font-weight: 900;
    text-align:center;
    margin-bottom: -10px;
    transition: transform 0.3s;
}}
.title:hover {{ transform: scale(1.05); }}
.subtitle {{
    font-size: 18px;
    color: {subtext_color};
    text-align:center;
    margin-bottom: 20px;
}}
.kpi {{
    background: {bg_color};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px;
    color: {text_color};
}}
.suggestion-card {{
    padding:20px;
    border-radius:15px;
    font-weight:bold;
    font-size:16px;
    text-align:center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    transition: transform 0.3s;
}}
.suggestion-card:hover {{ transform: scale(1.02); }}
.kpi-title {{
    font-size: 14px;
    color: {subtext_color};
    margin-bottom: 8px;
}}
.kpi-value {{
    font-size: 24px;
    color: {text_color};
    font-weight: 700;
}}
.ecowatt {{
    background: linear-gradient(90deg, #00ffb3, #00d4ff);
    padding:20px;
    border-radius:15px;
    color:#000;
    font-weight:bold;
    font-size:20px;
    text-align:center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}}
.watermark {{
    position: fixed;
    bottom: 16px;
    right: 16px;
    opacity: 0.08;
    font-size: 28px;
    font-weight: 900;
    pointer-events: none;
}}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------ #
st.markdown('<div class="title">⚡ EcoWatt AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Intelligent Renewable Energy Optimization Platform</div>', unsafe_allow_html=True)
st.divider()

# ------------------ SESSION STATE ------------------ #
if "df" not in st.session_state:
    st.session_state.df = None
if "data_ready" not in st.session_state:
    st.session_state.data_ready = False
if "latlon" not in st.session_state:
    st.session_state.latlon = (None, None)

# ------------------ SIDEBAR ------------------ #
with st.sidebar:
    st.header("⚙️ Controls")
    st.markdown("**Select a preset city or enter custom coordinates**")

    theme_choice = st.radio("Theme", ["Dark", "Light"], horizontal=True, index=0 if dark_mode else 1)
    st.session_state.theme = "dark" if theme_choice == "Dark" else "light"

    city = st.selectbox("City:", ["Select city...", "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Custom"])
    coords = {
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777),
        "Bangalore": (12.9716, 77.5946),
        "Chennai": (13.0827, 80.2707),
        "Hyderabad": (17.3850, 78.4867),
        "Kolkata": (22.5726, 88.3639),
    }

    if city == "Custom":
        lat = st.number_input("Latitude", value=28.6139, format="%.6f", help="Enter latitude (-90 to 90)")
        lon = st.number_input("Longitude", value=77.2090, format="%.6f", help="Enter longitude (-180 to 180)")
    elif city == "Select city...":
        lat, lon = None, None
    else:
        lat, lon = coords.get(city)

    st.session_state.latlon = (lat, lon)

    st.markdown("---")
    with st.expander("⚙️ Advanced options"):
        st.checkbox("Show debug API output", key="debug")
        horizon_days = st.slider("Forecast horizon (days)", 7, 30, 14)
        pr = st.slider("Solar performance ratio (PR)", 0.5, 0.9, 0.75)
        area_per_kw = st.slider("Solar area per kW (m²/kW)", 3.0, 8.0, 5.0)
        system_size_kw = st.slider("Solar system size (kW)", 1, 15, 5)
        turbine_kw = st.selectbox("Wind turbine size (kW)", [1,2,3], index=1)
        rotor_diam_m = st.slider("Rotor diameter (m)", 2.0,5.0,2.5)
        cp = st.slider("Power coefficient Cp",0.2,0.5,0.35)
        wind_pr = st.slider("Wind availability factor",0.3,0.9,0.5)
        air_density = 1.225
        st.markdown("---")
        st.subheader("🔋 Battery simulation")
        battery_capacity_kwh = st.slider("Battery capacity (kWh)", 2, 20, 10)
        battery_round_trip_eff = st.slider("Round-trip efficiency",0.7,0.98,0.90)
        daily_load_kwh = st.slider("Daily household load (kWh)",5,40,12)
        st.markdown("---")
        st.subheader("₹ Cost inputs")
        tariff_inr_per_kwh = st.slider("Electricity tariff (₹/kWh)",4.0,15.0,8.0)
        solar_om_inr_per_kwh = st.slider("Solar O&M cost (₹/kWh)",0.0,2.0,0.3)
        wind_om_inr_per_kwh = st.slider("Wind O&M cost (₹/kWh)",0.0,2.0,0.5)
    st.markdown("---")

# ------------------ CHART OPTIONS ------------------ #
chart_options = st.multiselect("Select charts to display:", ["Solar","Wind","Temperature"], default=["Solar","Wind","Temperature"])

# ------------------ HELPER FUNCTION: FETCH DATA ------------------ #
def fetch_data(lat,lon):
    url="https://api.open-meteo.com/v1/forecast"
    params={"latitude":lat,"longitude":lon,"daily":"temperature_2m_max,wind_speed_10m_max,shortwave_radiation_sum","timezone":"auto"}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

# ------------------ ANALYZE BUTTON ------------------ #
disabled_analyze = (st.session_state.latlon[0] is None or st.session_state.latlon[1] is None)
analyze_clicked = st.button("Analyze Renewable Potential", disabled=disabled_analyze)
if disabled_analyze:
    st.info("Please select a valid city or enter custom coordinates.")

if analyze_clicked and not disabled_analyze:
    with st.spinner("Fetching data..."):
        try:
            data = fetch_data(st.session_state.latlon[0], st.session_state.latlon[1])
        except Exception as e:
            st.error(f"API request failed: {e}")
            st.stop()

        if st.session_state.get("debug"):
            st.write("DEBUG:",data)

        daily = data.get("daily")
        if not daily or "time" not in daily:
            st.error("No daily data returned. Try another location.")
            st.stop()

        df = pd.DataFrame({
            "date":pd.to_datetime(daily["time"]),
            "solar_mj_m2":daily.get("shortwave_radiation_sum",[0]*len(daily["time"])),
            "wind_m_s_max":daily.get("wind_speed_10m_max",[0]*len(daily["time"])),
            "temp_max_c":daily.get("temperature_2m_max",[None]*len(daily["time"])),
        })
        df = df.sort_values("date").tail(horizon_days).reset_index(drop=True)
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
        df["solar_kwh_m2"] = df["solar_mj_m2"]*0.2778
        df["wind_m_s_avg"] = df["wind_m_s_max"]*0.6

        # ------------------ SAFE SCALING TO AVOID DIVISION BY ZERO ------------------ #
        avg_solar_kwh_m2 = df["solar_kwh_m2"].mean()
        avg_wind = df["wind_m_s_avg"].mean()
        solar_scale = (df["solar_kwh_m2"]/avg_solar_kwh_m2).fillna(1.0) if avg_solar_kwh_m2>0 else 1.0
        wind_scale = (df["wind_m_s_avg"]/avg_wind).fillna(1.0) if avg_wind>0 else 1.0

        st.session_state.df=df
        st.session_state.data_ready=True

# ------------------ DISPLAY ------------------ #
def add_watermark(fig):
    fig.update_layout(annotations=[dict(
        text="EcoWatt AI",
        x=1.0, y=-0.15, xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=24,color="rgba(0,0,0,0.15)"),
        xanchor="right", yanchor="top"
    )])
    return fig

if st.session_state.data_ready:
    df = st.session_state.df
    lat, lon = st.session_state.latlon
    left,right = st.columns([2,1])

    with left:
        st.subheader(f"📈 Forecast for coordinates: {lat:.4f}, {lon:.4f}")
        tabs = st.tabs(["Solar","Wind","Temperature","Map"])

        # ------------------ SOLAR ------------------ #
        with tabs[0]:
            if "Solar" in chart_options:
                fig_solar = px.line(df,x="date_str",y="solar_mj_m2",
                    title="☀️ Daily Solar (MJ/m²)",color_discrete_sequence=["#00ffb3"])
                fig_solar.update_layout(plot_bgcolor=bg_color,paper_bgcolor=bg_color,font_color=text_color,
                    xaxis=dict(showgrid=False),yaxis=dict(showgrid=False))
                fig_solar.update_traces(mode="lines+markers",hovertemplate='Date: %{x}<br>Solar: %{y:.2f} MJ/m²')
                fig_solar = add_watermark(fig_solar)
                st.plotly_chart(fig_solar,use_container_width=True)

                avg_solar=float(df["solar_mj_m2"].mean())
                solar_score=min((avg_solar/300)*100,100)
                st.markdown(f'<div class="kpi"><div class="kpi-title">Solar potential score</div><div class="kpi-value">{solar_score:.1f}/100</div></div>',unsafe_allow_html=True)
                st.progress(int(solar_score))


