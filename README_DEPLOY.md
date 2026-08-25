# 안성맞춤 수준별 단어 스터디 에이전트 v3 FINAL

## 이번 버전 핵심
최종 승인한 화면/흐름을 반영했습니다.

자료 선택(업로드 / 촬영 / 기존자료)
→ AI 자료분석
→ 단어 확인·수정
→ 학습자 수준
→ 난이도/시험유형
→ 내신 준비형
→ AI 문제유형 추천
→ 10개 유형에서 사용자 추가/삭제
→ 문제 수
→ 문제 출제
→ 채점
→ 취약 단어
→ 유의어/반의어/관련어/Collocation/예문
→ 학습이력 저장

상단 탭:
- 📝 테스트 문제 만들기
- 📊 학습 이력

## GitHub에 올릴 구조
app/
server/
.env.example
.gitignore
README_DEPLOY.md
history.db
requirements.txt

이 ZIP의 내용으로 기존 GitHub 저장소의 동일 파일을 덮어쓰세요.
이전 버전에만 있던 `server/retrieval/` 같은 폴더가 남아 있으면 삭제하세요.

## Railway - FastAPI 서비스
기존 FastAPI 서비스 연결을 그대로 사용합니다.

Start Command:
uvicorn server.main:app --host 0.0.0.0 --port $PORT

Variables:
GEMINI_API_KEY=<실제 Gemini API Key>
GEMINI_MODEL=gemini-2.5-flash-lite

확인:
https://<FASTAPI_DOMAIN>/health
→ {"status":"ok"}

## Railway - Streamlit 서비스
기존 zippy-success 서비스를 그대로 사용합니다.

Start Command:
streamlit run app/main.py --server.address 0.0.0.0 --server.port $PORT

Variables:
API_BASE_URL=https://<FASTAPI_DOMAIN>/api/v1

중요:
API_BASE_URL은 Streamlit(zippy-success) 주소가 아니라 FastAPI 서비스의 공개 주소입니다.

## iPhone / iPad
공개 HTTPS Streamlit 주소(zippy-success)로 Safari에서 접속합니다.
- 사진 파일 업로드: 사진 보관함/파일
- 카메라로 촬영: 해당 메뉴를 선택했을 때만 `st.camera_input`이 나타남
- Safari가 요청하면 카메라 권한 허용

## 학습자료/이력
- 사진을 AI 분석하면 추출 단어 세트가 `study_materials`에 저장됩니다.
- 기존 학습자료 불러오기에서 다시 사용할 수 있습니다.
- 채점 결과는 `study_history`에 저장됩니다.
- 학습 이력 탭에서 취약 단어, 관련 단어, 예문까지 다시 확인합니다.

## SQLite 주의
현재 `history.db`는 과제 시연에 적합합니다.
Railway 재배포 후에도 이력을 영구 보존하려면 Railway Volume 또는 PostgreSQL이 필요합니다.
