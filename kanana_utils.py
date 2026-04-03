import os
import re
import base64
import json
import wave
from dotenv import load_dotenv
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
from openai import OpenAI

load_dotenv()
api_key = os.getenv("KANANA_API_KEY")
if not api_key:
    raise ValueError("KANANA_API_KEY 환경변수가 설정되지 않았습니다.")

client = OpenAI(
    api_key=api_key,
    base_url="https://kanana-o.a2s-endpoint.kr-central-2.kakaocloud.com/v1"
)

SAMPLE_RATE = 24000

EMOTION_VOICE_STYLE = {
    "기쁨": "매우 신나고 빠르게, 높은 톤으로 통통 튀게",
    "삐짐": "퉁명스럽고 짧게 끊어서, 약간 낮은 톤으로",
    "당황": "빠르고 당황스럽게, 높은 톤으로 허둥지둥",
    "평온": "차분하고 부드럽게, 보통 속도로",
    "간절": "애원하듯 간절하게, 끝을 올리며",
}

VALID_EMOTIONS = ["기쁨", "삐짐", "당황", "평온", "간절"]
VALID_SPECIES  = ["dog", "cat", "other"]


# ── 프롬프트 ──────────────────────────────────────────────────────────────────

def get_analysis_prompt() -> str:
    """
    JSON 대신 [섹션] 형식 사용.
    Kanana-o가 JSON은 거부하지만 섹션 형식은 잘 따름.
    예시는 의도적으로 실내·장난감 상황으로 설정 → 복붙 방지.
    """
    return """\
너는 반려동물 전문 행동 분석가야. 사진을 보고 아래 형식으로만 답해.
형식 외 다른 텍스트는 절대 출력하지 마.

[분석]
제3자 관찰 시점으로 2~3문장 서술. 종류·자세·배경·감정 상태 포함. 확신 있는 어조로.

[감정]
기쁨 또는 삐짐 또는 당황 또는 평온 또는 간절

[동물]
dog 또는 cat 또는 other

[대사]
반려동물 1인칭으로 2~3문장. 강아지는 모든 문장을 반드시 "멍!"으로 끝낼 것. 고양이는 반드시 "냥."으로 끝낼 것.
강아지 예시: 장난감 어딨멍! 빨리 던져줘멍! 같이 놀자멍!
고양이 예시: 저 상자 내 거냥. 들어가고 싶냥. 비켜줘냥."""


# ── 이미지 전처리 ────────────────────────────────────────────────────────────

