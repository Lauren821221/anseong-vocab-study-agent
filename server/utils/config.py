from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings


load_dotenv()


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    DB_PATH: str = "history.db"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./history.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def get_client():
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY가 설정되지 않았습니다. "
            "프로젝트 최상위 .env 파일을 확인하세요."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_text(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.4,
) -> str:
    client = get_client()

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction or None,
        ),
    )
    return response.text or ""


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    system_instruction: str = "",
) -> str:
    client = get_client()

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[prompt, image_part],
        config=types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction or None,
        ),
    )
    return response.text or ""


class GeminiEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=texts,
        )
        return [list(item.values) for item in result.embeddings]

    def embed_query(self, text: str) -> List[float]:
        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=[text],
        )
        return list(result.embeddings[0].values)


def get_embeddings():
    return GeminiEmbeddings()
