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

# 2. USGS API 데이터 로드 함수 (캐싱 적용으로 속도 향상)
@st.cache_data(ttl=3600)  # 1시간마다 캐시 갱신
def load_earthquake_data(start_year, end_year):
    # API 호출용 URL 설정 (지진 규모 2.5 이상 데이터 추출)
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": f"{start_year}-01-01",
        "endtime": f"{end_year}-12-31",
        "minmagnitude": "2.5"
    }
    
    response = requests.get(url, params=params)
    if response.status_value == 200:
        data = response.json()
        
        # GeoJSON 데이터를 판다스 데이터프레임으로 변환
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

# 3. 사이드바 - 조건 선택
st.sidebar.header("🔍 필터 설정")

# 연도 선택 (USGS API 특성상 너무 먼 과거는 데이터 양이 방대하므로 최근 10년 제공)
current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "조회할 연도를 선택하세요",
    range(current_year, current_year - 10, -1)
)

# 지진 규모(Magnitude) 필터 추가
min_mag = st.sidebar.slider("최소 지진 규모 (Magnitude)", 2.5, 9.0, 4.5, step=0.1)

# 4. 데이터 로딩 및 필터링
with st.spinner(f"{selected_year}년 지진 데이터를 불러오는 중..."):
    df = load_earthquake_data(selected_year, selected_year)

if not df.empty:
    # 사용자가 선택한 최소 규모로 데이터 필터링
    filtered_df = df[df['mag'] >= min_mag]
    
    # 5. 주요 지표(Metrics) 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 발생 건수", f"{len(filtered_df)} 건")
    with col2:
        st.metric("최대 지진 규모", f"M {filtered_df['mag'].max():.1f}" if not filtered_df.empty else "N/A")
    with col3:
        st.metric("평균 지진 깊이", f"{filtered_df['depth'].mean():.1f} km" if not filtered_df.empty else "N/A")
        
    st.markdown("---")
    
    # 6. 지도 시각화
    st.subheader(f"📍 {selected_year}년 지진 발생 위치 (규모 {min_mag} 이상)")
    
    # Streamlit 내장 지도는 'latitude'와 'longitude' 컬럼명이 있으면 자동으로 매핑됩니다.
    if not filtered_df.empty:
        st.map(filtered_df[['latitude', 'longitude']])
        
        # 7. 상세 데이터 표 테이블
        st.subheader("📊 상세 데이터 리스트")
        st.dataframe(
            filtered_df[['time', 'mag', 'place', 'depth', 'latitude', 'longitude']]
            .sort_values(by='time', ascending=False),
            use_container_width=True
        )
    else:
        st.info("선택한 조건에 해당하는 지진 데이터가 없습니다.")
else:
    st.info("데이터를 불러올 수 없습니다.")
