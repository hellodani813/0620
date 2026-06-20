import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(
    page_title="Global Earthquake Tracker",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 대륙별 지진 시각화 대시보드")
st.markdown("USGS(미국 지질조사국) API 데이터를 활용하여 대륙별 지진 데이터를 선택하여 시각화합니다.")

# 2. 최근 24시간 실시간 지진 데이터 로드 함수 (캐싱 5분)
@st.cache_data(ttl=300)
def load_recent_24h_data():
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": "NOW - 1days",
        "minmagnitude": "3.0"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            features = data['features']
            earthquakes = []
            for f in features:
                props = f['properties']
                geom = f['geometry']
                earthquakes.append({
                    "time": pd.to_datetime(props['time'], unit='ms'),
                    "mag": props['mag'],
                    "place": props['place'],
                    "longitude": geom['coordinates'][0],
                    "latitude": geom['coordinates'][1],
                    "depth": geom['coordinates'][2]
                })
            return pd.DataFrame(earthquakes)
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()

# 3. 연도별 데이터 로드 함수 (캐싱 1시간)
@st.cache_data(ttl=3600)
def load_earthquake_data(start_year, end_year, min_mag=2.5):
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": f"{start_year}-01-01",
        "endtime": f"{end_year}-12-31",
        "minmagnitude": str(min_mag)
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            features = data['features']
            earthquakes = []
            for f in features:
                props = f['properties']
                geom = f['geometry']
                earthquakes.append({
                    "time": pd.to_datetime(props['time'], unit='ms'),
                    "mag": props['mag'],
                    "place": props['place'],
                    "longitude": geom['coordinates'][0],
                    "latitude": geom['coordinates'][1],
                    "depth": geom['coordinates'][2]
                })
            return pd.DataFrame(earthquakes)
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()

# 대륙별 위/경도 범위 정의 함수
def filter_by_continent(df, continent):
    if df.empty:
        return df
    
    if continent == "아시아 (Asia)":
        return df[(df['latitude'] >= -10) & (df['latitude'] <= 80) & (df['longitude'] >= 60) & (df['longitude'] <= 150)]
    elif continent == "유럽 (Europe)":
        return df[(df['latitude'] >= 35) & (df['latitude'] <= 75) & (df['longitude'] >= -25) & (df['longitude'] <= 60)]
    elif continent == "아프리카 (Africa)":
        return df[(df['latitude'] >= -35) & (df['latitude'] <= 35) & (df['longitude'] >= -20) & (df['longitude'] <= 50)]
    elif continent == "오세아니아 (Oceania)":
        return df[(df['latitude'] >= -50) & (df['latitude'] <= 0) & (df['longitude'] >= 110) & (df['longitude'] <= 180)]
    elif continent == "북아메리카 (North America)":
        return df[(df['latitude'] >= 7) & (df['latitude'] <= 85) & (df['longitude'] >= -170) & (df['longitude'] <= -50)]
    elif continent == "남아메리카 (South America)":
        return df[(df['latitude'] >= -60) & (df['latitude'] <= 15) & (df['longitude'] >= -90) & (df['longitude'] <= -35)]
    return df

# 4. 실시간 알림
recent_df = load_recent_24h_data()
if not recent_df.empty:
    strong_quakes = recent_df[recent_df['mag'] >= 5.0]
    if not strong_quakes.empty:
        top_quake = strong_quakes.sort_values(by='mag', ascending=False).iloc[0]
        st.error(f"🚨 **실시간 강진 알림 (최근 24시간 내 규모 5.0 이상):** **M {top_quake['mag']:.1f}** 지진 발생! 위치: `{top_quake['place']}`")
    else:
        st.success("✅ 최근 24시간 동안 규모 5.0 이상의 대형 강진은 보고되지 않았습니다.")

st.markdown("---")

# 5. 사이드바 - 조건 선택
st.sidebar.header("🔍 데이터 필터 설정")

continents = ["전세계", "아시아 (Asia)", "유럽 (Europe)", "아프리카 (Africa)", "오세아니아 (Oceania)", "북아메리카 (North America)", "남아메리카 (South America)"]
selected_continent = st.sidebar.selectbox("🗺️ 시각화할 대륙 선택", continents)

current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "📅 조회할 연도를 선택하세요",
    range(current_year, current_year - 10, -1)
)

min_mag = st.sidebar.slider("📉 최소 지진 규모 (Magnitude)", 2.5, 9.0, 4.0, step=0.1)

# 6. 연도별 데이터 로딩 (3단계 로딩 효과)
progress_text = f"🔄 {selected_year}년 데이터를 USGS에서 수집하는 중입니다. 잠시만 기다려주세요..."
with st.spinner(progress_text):
    time.sleep(0.3)
    df = load_earthquake_data(selected_year, selected_year)
    
    st.toast("데이터 다운로드 완료! 선택한 대륙 영역으로 필터링 중...", icon="📊")
    filtered_df = filter_by_continent(df, selected_continent)
    if not filtered_df.empty:
        filtered_df = filtered_df[filtered_df['mag'] >= min_mag]
    
    st.toast("지도를 생성하고 점을 찍는 중입니다...", icon="📍")
    time.sleep(0.2)

# 7. 결과 출력
if not filtered_df.empty:
    st.subheader(f"📊 {selected_year}년 {selected_continent} 지진 통계")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("해당 대륙 발생 건수", f"{len(filtered_df)} 건")
    with col2:
        st.metric("최대 지진 규모", f"M {filtered_df['mag'].max():.1f}")
    with col3:
        st.metric("평균 지진 깊이", f"{filtered_df
