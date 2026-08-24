from typing import Dict, List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from server.utils.config import get_embeddings


def build_documents(analysis: Dict) -> List[Document]:
    docs = []

    words = analysis.get("word_details", [])
    for item in words:
        word = item.get("word", "")
        meaning = item.get("meaning", "")
        note = item.get("context", "")

        if word:
            docs.append(
                Document(
                    page_content=(
                        f"word: {word}\n"
                        f"meaning: {meaning}\n"
                        f"context: {note}"
                    ),
                    metadata={"word": word},
                )
            )

    return docs


def retrieve_focus_words(
    analysis: Dict,
    query: str,
    k: int = 12,
) -> List[str]:
    docs = build_documents(analysis)

    if not docs:
        return analysis.get("extracted_words", [])[:k]

    try:
        vector_store = FAISS.from_documents(
            docs,
            get_embeddings(),
        )
        hits = vector_store.similarity_search(query, k=min(k, len(docs)))

        words = [
            d.metadata.get("word")
            for d in hits
            if d.metadata.get("word")
        ]

        return words

    except Exception:
        return analysis.get("extracted_words", [])[:k]
