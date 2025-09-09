import os
import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import boto3

# ----------------------
# MUST be first Streamlit command
# ----------------------
st.set_page_config(page_title="Sofia Air Quality Dashboard", layout="wide")

# ----------------------
# AWS S3 Data Sync (using boto3)
# ----------------------
@st.cache_data(show_spinner="🚀 Syncing latest data from S3...")
def sync_data_from_s3():
    s3 = boto3.client("s3")
    bucket_name = "my-sofia-air-quality"
    prefix = "processed-data/"
    # download into the repo's data/processed folder so the dashboard picks up parquet partitions
    local_folder = os.path.join("..", "data", "processed", "sofia_air_quality_weather")

    os.makedirs(local_folder, exist_ok=True)

    try:
        # List objects in the S3 folder
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if "Contents" not in response:
            return "⚠️ No files found in S3 path."

        # Download each file
        for obj in response["Contents"]:
            s3_key = obj["Key"]
            if s3_key.endswith("/"):
                continue  # skip folders

            # Preserve S3 key structure relative to the prefix when downloading
            try:
                rel_path = os.path.relpath(s3_key, prefix) if s3_key.startswith(prefix) else os.path.basename(s3_key)
            except Exception:
                rel_path = os.path.basename(s3_key)

            local_path = os.path.join(local_folder, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3.download_file(bucket_name, s3_key, local_path)

        return f"Data sync complete! {len(response['Contents'])} files downloaded."
    except Exception as e:
        return f"Sync failed: {str(e)}"

with st.spinner("Fetching latest data..."):
    sync_msg = sync_data_from_s3()
st.success(sync_msg)

# ----------------------
# Load Processed Dataset safely
# ----------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("../data/processed/sofia_air_quality_weather")  # Spark parquet folder
    return df

df = load_data()

# ----------------------
# Dashboard Title
# ----------------------
st.title("🌍 Sofia Air Quality & Weather Dashboard")

# ----------------------
# Sidebar Filters
# ----------------------
st.sidebar.header("Filters")

years = sorted(df["year"].unique())
year_selected = st.sidebar.selectbox("Select Year", years)

months = sorted(df[df["year"] == year_selected]["month"].unique())
month_selected = st.sidebar.selectbox("Select Month", months)

df_filtered = df[(df["year"] == year_selected) & (df["month"] == month_selected)]

stations = st.sidebar.multiselect(
    "Select Locations",
    df_filtered["location"].unique(),
    default=[df_filtered["location"].unique()[0]] if not df_filtered.empty else []
)

metrics = ["avg_PM10", "avg_PM2_5", "avg_temperature", "avg_humidity", "avg_pressure"]

# ----------------------
# Map Visualization
# ----------------------
st.subheader("🗺️ Air Quality Map")

if not df_filtered.empty:
    fig_map = px.scatter_mapbox(
        df_filtered,
        lat="lat",
        lon="lon",
        size="avg_PM2_5",
        color="avg_PM10",
        hover_name="location",
        hover_data={m: ':.2f' for m in metrics},  # format hover with 2 decimals
        color_continuous_scale="RdYlGn_r",
        size_max=30,
        zoom=10,
        title=f"Pollution Map ({year_selected}-{month_selected:02d})"
    )
    fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":30,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("⚠️ No data available for the selected year/month.")

# ----------------------
# Trend Visualization
# ----------------------
st.subheader("📈 Trends Over Time")

metric_selected = st.sidebar.selectbox("Select Metric", metrics)

# initial rangeslider window (days) control
initial_window_days = st.sidebar.number_input("Initial window (days)", min_value=0, max_value=365, value=60, step=1,
                                             help="If >0 the trend chart will initially show the last N days.")

# small tip
st.sidebar.markdown("**Tip:** Use the rangeslider or mouse wheel to zoom horizontally; set a smaller initial window to focus recent data.")

df_trend = df[df["location"].isin(stations)]

if not df_trend.empty:
    # ensure time ordering
    df_trend = df_trend.sort_values("date")
    fig_line = px.line(
        df_trend,
        x="date",
        y=metric_selected,
        color="location",
        markers=True,
        line_shape="linear",
        render_mode="svg",
        color_discrete_sequence=px.colors.qualitative.Dark24,
        title=f"{metric_selected} Trend Over Time")
    # connect gaps and slightly thicken lines for visibility
    fig_line.update_traces(connectgaps=True, line=dict(width=2))
    fig_line.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    # enable rangeslider and pan/zoom interactions for horizontal scrolling
    fig_line.update_xaxes(rangeslider_visible=True)
    # apply initial window focus if requested
    if initial_window_days and initial_window_days > 0:
        try:
            last_date = df_trend['date'].max()
            first_date = last_date - pd.Timedelta(days=int(initial_window_days))
            fig_line.update_xaxes(range=[first_date.isoformat(), last_date.isoformat()])
        except Exception:
            pass
    fig_line.update_layout(dragmode="pan")
    st.plotly_chart(fig_line, use_container_width=True, config={"scrollZoom": True})
else:
    st.info("Select at least one station to see trends.")

# ----------------------
# Insights & Analysis Section
# ----------------------
st.subheader("💡 Insights & Analysis")

# 1️⃣ Summary Statistics
st.markdown("### 📊 Summary Statistics")
if not df_filtered.empty:
    st.dataframe(df_filtered[metrics].describe().round(2))
else:
    st.info("Select a year and month to see summary statistics.")

# 2️⃣ Monthly / Seasonal Trends
st.markdown("### 📈 Monthly Pollution Trends")
monthly_avg = df.groupby("month")[["avg_PM10", "avg_PM2_5"]].mean().reset_index()
try:
    import calendar
    # ensure months are sorted numerically and show month names
    monthly_avg = monthly_avg.sort_values("month")
    monthly_avg["month_name"] = monthly_avg["month"].apply(lambda m: calendar.month_abbr[int(m)])
    x_col = "month_name"
except Exception:
    x_col = "month"

fig_monthly = px.line(
    monthly_avg,
    x=x_col,
    y=["avg_PM10", "avg_PM2_5"],
    markers=True,
    color_discrete_sequence=px.colors.qualitative.T10,
    labels={"value":"Pollution Level (µg/m³)", x_col:"Month"},
    title="Average Monthly Pollution Levels"
)
fig_monthly.update_traces(line=dict(width=2))
fig_monthly.update_traces(connectgaps=True, line=dict(width=2))
fig_monthly.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
fig_monthly.update_xaxes(rangeslider_visible=True)
fig_monthly.update_layout(dragmode="pan")
st.plotly_chart(fig_monthly, use_container_width=True, config={"scrollZoom": True})

# 3️⃣ Weather vs Pollution Correlation
st.markdown("### 🌡️ Weather vs Pollution Correlation")
corr = df[["avg_PM10", "avg_PM2_5", "avg_temperature", "avg_humidity", "avg_pressure"]].corr()
st.dataframe(corr.round(2))

fig_corr, ax = plt.subplots(figsize=(6,5))
sns.heatmap(corr, annot=True, cmap="RdYlGn_r", ax=ax)
st.pyplot(fig_corr)

st.markdown(
    "🔹 Observations:\n"
    "- Positive correlation indicates both metrics increase together.\n"
    "- Negative correlation indicates inverse relationships.\n"
    "- Example: PM2.5 tends to rise when humidity is lower."
)

# 4️⃣ Top Polluted Locations
st.markdown("### 🏭 Top Polluted Locations")
top_stations = df.groupby("location")[["avg_PM10", "avg_PM2_5"]].mean().sort_values("avg_PM2_5", ascending=False).head(5)
st.table(top_stations.round(2))

st.markdown(
    "🔹 Observations:\n"
    "- Locations at the top of the table consistently have the highest pollution.\n"
    "- Focus for policy or interventions could be in these areas."
)

# 5️⃣ Dynamic Seasonal Insights
st.markdown("### 📌 Seasonal & Location Insights")
st.markdown("#### Current Problem We Are Addressing")
st.markdown(
    "Air pollution in Sofia fluctuates across months and locations, impacting public health and quality of life. "
    "This section highlights seasonal trends, identifies the most polluted areas, and shows how weather affects pollution levels."
)

if not df.empty:
    month_pm25_avg = df.groupby("month")["avg_PM2_5"].mean()
    highest_pm25_month = month_pm25_avg.idxmax()
    lowest_pm25_month = month_pm25_avg.idxmin()

    location_pm25_avg = df.groupby("location")["avg_PM2_5"].mean()
    worst_location = location_pm25_avg.idxmax()
    best_location = location_pm25_avg.idxmin()

    insights = [
        f"🌡️ The highest average PM2.5 pollution occurs in month {highest_pm25_month}, while the lowest occurs in {lowest_pm25_month}.",
        f"🏭 Among all monitoring stations, {worst_location} is the most polluted, while {best_location} shows the cleanest air on average."
    ]

    corr_pm25_temp = df["avg_PM2_5"].corr(df["avg_temperature"])
    corr_pm25_hum = df["avg_PM2_5"].corr(df["avg_humidity"])

    if corr_pm25_temp < -0.2:
        insights.append("❄️ PM2.5 tends to increase during colder temperatures.")
    if corr_pm25_hum < -0.2:
        insights.append("💧 PM2.5 tends to increase when humidity is low.")

    for insight in insights:
        st.markdown(f"- {insight}")

    st.markdown("### Narrative")
    narrative = (
        f"During the year, the air quality in Sofia shows clear seasonal patterns. "
        f"The worst air quality is observed in {highest_pm25_month}, while the cleanest month is {lowest_pm25_month}. "
        f"The station at {worst_location} consistently records the highest PM2.5 levels, whereas {best_location} remains relatively clean. "
        f"Weather conditions also play a role: lower temperatures and reduced humidity are associated with higher PM2.5 concentrations. "
        f"This information helps prioritize public health interventions and policy actions to mitigate pollution hotspots."
    )
    st.markdown(narrative)
else:
    st.info("No data available to generate seasonal insights.")
