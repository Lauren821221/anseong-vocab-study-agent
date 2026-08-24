# 안성맞춤 수준별 단어 스터디 에이전트 v2

## GitHub
이 폴더의 내용 전체를 기존 GitHub 저장소에 업로드/덮어쓰기합니다.
`.env` 실제 파일과 API Key는 GitHub에 올리지 마세요.

## Railway FastAPI 서비스
Start Command:
`uvicorn server.main:app --host 0.0.0.0 --port $PORT`

Variables:
- GEMINI_API_KEY = 실제 키
- GEMINI_MODEL = gemini-2.5-flash-lite

배포 후 `/health`가 `{"status":"ok"}`인지 확인합니다.

## Railway Streamlit 서비스
Start Command:
`streamlit run app/main.py --server.address 0.0.0.0 --server.port $PORT`

Variables:
- API_BASE_URL = `https://<FastAPI 공개도메인>/api/v1`

Public Networking은 Streamlit 서비스가 실제 listen하는 `$PORT`에 연결합니다.

## iPhone/iPad
공개 HTTPS Streamlit URL로 Safari에서 접속할 수 있습니다.
- `사진 파일 선택`: 사진 보관함/파일에서 업로드
- `카메라로 촬영`: Safari 카메라 권한 허용 후 바로 촬영
카메라 기능은 HTTPS 공개 주소에서 사용하는 것을 권장합니다.

## 학습 로직
10개 문제 유형을 제공하고, 학습자 수준 + 난이도/시험 스타일에 따라 추천 유형을 다르게 선택합니다.
추천 결과는 강제가 아니라 사용자가 체크박스로 최종 선택하며, 선택한 유형만 문제 생성 API에 전달됩니다.

난이도/스타일:
- 쉬움 / 보통 / 어려움
- TOSEL 수준
- TOEFL Junior 수준
- TOEFL 수준
- 최선어학원 유형

주의: TOSEL/TOEFL/TOEFL Junior 이름은 난이도·역량 설계를 위한 참고 스타일이며,
공식 시험 문항을 복제하지 않고 새 문제를 생성합니다.

## 새 접속/초기화
메인 화면의 업로드/분석/문제/채점 상태는 새 브라우저 세션 또는 `새 학습 시작`에서 초기화합니다.
학습 이력은 FastAPI의 DB에 별도로 저장되어 사이드바에 남습니다.

## Railway DB 주의
현재 history.db(SQLite)는 과제 시연과 단일 인스턴스 테스트에 적합합니다.
Railway 재배포 후에도 이력을 확실히 영구 보존해야 한다면 Railway Volume 또는 PostgreSQL로 전환하세요.
