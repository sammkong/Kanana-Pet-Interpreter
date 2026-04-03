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
| 🔊 Voice Synthesis | Kanana-o TTS로 반려동물 목소리 생성 및 즉시 재생 |

## 🛠 Tech Stack
- **AI Model**: Kanana-o Omni API (Kakao Cloud)
- **Frontend**: Streamlit
- **Language**: Python 3.10+
- **Libraries**: openai, Pillow, python-dotenv

## 📁 Project Structure
```
pet_interpreter/
├── app.py              # Streamlit UI
├── kanana_utils.py     # Kanana-o API 호출 및 분석 로직
├── requirements.txt    # 의존성 목록
├── .env                # API 키 (git 제외)
└── README.md
```

## ⚙️ Installation & Run

**1. 저장소 클론**
```bash
git clone https://github.com/your-username/pet_interpreter.git
cd pet_interpreter
```

**2. 가상환경 생성 및 활성화**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

**3. 패키지 설치**
```bash
pip install -r requirements.txt
```

**4. 환경 변수 설정**
프로젝트 루트에 `.env` 파일 생성:
```
KANANA_API_KEY=your_kanana_api_key_here
```

**5. 실행**
```bash
streamlit run app.py
```

## 🔑 API Key 발급
[카카오클라우드 콘솔](https://console.kakaocloud.com) → AI Service → Kanana-o에서 API 키를 발급받으세요.

## 🐶🐱 사용 방법 (추후 Streamlit Cloud 배포 예정)

### 로컬 실행
1. 브라우저에서 `http://localhost:8501` 접속
2. 반려동물 사진(JPG/PNG) 업로드
3. **분석 시작** 버튼 클릭
4. AI 분석 결과 + 말풍선 대사 + 음성 재생 확인