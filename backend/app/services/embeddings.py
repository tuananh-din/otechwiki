import openai
from app.core.config import get_settings

settings = get_settings()
client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    default_headers=settings.openai_extra_headers
)


async def get_embedding(text: str) -> list[float]:
    """Generate embedding for a text using OpenAI."""
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def get_embeddings_batch(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """Generate embeddings for multiple texts in batches."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings
