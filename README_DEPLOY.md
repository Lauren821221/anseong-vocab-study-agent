# 안성맞춤 수준별 단어 스터디 에이전트 - 공개 배포 가이드

## 1) GitHub 업로드
이 폴더 전체를 GitHub 저장소에 업로드합니다.

중요:
- `.env`는 업로드하지 않습니다.
- `.env.example`만 업로드합니다.

## 2) Railway - FastAPI 서비스
같은 GitHub 저장소로 첫 번째 서비스를 만듭니다.

Start Command:
```bash
uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

Variables:
```text
GEMINI_API_KEY=실제_Gemini_API_Key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

배포 후 FastAPI 공개 URL을 확인합니다.

예:
```text
https://anseong-vocab-api-production.up.railway.app
```

확인:
```text
https://anseong-vocab-api-production.up.railway.app/health
https://anseong-vocab-api-production.up.railway.app/docs
```

## 3) Railway - Streamlit 서비스
같은 GitHub 저장소로 두 번째 서비스를 만듭니다.

Start Command:
```bash
streamlit run app/main.py --server.address 0.0.0.0 --server.port $PORT
```

Variables:
```text
API_BASE_URL=https://YOUR-FASTAPI-SERVICE.up.railway.app/api/v1
```

주의: `/api/v1`까지 포함합니다.

## 4) 검토자에게 전달
검토자에게는 Streamlit 서비스 공개 URL 하나만 전달합니다.

예:
```text
https://anseong-vocab-study-production.up.railway.app
```

PC/아이폰/안드로이드 브라우저에서 바로 접속할 수 있습니다.

## 5) 로컬 실행
FastAPI:
```bash
uvicorn server.main:app --reload --port 8000
```

Streamlit:
```bash
streamlit run app/main.py
```

접속:
```text
http://localhost:8501
```