def preprocess_image(image_input) -> str:
    if isinstance(image_input, bytes):
        img = Image.open(BytesIO(image_input))
    else:
        img = Image.open(image_input)

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    img.thumbnail((800, 800), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ── 섹션 파싱 ────────────────────────────────────────────────────────────────

def parse_section_response(text: str) -> dict:
    """
    [분석] / [감정] / [동물] / [대사] 섹션 추출.
    각 섹션에서 "예시:" 행은 제거.
    """
    result = {}
    pattern = r'\[([^\]]+)\]\s*\n?(.*?)(?=\n\[|\Z)'
    for match in re.finditer(pattern, text.strip(), re.DOTALL):
        key   = match.group(1).strip()
        value = match.group(2).strip()
        # "예시:" 로 시작하는 줄 제거
        lines = [l for l in value.splitlines() if not re.match(r'\s*(강아지\s*예시|고양이\s*예시|예시)', l)]
        result[key] = ' '.join(l.strip() for l in lines if l.strip())
    return result


# ── pet_speech 후처리 ────────────────────────────────────────────────────────

def _enforce_pet_ending(text: str, species: str) -> str:
    """
    문장 끝에 멍!/냥. 강제 적용.
    모델이 "멍! 문장멍!" 처럼 앞에도 붙이는 패턴 정리.
    """
    ending = "멍!" if species == "dog" else ("냥." if species == "cat" else None)
    if not ending:
        return text

    # 맨 앞 "멍! " / "냥. " 제거 (모델 형식 오류)
    text = re.sub(r'^(멍!|냥\.)\s*', '', text.strip())

    # 문장 분리: ending 기준으로 분리 후 재조합
    token = "멍!" if species == "dog" else "냥."
    parts = text.split(token)
    sentences = []
    for p in parts:
        p = p.strip()
        if p:
            # 남은 문장부호 제거 후 ending 재부착
            p = re.sub(r'[.!?。]+$', '', p).strip()
            if p:
                sentences.append(p + token)

    if not sentences:
        return text

    return ' '.join(sentences[:3])  # 최대 3문장


# ── 키워드 기반 추정 ──────────────────────────────────────────────────────────

def _detect_species(text: str) -> str:
    if any(w in text for w in ["강아지", "개", "dog", "포메", "푸들", "말티즈", "비숑", "코커", "시츄"]):
        return "dog"
    if any(w in text for w in ["고양이", "냥이", "cat", "페르시안", "먼치킨", "삼색"]):
        return "cat"
    return "other"


def _detect_emotion(text: str) -> str:
    for emotion, words in {
        "기쁨": ["기쁨", "행복", "신남", "즐거", "활발", "좋아", "반가"],
        "삐짐": ["삐짐", "화", "짜증", "싫", "불만", "시무룩"],
        "당황": ["당황", "놀람", "깜짝", "경계", "긴장"],
        "간절": ["간절", "간청", "애원", "바라"],
    }.items():
        if any(w in text for w in words):
            return emotion
    return "평온"


def _default_speech(species: str) -> str:
    return {
        "dog": "주인이랑 있으니 너무 좋멍! 오늘도 행복한 하루멍! 간식 줘멍!",
        "cat": "오늘도 귀찮냥. 그냥 있고 싶냥. 내버려 두냥.",
    }.get(species, "오늘도 좋은 하루야!")


# ── 이미지 분석 (단일 호출) ───────────────────────────────────────────────────

def analyze_pet_image(base64_image: str) -> Tuple[str, str, str, str]:
    """
    이미지 분석 → (ai_analysis, pet_speech, emotion, species)

    [설계 원칙]
    - API 호출 1회만: 이미지 분석 + 대사 생성을 한 번에 처리.
      (2차 호출 제거 → quota 절약)
    - JSON 대신 [섹션] 형식: Kanana-o가 JSON은 거부하지만 섹션 형식은 잘 따름.
    - stream=False: 누적 텍스트 중복 버그 방지.
    """
    response = client.chat.completions.create(
        model="kanana-o",
        messages=[
            {"role": "system", "content": get_analysis_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": base64_image}},
                    {"type": "text", "text": "이 반려동물 사진을 분석해줘."}
                ]
            }
        ],
        # stream=False (기본값): 누적 텍스트 중복 방지
    )

    full_text = (response.choices[0].message.content or "").strip()

    print("\n" + "=" * 60)
    print("[DEBUG] raw response:")
    print(full_text)
    print("=" * 60 + "\n")

    # 기본값
    ai_analysis = "반려동물의 사진입니다."
    pet_speech  = ""
    emotion     = "평온"
    species     = "other"

    # ── 섹션 파싱 시도 ────────────────────────────────────────────────────────
    try:
        sections = parse_section_response(full_text)
        print(f"[DEBUG] 파싱된 섹션: {list(sections.keys())}\n")

        raw_analysis = sections.get("분석", "")
        raw_speech   = sections.get("대사", "")
        raw_emotion  = sections.get("감정", "").strip()
        raw_species  = sections.get("동물", "").strip().lower()

        if raw_analysis:
            ai_analysis = raw_analysis
        if raw_emotion in VALID_EMOTIONS:
            emotion = raw_emotion
        for s in VALID_SPECIES:
            if s in raw_species:
                species = s
                break

        # pet_speech: 섹션에서 추출 후 ending 강제 적용
        if raw_speech:
            pet_speech = _enforce_pet_ending(raw_speech, species)
            print(f"[DEBUG] pet_speech (섹션): {pet_speech}\n")

    except Exception as e:
        print(f"[DEBUG] 섹션 파싱 실패: {e}\n")

    # ── 섹션 파싱 실패 시 폴백 ────────────────────────────────────────────────
    if not ai_analysis or ai_analysis == "반려동물의 사진입니다.":
        if full_text:
            ai_analysis = re.sub(r'[ \t]+', ' ', full_text).strip()
        species = _detect_species(full_text)
        emotion = _detect_emotion(full_text)

    # pet_speech 최종 안전망 (2차 API 호출 없이 기본값 사용)
    if not pet_speech:
        pet_speech = _default_speech(species)
        print(f"[DEBUG] pet_speech (기본값): {pet_speech}\n")

    return ai_analysis, pet_speech, emotion, species


