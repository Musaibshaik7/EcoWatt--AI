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

# ------------------ SESSION STATE ------------------ #
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "df" not in st.session_state:
    st.session_state.df = None
if "data_ready" not in st.session_state:
    st.session_state.data_ready = False
if "latlon" not in st.session_state:
    st.session_state.latlon = (None, None)
if "scores" not in st.session_state:
    st.session_state.scores = {}
if "summary" not in st.session_state:
    st.session_state.summary = {}

# ------------------ THEME ------------------ #
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
    text-align:center;color:{subtext_color};margin-top:24px;font-size:14px;
}}
.footer a {{ color:{text_color}; text-decoration:none; font-weight:bold; }}
.credits {{
    margin-top:10px; font-size:13px; color:{subtext_color};
}}
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------ #
st.markdown('<div class="title">⚡ EcoWatt AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Intelligent Renewable Energy Optimization Platform</div>', unsafe_allow_html=True)
st.divider()

# ------------------ SIDEBAR ------------------ #
with st.sidebar:
    st.header("⚙️ Controls")
    theme_choice = st.radio("Theme", ["Dark", "Light"], horizontal=True, index=0 if dark_mode else 1)
    st.session_state.theme = "dark" if theme_choice == "Dark" else "light"
    dark_mode = st.session_state.theme == "dark"
    bg_color = "#0b1a1f" if dark_mode else "#f6fbff"
    text_color = "#e6f6f1" if dark_mode else "#1b1b1b"
    subtext_color = "#bcded2" if dark_mode else "#385e6a"

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

    st.markdown("---")
    st.subheader("Charts")
    available_tabs = ["Solar", "Wind", "Temperature", "Battery", "Cost", "Map"]
    chart_options = st.multiselect("Select charts:", available_tabs, default=available_tabs)

# ------------------ FETCH DATA ------------------ #
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

    # Battery & generation
    df["solar_gen_kwh"] = df["solar_kwh_m2"] * system_size_kw * pr
    df["wind_gen_kwh"] = df["wind_m_s_avg"] * turbine_kw * 24 * 0.4
    df["total_gen_kwh"] = df["solar_gen_kwh"] + df["wind_gen_kwh"]

    battery = float(battery_capacity_kwh)
    battery_state = []
    grid_use = []
    served_from_battery = []
    for gen in df["total_gen_kwh"]:
        load = float(daily_load_kwh)
        excess = max(gen - load, 0.0)
        battery = min(battery + excess * battery_round_trip_eff, float(battery_capacity_kwh))
        remaining_load = max(load - gen, 0.0)
        discharge = min(battery, remaining_load)
        battery -= discharge
        served_from_battery.append(discharge)
        shortage = max(remaining_load - discharge, 0.0)
        grid_use.append(shortage)
        battery = max(battery, 0.0)
        battery_state.append(battery)

    df["battery_kwh"] = battery_state
    df["grid_kwh"] = grid_use
    df["served_from_battery_kwh"] = served_from_battery

    # Costs & scores
    df["solar_cost"] = df["solar_gen_kwh"] * solar_om_inr_per_kwh
    df["wind_cost"] = df["wind_gen_kwh"] * wind_om_inr_per_kwh
    df["grid_cost"] = df["grid_kwh"] * tariff_inr_per_kwh
    df["total_cost"] = df["solar_cost"] + df["wind_cost"] + df["grid_cost"]

    solar_score = min((avg_solar/300) * 100, 100) if avg_solar >= 0 else 0
    wind_score = min((avg_wind/10) * 100, 100) if avg_wind >= 0 else 0
    battery_score = min((battery_capacity_kwh/20) * 100, 100)
    eco_score = (solar_score*0.4 + wind_score*0.3 + battery_score*0.3)

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

# ------------------ CHART HELPERS ------------------ #
def add_watermark(fig):
    color = "rgba(255,255,255,0.15)" if dark_mode else "rgba(0,0,0,0.15)"
    fig.update_layout(annotations=[dict(
        text="EcoWatt AI", x=1.0, y=-0.15, xref="paper", yref="paper",
        showarrow=False, font=dict(size=24, color=color),
        xanchor="right", yanchor="top")])
    return fig

