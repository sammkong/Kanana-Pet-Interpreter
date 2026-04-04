# 🐾 무슨 생각 하냥? (Pet Interpreter)
> **Kanana-o Omni API**를 활용한 멀티모달 반려동물 속마음 해석기

![my_pet](docs/my_pet.jpg)

## 🌟 Project Overview
본 프로젝트는 카카오 **Kanana-o API 베타테스트**의 일환으로 제작되었습니다.
반려동물 사진 한 장을 업로드하면, AI가 표정·자세·환경을 분석하여 동물의 시점에서 현재 기분을 **텍스트**와 **음성**으로 들려주는 멀티모달 AI 서비스입니다.

## 🚀 Key Features
| 기능 | 설명 |
|------|------|
| 📸 Vision Analysis | 반려동물의 표정, 자세, 주변 환경 인식 |
| 🧠 Emotional Reasoning | 기쁨 / 삐짐 / 당황 / 평온 / 간절 5가지 감정 분류 |
| 💬 Persona Speech | 개는 `~멍!`, 고양이는 `~냥.` 말투로 1인칭 대사 생성 |
| 🔊 Voice Synthesis | Kanana-o 멀티모달 응답으로 텍스트·음성 동시 생성 및 즉시 재생 |

## 🛠 Tech Stack
- **AI Model**: Kanana-o Omni API (Kakao Cloud)
- **Frontend**: Streamlit
- **Language**: Python 3.10+
- **Libraries**: openai, Pillow, python-dotenv

## 🌐 서비스 이용해보기

👉 **[https://kanana-pet-interpreter.streamlit.app](https://kanana-pet-interpreter.streamlit.app)**

별도 설치 없이 위 링크에 접속하시면, 바로 이용 가능합니다!

## 📖 사용 방법

1. 위 링크로 접속합니다
2. **"반려동물 사진을 올려주세요"** 버튼을 눌러 JPG / PNG 사진을 업로드합니다
3. **"🚀 분석 시작"** 버튼을 클릭합니다
4. AI가 사진을 분석하는 동안 잠시 기다립니다 (10~20초 소요)
5. 결과 확인:
   - 🔍 **AI 분석**: 반려동물의 외형·자세·표정·배경 설명
   - 💬 **반려동물의 말**: 개는 `~멍!`, 고양이는 `~냥.` 말투로 속마음 표현
   - 🔊 **음성 재생**: 반려동물의 말을 AI 음성으로 바로 청취

> ⚠️ API 호출 한도가 있어 응답이 느리거나 오류가 발생할 수 있습니다.

## 왜 만들었냐면...
현생에 지쳐 힐링 서비스를 만들어 보고자 했습니다. 제 강아지 귀엽죠!