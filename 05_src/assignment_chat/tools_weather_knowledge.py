from langchain.tools import tool
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

import os
from dotenv import load_dotenv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_DIR = os.path.dirname(_THIS_DIR)  # 05_src
CHROMA_PATH = os.path.join(_THIS_DIR, "chroma_store")

load_dotenv(os.path.join(_ENV_DIR, ".env"))
load_dotenv(os.path.join(_ENV_DIR, ".secrets"))


USE_GATEWAY = os.getenv("USE_GATEWAY", "True").lower() == "true"
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')


embedding_function = OpenAIEmbeddingFunction(
    api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_type="openai",
    model_name=EMBEDDING_MODEL,
    default_headers={
        "x-api-key": os.getenv("API_GATEWAY_KEY")
    }
)

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(name="weather_knowledge", embedding_function=embedding_function)

@tool
def search_weather_knowledge(query: str, category: str = None) -> list[dict]:
    """
    Semantic search over a curated weather knowledge base.
    category, if provided, must be one of: history, phenomena, records, folklore.
    Only set it when the user's question clearly falls into one of these buckets;
    otherwise leave it unset and search across all categories.
    """
    where_filter = {"category": category} if category else None
    results = collection.query(query_texts=[query], n_results=3, where=where_filter)
    return results