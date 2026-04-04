import os
import re
import base64
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


# ── 이미지 전처리 ─────────────────────────────────────────────────────────────

def preprocess_image(image_input) -> str:
    if isinstance(image_input, bytes):
        img = Image.open(BytesIO(image_input))
    else:
        img = Image.open(image_input)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── 키워드 추정 ───────────────────────────────────────────────────────────────

def _detect_species(text: str) -> str:
    if any(w in text for w in ["강아지", "개", "dog", "포메", "푸들", "말티즈", "비숑", "시츄", "웰시", "골든"]):
        return "dog"
    if any(w in text for w in ["고양이", "냥이", "cat", "페르시안", "먼치킨"]):
        return "cat"
    return "other"


def _detect_emotion(text: str) -> str:
    for emotion, words in {
        "기쁨": ["기쁨", "행복", "신남", "즐거", "활발", "좋아", "반가", "신나"],
        "삐짐": ["삐짐", "화", "짜증", "싫", "불만", "시무룩"],
        "당황": ["당황", "놀람", "깜짝", "경계", "긴장"],
        "간절": ["간절", "간청", "애원", "바라"],
    }.items():
        if any(w in text for w in words):
            return emotion
    return "평온"


def _default_speech(species: str) -> str:
    return {
        "dog": "주인이랑 있으니 너무 좋멍! 오늘도 행복한 하루멍!",
        "cat": "오늘도 귀찮냥. 그냥 있고 싶냥.",
    }.get(species, "오늘도 좋은 하루야!")


def _enforce_pet_ending(text: str, species: str) -> str:
    ending = "멍!" if species == "dog" else ("냥." if species == "cat" else None)
    if not ending:
        return text
    text = re.sub(r'^(멍!|냥\.)\s*', '', text.strip())
    parts = text.split(ending)
    sentences = []
    for p in parts:
        p = p.strip()
        if p:
            p = re.sub(r'[.!?。]+$', '', p).strip()
            if p:
                sentences.append(p + ending)
    return ' '.join(sentences[:3]) if sentences else text


# ── Call 1: 이미지 → ai_analysis 텍스트 ──────────────────────────────────────

def _analyze(base64_url: str) -> Tuple[str, str, str]:
    """
    이미지 → ai_analysis(설명), species, emotion.
    설명만 받음. pet_speech는 Call 2에서 생성.
    stream=False, 오디오 없음.
    """
    response = client.chat.completions.create(
        model="kanana-o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": base64_url}},
                    {
                        "type": "text",
                        "text": (
                            "이 사진 속 반려동물의 외형·자세·표정·배경을 "
                            "2~3문장으로 자세히 설명해줘. "
                            "수의사 주의사항이나 거절 멘트는 쓰지 마."
                        )
                    }
                ]
            }
        ],
    )

    ai_analysis = re.sub(
        r'[ \t]+', ' ',
        (response.choices[0].message.content or "").strip()
    )

    print("\n" + "=" * 60)
    print("[DEBUG] ai_analysis:")
    print(ai_analysis)
    print("=" * 60 + "\n")

    species = _detect_species(ai_analysis)
    emotion = _detect_emotion(ai_analysis)
    return ai_analysis, species, emotion


# ── Call 2: pet_speech 텍스트 + 오디오 동시 생성 ──────────────────────────────

def _speech_and_audio(
    ai_analysis: str, species: str, emotion: str
) -> Tuple[str, Optional[bytes]]:
    """
    pet_speech 텍스트와 오디오를 하나의 응답에서 동시에 생성.

    [핵심 원칙]
    텍스트(UI 표시)와 오디오는 같은 모델 응답에서 나옴 → 항상 일치.
    - 텍스트 스트림: 누적 전송이므로 last_text = content (마지막 값만)
    - 오디오 스트림: 증분 청크 → 누적

    few-shot으로 멍!/냥. 형식을 유도하고,
    ai_analysis를 컨텍스트로 전달해 사진 상황에 맞는 대사 생성.
    """
    ending     = "멍!" if species == "dog" else ("냥." if species == "cat" else "!")
    species_kr = {"dog": "강아지", "cat": "고양이"}.get(species, "동물")
    emotion_tone = {
        "기쁨": "매우 신나고 활발하게",
        "삐짐": "퉁명스럽고 낮은 톤으로",
        "당황": "빠르고 허둥지둥하게",
        "평온": "차분하고 부드럽게",
        "간절": "애원하듯 간절하게",
    }.get(emotion, "자연스럽게")

    # few-shot: 다른 종류·감정 예시 → 복붙 방지
    few_q = f"강아지가 삐진 상태야. 강아지 시점으로 멍!으로 끝나는 2문장만:"
    few_a = "밥이 왜 이리 늦어멍! 너무 배고프멍!"

    actual_q = (
        f"상황: {ai_analysis}\n"
        f"{species_kr}가 지금 {emotion} 상태야. {emotion_tone}. "
        f"{species_kr} 시점으로 {ending}로 끝나는 2문장만 써줘."
    )

    try:
        response = client.chat.completions.create(
            model="kanana-o",
            messages=[
                {"role": "user",      "content": few_q},
                {"role": "assistant", "content": few_a},
                {"role": "user",      "content": actual_q},
            ],
            modalities=["text", "audio"],
            stream=True,
        )

        last_text    = ""
        audio_chunks = []

        for chunk in response:
            raw     = chunk.model_dump()
            choices = raw.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}

            # 텍스트: Kanana-o 누적 전송 → 마지막 값으로 교체
            content = delta.get("content")
            if isinstance(content, str) and content:
                last_text = content

            # 오디오: 증분 → 누적
            audio = delta.get("audio")
            if audio is not None:
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

        pet_speech_raw = last_text.strip()
        print(f"[DEBUG] pet_speech 원본: {pet_speech_raw}")

        # 텍스트와 오디오는 같은 응답 → 항상 일치
        pet_speech = _enforce_pet_ending(pet_speech_raw, species) if pet_speech_raw else _default_speech(species)
        print(f"[DEBUG] pet_speech 최종: {pet_speech}\n")

        audio_data = None
        if audio_chunks:
            all_frames = b"".join(audio_chunks)
            buf = BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(all_frames)
            buf.seek(0)
            audio_data = buf.getvalue()

        return pet_speech, audio_data

    except Exception as e:
        print(f"[DEBUG] speech+audio 실패: {e}")
        return _default_speech(species), None


# ── 진입점 ───────────────────────────────────────────────────────────────────

def get_pet_mind(image_input) -> Tuple[str, str, str, str, Optional[bytes]]:
    """
    API 2회:
      Call 1 (_analyze)        : 이미지 → ai_analysis, species, emotion
      Call 2 (_speech_and_audio): ai_analysis 컨텍스트 → pet_speech + 오디오

    UI 표시 텍스트(pet_speech)와 오디오가 Call 2의 동일 응답에서 나오므로
    항상 일치함.
    """
    base64_image = preprocess_image(image_input)
    base64_url   = f"data:image/jpeg;base64,{base64_image}"

    ai_analysis, species, emotion = _analyze(base64_url)
    pet_speech, audio_data        = _speech_and_audio(ai_analysis, species, emotion)

    return ai_analysis, pet_speech, emotion, species, audio_data