# ── 음성 생성 ────────────────────────────────────────────────────────────────

def generate_pet_voice(pet_speech: str, emotion: str, species: str) -> Optional[bytes]:
    """
    pet_speech만 TTS 변환.
    오디오 청크 수신은 스트리밍이 효율적이므로 stream=True 유지.
    """
    voice_direction = EMOTION_VOICE_STYLE.get(emotion, "보통 속도로 자연스럽게")
    species_voice   = {
        "dog": "활발하고 에너지 넘치는 어린 강아지 목소리. 높은 음정. 문장마다 생동감 있게.",
        "cat": "약간 콧소리 섞인 도도한 고양이 목소리. 중간 음정. 살짝 느릿하고 우아하게.",
    }.get(species, "귀엽고 통통 튀는 작은 동물 목소리.")

    tts_system = f"""\
너는 반려동물 성우야. 주어진 텍스트를 {species_voice}
말하는 속도: {voice_direction}.
규칙:
- 텍스트를 한 글자도 바꾸지 말고 그대로 읽을 것
- 절대 설명하거나 다른 말을 추가하지 말 것
- 감탄사(멍!, 냥.)는 특히 강조해서 생동감 있게 읽을 것"""

    try:
        response = client.chat.completions.create(
            model="kanana-o",
            messages=[
                {"role": "system", "content": tts_system},
                {"role": "user", "content": pet_speech}
            ],
            modalities=["text", "audio"],
            stream=True,
        )

        audio_chunks = []
        for chunk in response:
            raw     = chunk.model_dump()
            choices = raw.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            audio = delta.get("audio")
            if audio is None:
                continue

            audio_b64 = None
            if isinstance(audio, str):
                audio_b64 = audio
            elif isinstance(audio, dict):
                audio_b64 = audio.get("data") or audio.get("audio")

            if isinstance(audio_b64, str) and audio_b64:
                try:
                    pcm = base64.b64decode(audio_b64, validate=True)
                    if pcm:
                        audio_chunks.append(pcm)
                except Exception:
                    pass

        if not audio_chunks:
            return None

        all_frames = b"".join(audio_chunks)
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(all_frames)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        print(f"[DEBUG] 음성 생성 실패: {e}")
        return None


# ── 진입점 ───────────────────────────────────────────────────────────────────

def get_pet_mind(image_input) -> Tuple[str, str, str, str, Optional[bytes]]:
    """
    사진 → 분석 + 음성 (API 총 2회: 분석 1회 + TTS 1회)
    Returns: (ai_analysis, pet_speech, emotion, species, audio_data)
    """
    base64_image    = preprocess_image(image_input)
    base64_data_url = f"data:image/jpeg;base64,{base64_image}"

    ai_analysis, pet_speech, emotion, species = analyze_pet_image(base64_data_url)
    audio_data = generate_pet_voice(pet_speech, emotion, species)

    return ai_analysis, pet_speech, emotion, species, audio_data