def style_fig(fig):
    axis_color = "#e6f6f1" if dark_mode else "#1b1b1b"
    grid_color = "rgba(255,255,255,0.12)" if dark_mode else "rgba(0,0,0,0.12)"
    fig.update_layout(
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=axis_color),
        xaxis=dict(color=axis_color, gridcolor=grid_color),
        yaxis=dict(color=axis_color, gridcolor=grid_color),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return add_watermark(fig)

# ------------------ DISPLAY ------------------ #
if st.session_state.data_ready:
    df = st.session_state.df
    st.subheader(f"📈 Forecast for coordinates: {st.session_state.latlon[0]:.4f}, {st.session_state.latlon[1]:.4f}")

    # Tabs in center
    tabs = st.tabs(chart_options)
    tab_index = {name: i for i, name in enumerate(chart_options)}

    def get_line_color(name):
        colors = {
            "Solar": "#00ffb3",
            "Wind": "#00d4ff",
            "Temperature": "#ffaa00",
            "Battery": "#00bfff",
            "Cost": "#ff6f00"
        }
        return colors.get(name, "#00ffb3")

    for name in chart_options:
        with tabs[tab_index[name]]:
            y_cols = []
            title = name
            if name == "Solar":
                y_cols = ["solar_mj_m2"]
                title = "☀️ Daily Solar (MJ/m²)"
            elif name == "Wind":
                y_cols = ["wind_m_s_avg"]
                title = "🌬️ Wind Speed (m/s)"
            elif name == "Temperature":
                y_cols = ["temp_max_c"]
                title = "🌡️ Max Temperature (°C)"
            elif name == "Battery":
                y_cols = ["battery_kwh", "grid_kwh", "served_from_battery_kwh"]
                title = "🔋 Battery & Grid Usage (kWh)"
            elif name == "Cost":
                y_cols = ["solar_cost", "wind_cost", "grid_cost", "total_cost"]
                title = "💰 Energy Costs (₹)"
            fig = px.line(df, x="date", y=y_cols, title=title,
                          color_discrete_sequence=[get_line_color(name)]*len(y_cols))
            st.plotly_chart(style_fig(fig), use_container_width=True)

    if "Map" in chart_options:
        with tabs[tab_index["Map"]]:
            lat, lon = st.session_state.latlon
            if None not in (lat, lon):
                st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
            else:
                st.info("No valid coordinates to display on map.")

    # Sidebar: Scores + Suggestions
    st.sidebar.subheader("⚡ EcoWatt Scores")
    for key, val in st.session_state.scores.items():
        st.sidebar.markdown(
            f'<div class="kpi-card"><div class="kpi-title">{key}</div>'
            f'<div class="kpi-value">{val:.1f}/100</div></div>',
            unsafe_allow_html=True
        )

    st.sidebar.subheader("💡 Suggestions")
    suggestions = []
    if st.session_state.scores.get("Solar", 0) < 50:
        suggestions.append("Increase solar panel area or use higher-efficiency modules (boost PR).")
    if st.session_state.scores.get("Wind", 0) < 50:
        suggestions.append("Consider higher capacity turbines or check siting for better wind resource.")
    if st.session_state.scores.get("Battery", 0) < 50:
        suggestions.append("Upgrade battery capacity or round-trip efficiency for improved storage.")
    if st.session_state.scores.get("EcoWatt", 0) > 80:
        suggestions.append("Excellent setup! You’re nearing optimal hybrid performance—keep fine-tuning.")
    if st.session_state.scores.get("Self-sufficiency (%)", 0) < 60:
        suggestions.append("Reduce grid dependence with demand shifting or incremental capacity increases.")
    if len(suggestions) == 0:
        suggestions.append("System looks balanced—monitor seasonal trends and maintenance for sustained gains.")
    for s in suggestions:
        st.sidebar.markdown(f'<div class="suggestion-card">{s}</div>', unsafe_allow_html=True)

    # Export & summary
    with st.expander("Download results"):
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "ecowatt_results.csv", "text/csv")
        st.write("Summary:")
        st.json(st.session_state.summary)

# ------------------ FOOTER ------------------ #
st.markdown(f"""
<div class="footer">
Made with ❤️ by <b>Musaib Shaik</b> |
<a href="https://github.com/Musaibshaik7" target="_blank">GitHub</a> |
<a href="https://www.linkedin.com/in/musaibshaik7/" target="_blank">LinkedIn</a>
<div class="credits">
Data: Open-Meteo API | Charts: Plotly & Streamlit | Build: Python & Streamlit
</div>
</div>
""", unsafe_allow_html=True)
