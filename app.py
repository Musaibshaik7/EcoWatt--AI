import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="EcoWatt AI | Renewable Energy Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------ THEME ------------------ #
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
theme = st.session_state.theme
dark_mode = theme == "dark"

bg_color = "#0b1a1f" if dark_mode else "#f6fbff"
text_color = "#e6f6f1" if dark_mode else "#1b1b1b"
subtext_color = "#bcded2" if dark_mode else "#385e6a"

# ------------------ STYLES ------------------ #
st.markdown(f"""
<style>
body {{ background-color: {bg_color}; }}
.title {{
    background: linear-gradient(90deg, #00ffb3, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size:50px;font-weight:900;text-align:center;margin-bottom:-10px;
}}
.subtitle {{ font-size:18px;color:{subtext_color};text-align:center;margin-bottom:20px; }}
.kpi-card {{
    padding:20px;border-radius:15px;font-weight:bold;font-size:16px;text-align:center;
    margin-bottom:15px;background: linear-gradient(90deg, #00ffb3, #00d4ff);color:#000;
    transition: transform 0.3s;
}}
.kpi-card:hover {{ transform: scale(1.05); }}
.kpi-title {{ font-size:14px;color:{subtext_color};margin-bottom:8px; }}
.kpi-value {{ font-size:24px;font-weight:700; }}
.suggestion-card {{
    padding:15px;border-radius:12px;margin-bottom:10px;
    background-color:rgba(255,255,255,0.1);color:{text_color};
    font-weight:bold;transition: transform 0.3s;
}}
.suggestion-card:hover {{ transform: scale(1.02); }}
.footer {{
    text-align:center;color:{subtext_color};margin-top:20px;font-size:14px;
}}
.footer a {{ color:{text_color}; text-decoration:none; font-weight:bold; }}
.section-box {{
    background-color: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 16px;
}}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------ #
st.markdown('<div class="title">⚡ EcoWatt AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Intelligent Renewable Energy Optimization Platform</div>', unsafe_allow_html=True)
st.divider()

# ------------------ SESSION STATE ------------------ #
if "df" not in st.session_state: st.session_state.df = None
if "data_ready" not in st.session_state: st.session_state.data_ready = False
if "latlon" not in st.session_state: st.session_state.latlon = (None, None)
if "scores" not in st.session_state: st.session_state.scores = {}

# ------------------ SIDEBAR ------------------ #
with st.sidebar:
    st.header("⚙️ Controls")
    theme_choice = st.radio("Theme", ["Dark", "Light"], horizontal=True, index=0 if dark_mode else 1)
    st.session_state.theme = "dark" if theme_choice == "Dark" else "light"

    city = st.selectbox("City:", ["Select city...", "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Custom"])
    coords = {
        "Delhi": (28.6139, 77.2090), "Mumbai": (19.0760, 72.8777), "Bangalore": (12.9716, 77.5946),
        "Chennai": (13.0827, 80.2707), "Hyderabad": (17.3850, 78.4867), "Kolkata": (22.5726, 88.3639)
    }
    if city == "Custom":
        lat = st.number_input("Latitude", value=28.6139, format="%.6f")
        lon = st.number_input("Longitude", value=77.2090, format="%.6f")
    elif city == "Select city...":
        lat, lon = None, None
    else:
        lat, lon = coords.get(city)
    st.session_state.latlon = (lat, lon)

    st.markdown("---")
    st.subheader("Forecast & System")
    horizon_days = st.slider("Forecast horizon (days)", 7, 30, 14)
    pr = st.slider("Solar PR", 0.5, 0.9, 0.75)
    system_size_kw = st.slider("Solar system size (kW)", 1, 15, 5)
    turbine_kw = st.selectbox("Wind turbine size (kW)", [1, 2, 3], index=1)

    st.markdown("---")
    st.subheader("Battery & Load")
    battery_capacity_kwh = st.slider("Battery capacity (kWh)", 2, 20, 10)
    battery_round_trip_eff = st.slider("Battery efficiency", 0.7, 0.98, 0.90)
    daily_load_kwh = st.slider("Daily household load (kWh)", 5, 40, 12)

    st.markdown("---")
    st.subheader("Cost")
    tariff_inr_per_kwh = st.slider("Electricity tariff (₹/kWh)", 4.0, 15.0, 8.0)
    solar_om_inr_per_kwh = st.slider("Solar O&M cost (₹/kWh)", 0.0, 2.0, 0.3)
    wind_om_inr_per_kwh = st.slider("Wind O&M cost (₹/kWh)", 0.0, 2.0, 0.5)

# ------------------ CHART OPTIONS ------------------ #
available_tabs = ["Solar", "Wind", "Temperature", "Battery", "Cost", "Map"]
chart_options = st.multiselect("Select charts:", available_tabs, default=available_tabs)

# ------------------ FETCH DATA (CACHED) ------------------ #
@st.cache_data(show_spinner=False)
def fetch_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,wind_speed_10m_max,shortwave_radiation_sum",
        "timezone": "auto"
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# ------------------ ANALYZE ------------------ #
disabled_analyze = (st.session_state.latlon[0] is None or st.session_state.latlon[1] is None)
analyze_clicked = st.button("Analyze Renewable Potential", disabled=disabled_analyze)
if disabled_analyze:
    st.info("Please select a valid city or enter custom coordinates.")

if analyze_clicked and not disabled_analyze:
    with st.spinner("Fetching data..."):
        try:
            data = fetch_data(*st.session_state.latlon)
        except Exception as e:
            st.error(f"API request failed: {e}")
            st.stop()

    daily = data.get("daily")
    if not daily or "time" not in daily:
        st.error("No daily data returned. Try another location.")
        st.stop()

    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "solar_mj_m2": daily.get("shortwave_radiation_sum", [0]*len(daily["time"])),
        "wind_m_s_max": daily.get("wind_speed_10m_max", [0]*len(daily["time"])),
        "temp_max_c": daily.get("temperature_2m_max", [None]*len(daily["time"]))
    })
    df = df.sort_values("date").tail(horizon_days).reset_index(drop=True)

    # Derived metrics
    df["solar_kwh_m2"] = df["solar_mj_m2"] * 0.2778
    df["wind_m_s_avg"] = df["wind_m_s_max"] * 0.6

    avg_solar = df["solar_kwh_m2"].mean()
    avg_wind = df["wind_m_s_avg"].mean()
    df["solar_scale"] = (df["solar_kwh_m2"]/avg_solar).fillna(1.0) if avg_solar > 0 else 1.0
    df["wind_scale"] = (df["wind_m_s_avg"]/avg_wind).fillna(1.0) if avg_wind > 0 else 1.0

    # ------------------ BATTERY SIMULATION (SAFEGUARDED) ------------------ #
    df["solar_gen_kwh"] = df["solar_kwh_m2"] * system_size_kw * pr
    df["wind_gen_kwh"] = df["wind_m_s_avg"] * turbine_kw * 24 * 0.4
    df["total_gen_kwh"] = df["solar_gen_kwh"] + df["wind_gen_kwh"]

    battery = float(battery_capacity_kwh)
    battery_state = []
    grid_use = []
    served_from_battery = []
    for gen in df["total_gen_kwh"]:
        load = float(daily_load_kwh)

        # Charge with excess generation
        excess = max(gen - load, 0.0)
        battery = min(battery + excess * battery_round_trip_eff, float(battery_capacity_kwh))

        # Discharge to meet remaining load if needed
        remaining_load = max(load - gen, 0.0)
        discharge = min(battery, remaining_load)
        battery -= discharge
        served_from_battery.append(discharge)

        # Any unmet load is taken from the grid
        shortage = max(remaining_load - discharge, 0.0)
        grid_use.append(shortage)

        # Safeguard: never negative
        battery = max(battery, 0.0)

        battery_state.append(battery)

    df["battery_kwh"] = battery_state
    df["grid_kwh"] = grid_use
    df["served_from_battery_kwh"] = served_from_battery

    # ------------------ COST & ECO-WATT ------------------ #
    df["solar_cost"] = df["solar_gen_kwh"] * solar_om_inr_per_kwh
    df["wind_cost"] = df["wind_gen_kwh"] * wind_om_inr_per_kwh
    df["grid_cost"] = df["grid_kwh"] * tariff_inr_per_kwh
    df["total_cost"] = df["solar_cost"] + df["wind_cost"] + df["grid_cost"]

    # Simple normalized scores
    solar_score = min((avg_solar/300) * 100, 100) if avg_solar >= 0 else 0
    wind_score = min((avg_wind/10) * 100, 100) if avg_wind >= 0 else 0
    battery_score = min((battery_capacity_kwh/20) * 100, 100)
    eco_score = (solar_score*0.4 + wind_score*0.3 + battery_score*0.3)

    # Summary KPIs
    total_gen = df["total_gen_kwh"].sum()
    total_load = daily_load_kwh * len(df)
    grid_fraction = (df["grid_kwh"].sum() / total_load) * 100 if total_load > 0 else 0
    self_sufficiency = 100 - grid_fraction

    st.session_state.df = df
    st.session_state.data_ready = True
    st.session_state.scores = {
        "Solar": solar_score,
        "Wind": wind_score,
        "Battery": battery_score,
        "EcoWatt": eco_score,
        "Self-sufficiency (%)": self_sufficiency
    }
    st.session_state.summary = {
        "Total generation (kWh)": total_gen,
        "Total load (kWh)": total_load,
        "Grid use (kWh)": df["grid_kwh"].sum(),
        "Battery discharge (kWh)": df["served_from_battery_kwh"].sum(),
        "Total cost (₹)": df["total_cost"].sum()
    }

# ------------------ DISPLAY ------------------ #
def add_watermark(fig):
    fig.update_layout(annotations=[dict(
        text="EcoWatt AI", x=1.0, y=-0.15, xref="paper", yref="paper",
        showarrow=False, font=dict(size=24, color="rgba(0,0,0,0.15)"),
        xanchor="right", yanchor="top")])
    return fig

if st.session_state.data_ready:
    df = st.session_state.df
    left, right = st.columns([2, 1])

    # LEFT: Charts (dynamic tabs)
    with left:
        lat, lon = st.session_state.latlon
        st.subheader(f"📈 Forecast for coordinates: {lat:.4f}, {lon:.4f}")

        # Build tabs dynamically based on selected chart_options
        tabs = st.tabs(chart_options)

        # Map selected tab names to indices for clean rendering
        tab_index = {name: i for i, name in enumerate(chart_options)}

        if "Solar" in chart_options:
            with tabs[tab_index["Solar"]]:
                fig = px.line(df, x="date", y="solar_mj_m2", title="☀️ Daily Solar (MJ/m²)",
                              color_discrete_sequence=["#00ffb3"])
                fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
                st.plotly_chart(add_watermark(fig), use_container_width=True)

        if "Wind" in chart_options:
            with tabs[tab_index["Wind"]]:
                fig = px.line(df, x="date", y="wind_m_s_avg", title="🌬️ Wind Speed (m/s)",
                              color_discrete_sequence=["#00d4ff"])
                fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
                st.plotly_chart(add_watermark(fig), use_container_width=True)

        if "Temperature" in chart_options:
            with tabs[tab_index["Temperature"]]:
                fig = px.line(df, x="date", y="temp_max_c", title="🌡️ Max Temperature (°C)",
                              color_discrete_sequence=["#ffaa00"])
                fig.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
                st.plotly_chart(add_watermark(fig), use_container_width=True)

        if "Battery" in chart_options:
            with tabs[tab_index["Battery"]]:
                st.line_chart(df[["battery_kwh", "grid_kwh", "served_from_battery_kwh"]], use_container_width=True)

        if "Cost" in chart_options:
            with tabs[tab_index["Cost"]]:
                st.line_chart(df[["solar_cost", "wind_cost", "grid_cost", "total_cost"]], use_container_width=True)

        if "Map" in chart_options:
            with tabs[tab_index["Map"]]:
                if None not in (lat, lon):
                    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
                else:
                    st.info("No valid coordinates to display on map.")

        # Export section
        with st.expander("Download results"):
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "ecowatt_results.csv", "text/csv")
            st.write("Summary:")
            st.json(st.session_state.summary)

    # RIGHT: Scores + Suggestions
    with right:
        st.subheader("⚡ EcoWatt Scores")
        for key, val in st.session_state.scores.items():
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-title">{key}</div>'
                f'<div class="kpi-value">{val:.1f}/100</div></div>',
                unsafe_allow_html=True
            )

        st.subheader("💡 Suggestions")
        suggestions = []
        # Solar
        if st.session_state.scores.get("Solar", 0) < 50:
            suggestions.append("Increase solar panel area or use higher-efficiency modules (boost PR).")
        # Wind
        if st.session_state.scores.get("Wind", 0) < 50:
            suggestions.append("Consider higher capacity turbines or check siting for better wind resource.")
        # Battery
        if st.session_state.scores.get("Battery", 0) < 50:
            suggestions.append("Upgrade battery capacity or round-trip efficiency for improved storage.")
        # EcoWatt
        if st.session_state.scores.get("EcoWatt", 0) > 80:
            suggestions.append("Excellent setup! You’re nearing optimal hybrid performance—keep fine-tuning.")

        # Self-sufficiency
        if st.session_state.scores.get("Self-sufficiency (%)", 0) < 60:
            suggestions.append("Reduce grid dependence with demand shifting or incremental capacity increases.")

        if len(suggestions) == 0:
            suggestions.append("System looks balanced—monitor seasonal trends and maintenance for sustained gains.")

        for s in suggestions:
            st.markdown(f'<div class="suggestion-card">{s}</div>', unsafe_allow_html=True)

# ------------------ FOOTER ------------------ #
st.markdown(f"""
<div class="footer">
Made with ❤️ by <b>Musaib Shaik</b> |
<a href="https://github.com/Musaibshaik7" target="_blank">GitHub</a> |
<a href="https://www.linkedin.com/in/musaibshaik7/" target="_blank">LinkedIn</a>
</div>
""", unsafe_allow_html=True)