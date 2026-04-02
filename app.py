import streamlit as st
from kanana_utils import get_pet_mind
import io

st.set_page_config(
    page_title="🐾 무슨 생각 하냥?",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-title {
        text-align: center;
        font-size: 2.5em;
        color: #FF6B6B;
        margin-bottom: 10px;
    }
    
    .subtitle {
        text-align: center;
        font-size: 1.1em;
        color: #666;
        margin-bottom: 30px;
    }
    
    .emotion-tag {
        display: inline-block;
        background-color: #FFE5E5;
        color: #FF6B6B;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: bold;
        margin: 5px 5px 5px 0;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🐾 무슨 생각 하냥?</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>반려동물의 마음을 읽는 AI</div>", unsafe_allow_html=True)

st.markdown("""
---
### ✨ 기능
- 📸 사진 분석: 표정, 자세, 주변 환경 분석
- 🧠 감정 인식: 5가지 감정 태그 중 현재 심리상태 판별
- 🎤 음성 생성: AI 페르소나로 1인칭 한국어 대사
- 🔊 음성 재생: 감정에 맞는 톤으로 즉시 청음
---
""")

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

if "current_result" not in st.session_state:
    st.session_state.current_result = None


st.markdown("### 📤 반려동물 사진을 올려주세요")

uploaded_file = st.file_uploader(
    "JPG, PNG 형식",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed"
)

if uploaded_file is not None:
    image_bytes = uploaded_file.read()
    
    with st.sidebar:
        st.image(image_bytes, caption="📸 선택된 사진")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(image_bytes, width=300)
    
    if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
        with st.spinner("반려동물의 마음을 읽는 중..."):
            try:
                analysis_text, emotion_tag, audio_data = get_pet_mind(image_bytes)
                
                st.session_state.current_result = {
                    "text": analysis_text,
                    "emotion": emotion_tag,
                    "audio": audio_data
                }
                
                st.session_state.analysis_history.append({
                    "text": analysis_text,
                    "emotion": emotion_tag
                })
                
                st.success("분석 완료!", icon="✅")
            
            except ValueError as e:
                st.error(f"입력 오류: {str(e)}")
            
            except RuntimeError as e:
                st.error(f"API 오류: {str(e)}")
                st.info("API 키를 확인해주세요.")
            
            except Exception as e:
                st.error(f"오류: {str(e)}")


if st.session_state.current_result is not None:
    result = st.session_state.current_result
    
    st.markdown("---")
    st.markdown("### 🧠 분석 결과")
    
    emotion_emoji = {
        "기쁨": "😊",
        "삐짐": "😾",
        "당황": "😲",
        "평온": "😸",
        "간절": "🥺"
    }
    
    emoji = emotion_emoji.get(result["emotion"], "😺")
    st.markdown(f"<div class='emotion-tag'>{emoji} {result['emotion']}</div>", 
               unsafe_allow_html=True)
    
    with st.chat_message("assistant", avatar="🐾"):
        st.markdown(result["text"])
    
    if result["audio"] is not None:
        st.markdown("### 🎤 음성")
        st.audio(result["audio"], format="audio/mp3")
    else:
        st.info("음성 생성이 일시적으로 불가능합니다.")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 복사", use_container_width=True):
            st.write(f"감정: {result['emotion']}\n{result['text']}")
    
    with col2:
        if st.button("❤️ 저장", use_container_width=True):
            st.info("저장되었습니다!")


if st.session_state.analysis_history:
    with st.sidebar:
        st.markdown("### 📜 최근 분석")
        
        for idx, record in enumerate(st.session_state.analysis_history[-5:], 1):
            with st.expander(f"{record['emotion']}"):
                st.write(record['text'])
        
        if st.button("초기화", use_container_width=True):
            st.session_state.analysis_history = []
            st.rerun()


st.markdown("""
---
<div style='text-align: center; color: #999; font-size: 0.9em;'>
  <p>🐾 무슨 생각 하냥? v1.0</p>
  <p>Powered by Kanana-o API & Streamlit</p>
</div>
""", unsafe_allow_html=True)