import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title="Global Earthquake Tracker",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 전세계 지진 시각화 대시보드")
st.markdown("USGS(미국 지질조사국) API 데이터를 활용하여 실시간 및 연도별 지진 데이터를 시각화합니다.")

# [신규 기능] 2. 최근 24시간 실시간 지진 데이터 로드 함수 (캐싱 시간 5분으로 짧게 설정)
@st.cache_data(ttl=300)
def load_recent_24h_data():
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": "NOW - 1days",  # 최근 24시간 데이터 요청
        "minmagnitude": "2.5"
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
    except Exception as e:
        return pd.DataFrame()
    return pd.DataFrame()

# 기존 3. 연도별 데이터 로드 함수 (status_code 오류 수정 완료)
@st.cache_data(ttl=3600)
def load_earthquake_data(start_year, end_year):
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": f"{start_year}-01-01",
        "endtime": f"{end_year}-12-31",
        "minmagnitude": "2.5"
    }
    
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
    else:
        st.error("USGS API로부터 데이터를 가져오는데 실패했습니다.")
        return pd.DataFrame()

# ---------------------------------------------------------
# [신규 기능] 4. 실시간 알림 및 최근 24시간 하이라이트 섹션
# ---------------------------------------------------------
recent_df = load_recent_24h_data()

if not recent_df.empty:
    # 최근 24시간 중 규모 5.0 이상의 강진 필터링
    strong_quakes = recent_df[recent_df['mag'] >= 5.0]
    
    if not strong_quakes.empty:
        # 가장 규모가 큰 지진 정보 추출
        top_quake = strong_quakes.sort_values(by='mag', ascending=False).iloc[0]
        st.error(f"🚨 **실시간 강진 알림 (최근 24시간 내 규모 5.0 이상):** "
                 f"**M {top_quake['mag']:.1f}** 지진 발생! 위치: `{top_quake['place']}` "
                 f"({top_quake['time'].strftime('%m-%d %H:%M')} UTC)")
    else:
        st.success("✅ 최근 24시간 동안 규모 5.0 이상의 대형 강진은 보고되지 않았습니다.")

    # 실시간 하이라이트 대시보드 접이식 메뉴(Expander)로 깔끔하게 배치
    with st.expander("⚡ 최근 24시간 글로벌 지진 동향 하이라이트", expanded=True):
        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            st.metric("최근 24시간 발생 건수", f"{len(recent_df)} 건")
        with h_col2:
            max_recent = recent_df.sort_values(by='mag', ascending=False).iloc[0]
            st.metric("24시간 내 최대 규모", f"M {max_recent['mag']:.1f}", help=max_recent['place'])
        with h_col3:
            # 실시간 데이터 수동 갱신 버튼
            if st.button("🔄 실시간 데이터 새로고침"):
                st.cache_data.clear()
                st.rerun()
                
st.markdown("---")

# 5. 사이드바 - 조건 선택
st.sidebar.header("🔍 과거 데이터 필터 설정")

current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "조회할 연도를 선택하세요",
    range(current_year, current_year - 10, -1)
)

min_mag = st.sidebar.slider("최소 지진 규모 (Magnitude)", 2.5, 9.0, 4.5, step=0.1)

# 6. 연도별 데이터 로딩 및 필터링
with st.spinner(f"{selected_year}년 지진 데이터를 불러오는 중..."):
    df = load_earthquake_data(selected_year, selected_year)

if not df.empty:
    filtered_df = df[df['mag'] >= min_mag]
    
    # 7. 주요 지표(Metrics) 표시
    st.subheader(f"📊 {selected_year}년 통계 요약")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 발생 건수", f"{len(filtered_df)} 건")
    with col2:
        st.metric("최대 지진 규모", f"M {filtered_df['mag'].max():.1f}" if not filtered_df.empty else "N/A")
    with col3:
        st.metric("평균 지진 깊이", f"{filtered_df['depth'].mean():.1f} km" if not filtered_df.empty else "N/A")
        
    # 8. 지도 시각화
    st.subheader(f"📍 지진 발생 위치 지도 (규모 {min_mag} 이상)")
    if not filtered_df.empty:
        st.map(filtered_df[['latitude', 'longitude']])
        
        # 9. 상세 데이터 표 테이블
        st.subheader("📋 상세 데이터 리스트")
        st.dataframe(
            filtered_df[['time', 'mag', 'place', 'depth', 'latitude', 'longitude']]
            .sort_values(by='time', ascending=False),
            use_container_width=True
        )
    else:
        st.info("선택한 조건에 해당하는 지진 데이터가 없습니다.")
else:
    st.info("데이터를 불러올 수 없습니다.")
