import os
import base64
import json
from typing import Tuple, Optional
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from openai import OpenAI
import wave

load_dotenv()
KANANA_API_KEY = os.getenv("KANANA_API_KEY")

if not KANANA_API_KEY:
    raise ValueError("KANANA_API_KEY를 .env 파일에 설정해주세요.")

# 올바른 Kanana-o 엔드포인트 (카카오 제공)
client = OpenAI(
    base_url="https://kanana-o.a2s-endpoint.kr-central-2.kakaocloud.com/v1",
    api_key=KANANA_API_KEY
)

SAMPLE_RATE = 24000


def preprocess_image(image_input) -> str:
    """이미지를 Base64로 인코딩"""
    try:
        if isinstance(image_input, str):
            image = Image.open(image_input)
        else:
            image = Image.open(BytesIO(image_input))
        
        if image.mode in ("RGBA", "LA", "P"):
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "RGBA":
                rgb_image.paste(image, mask=image.split()[-1])
            else:
                rgb_image.paste(image)
            image = rgb_image
        
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()
        
        return base64.b64encode(image_bytes).decode("utf-8")
    
    except Exception as e:
        raise ValueError(f"이미지 전처리 실패: {str(e)}")


def get_system_prompt() -> str:
    """반려동물 감정 분석 프롬프트"""
    return """당신은 반려동물 심리 분석가입니다.

다음 순서로 분석하세요:
1. 동물 종 파악 (개/고양이/기타)
2. 신체 언어 읽기:
   - 귀: 위치, 움직임
   - 눈: 크기, 깜빡임, 응시
   - 꼬리: 위치, 속도
   - 자세: 긴장도, 근육 상태
3. 주변 환경 분석 (밥그릇, 장난감, 자극물 등)
4. 종합 감정 판단

페르소나:
- 개: 에너제틱, 긍정적, 직설적
- 고양이: 츤데레, 신비로움, 독립적
- 기타: 동물 특성에 맞는 고유 톤

감정 태그 (반드시 하나만 선택):
- 기쁨: 에너지 넘치고 명랑
- 삐짐: 불만족, 투덜거림
- 당황: 혼란, 놀람
- 평온: 차분, 만족
- 간절: 간청, 애타는 상태

출력 형식:
1~N줄: 1인칭 반말, 자연스러운 한국어 (2~3문장)
마지막: {"emotion": "기쁨|삐짐|당황|평온|간절"}"""


def analyze_pet_image(base64_image: str) -> Tuple[str, str, Optional[bytes]]:
    """Kanana-o API로 반려동물 감정 분석 + 음성 생성"""
    
    try:
        # OpenAI 호환 인터페이스로 텍스트 + 오디오 함께 요청
        response = client.chat.completions.create(
            model="kanana-o",
            messages=[
                {
                    "role": "system",
                    "content": get_system_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": base64_image}
                        },
                        {
                            "type": "text",
                            "text": "이 사진 속 반려동물의 심리상태를 분석해주세요."
                        }
                    ]
                }
            ],
            modalities=["text", "audio"],
            stream=True,
        )
        
        analysis_text = ""
        audio_chunks = []
        
        # 스트림 응답 처리
        for chunk in response:
            raw = chunk.model_dump()
            choices = raw.get("choices") or []
            if not choices:
                continue
            
            delta = choices[0].get("delta") or {}
            
            # 텍스트 콘텐츠
            content = delta.get("content")
            if isinstance(content, str) and content:
                analysis_text += content
            
            # 오디오 데이터
            audio = delta.get("audio")
            if audio is not None:
                audio_b64_data = None
                if isinstance(audio, str):
                    audio_b64_data = audio
                elif isinstance(audio, dict):
                    audio_b64_data = audio.get("data") or audio.get("audio")
                
                if isinstance(audio_b64_data, str) and audio_b64_data:
                    try:
                        pcm = base64.b64decode(audio_b64_data, validate=True)
                        if pcm:
                            audio_chunks.append(pcm)
                    except Exception as e:
                        print(f"오디오 디코딩 실패: {e}")
        
        # 감정 태그 추출
        emotion_tag = "평온"
        try:
            lines = analysis_text.strip().split('\n')
            json_line = lines[-1]
            emotion_obj = json.loads(json_line)
            emotion_tag = emotion_obj.get("emotion", "평온")
        except (json.JSONDecodeError, IndexError, KeyError):
            keywords = {
                "기쁨": ["기쁨", "행복", "즐거"],
                "삐짐": ["삐짐", "화", "짜증"],
                "당황": ["당황", "놀람"],
                "간절": ["간절", "간청"],
                "평온": ["평온", "차분", "안정"]
            }
            for emotion, words in keywords.items():
                if any(w in analysis_text for w in words):
                    emotion_tag = emotion
                    break
        
        # JSON 부분 제거
        lines = analysis_text.strip().split('\n')
        clean_text = '\n'.join(lines[:-1]).strip() if len(lines) > 1 else analysis_text
        
        # 오디오 청크 병합
        audio_data = None
        if audio_chunks:
            audio_data = merge_audio_chunks(audio_chunks)
        
        return clean_text, emotion_tag, audio_data
    
    except Exception as e:
        raise RuntimeError(f"API 호출 실패: {str(e)}")


def merge_audio_chunks(chunks: list) -> Optional[bytes]:
    """오디오 청크들을 WAV 파일로 병합"""
    try:
        if not chunks:
            return None
        
        # 모든 PCM 데이터 합치기
        all_frames = b"".join(chunks)
        
        # WAV 포맷으로 저장
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(all_frames)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        print(f"오디오 병합 실패: {str(e)}")
        return None


def get_pet_mind(image_input) -> Tuple[str, str, Optional[bytes]]:
    """사진 업로드 -> 감정 분석 + 음성 생성"""
    
    base64_image = preprocess_image(image_input)
    
    # Base64를 data URL 포맷으로 변환 (카카오 API 요구사항)
    base64_data_url = f"data:image/jpeg;base64,{base64_image}"
    
    analysis_text, emotion_tag, audio_data = analyze_pet_image(base64_data_url)
    
    return analysis_text, emotion_tag, audio_data