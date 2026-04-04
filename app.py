import streamlit as st
from kanana_utils import get_pet_mind

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
        font-weight: bold;
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
        padding: 8px 18px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.05em;
        margin-bottom: 16px;
    }
    .section-label {
        font-size: 0.78em;
        font-weight: bold;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .analysis-box {
        background-color: #F8F9FA;
        border: 1px solid #DEE2E6;
        border-radius: 10px;
        padding: 16px 20px;
        font-size: 0.97em;
        color: #444;
        line-height: 1.8;
        margin-bottom: 20px;
    }
    .speech-bubble {
        background-color: #FFF3F3;
        border: 2px solid #FF6B6B;
        border-radius: 16px;
        padding: 18px 22px;
        font-size: 1.18em;
        font-weight: 600;
        color: #222;
        line-height: 1.9;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

EMOTION_EMOJI = {
    "기쁨": "😊",
    "삐짐": "😾",
    "당황": "😲",
    "평온": "😸",
    "간절": "🥺",
}

st.markdown("<div class='main-title'>🐾 무슨 생각 하냥?</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>반려동물의 마음을 읽는 AI</div>", unsafe_allow_html=True)

st.markdown("""
---
### ✨ 기능
- 📸 **사진 분석**: 종, 자세, 표정으로 심리상태 파악
- 🧠 **감정 인식**: 기쁨 / 삐짐 / 당황 / 평온 / 간절
- 💬 **말풍선**: 개는 `~멍!`, 고양이는 `~냥.` 말투
- 🔊 **음성**: 반려동물의 말을 음성으로 들려줌

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
        st.image(image_bytes, caption="📸 선택된 사진", width="stretch")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(image_bytes, width=300)

    if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
        with st.spinner("반려동물의 마음을 읽는 중..."):
            try:
                ai_analysis, pet_speech, emotion, species, audio_data = get_pet_mind(image_bytes)

                st.session_state.current_result = {
                    "ai_analysis": ai_analysis,
                    "pet_speech": pet_speech,
                    "emotion": emotion,
                    "species": species,
                    "audio": audio_data,
                }

                st.session_state.analysis_history.append({
                    "pet_speech": pet_speech,
                    "emotion": emotion,
                    "species": species,
                })

                st.success("분석 완료!", icon="✅")

            except ValueError as e:
                st.error(f"입력 오류: {str(e)}")
            except RuntimeError as e:
                st.error(f"API 오류: {str(e)}")
                st.info("🔑 API 키를 확인해주세요.")
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")

# ── 결과 표시 ──────────────────────────────────────────
if st.session_state.current_result is not None:
    result = st.session_state.current_result

    st.markdown("---")
    st.markdown("### 🧠 분석 결과")

    emoji = EMOTION_EMOJI.get(result["emotion"], "😺")
    st.markdown(
        f"<div class='emotion-tag'>{emoji} {result['emotion']}</div>",
        unsafe_allow_html=True
    )

    # AI 분석 (서술형 문장)
    st.markdown("<div class='section-label'>AI 분석</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='analysis-box'>🔍 {result['ai_analysis']}</div>",
        unsafe_allow_html=True
    )

    # 말풍선 (pet_speech만)
    st.markdown("<div class='section-label'>반려동물의 말</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='speech-bubble'>🐾 {result['pet_speech']}</div>",
        unsafe_allow_html=True
    )

    # 음성 (pet_speech 기준)
    st.markdown("### 🔊 음성")
    if result["audio"] is not None:
        st.audio(result["audio"], format="audio/wav")
    else:
        st.info("음성 생성이 일시적으로 불가능합니다.")

# ── 히스토리 (사이드바) ────────────────────────────────
if st.session_state.analysis_history:
    with st.sidebar:
        st.markdown("### 📜 최근 분석")
        for record in st.session_state.analysis_history[-5:]:
            sp_emoji = {"dog": "🐶", "cat": "🐱"}.get(record["species"], "🐾")
            em_emoji = EMOTION_EMOJI.get(record["emotion"], "😺")
            with st.expander(f"{sp_emoji} {em_emoji} {record['emotion']}"):
                st.write(record["pet_speech"])

        if st.button("초기화", use_container_width=True):
            st.session_state.analysis_history = []
            st.session_state.current_result = None
            st.rerun()

st.markdown("""
---
<div style='text-align: center; color: #999; font-size: 0.9em;'>
  <p>🐾 무슨 생각 하냥? v2.2</p>
  <p>Powered by Kanana-o API & Streamlit</p>
</div>
""", unsafe_allow_html=True)
