import json
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os
from dotenv import load_dotenv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_DIR = os.path.dirname(_THIS_DIR)  # 05_src
CHROMA_PATH = os.path.join(_THIS_DIR, "chroma_store")
DATA_PATH = os.path.join(_THIS_DIR, "data", "weather_knowledge.jsonl")

load_dotenv(os.path.join(_ENV_DIR, ".env"))
load_dotenv(os.path.join(_ENV_DIR, ".secrets"))

USE_GATEWAY = os.getenv("USE_GATEWAY", "False").lower() == "true"
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
COLLECTION_NAME = "weather_knowledge"

embedding_function = OpenAIEmbeddingFunction(
    api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_type="openai",
    model_name=EMBEDDING_MODEL,
    default_headers={
        "x-api-key": os.getenv("API_GATEWAY_KEY")
    }
)

def load_records(file_path: str) -> list[dict]:
    """Reads a JSONL file and returns a list of records."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def build_collection(records: list[dict]):
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # delete existing collection if it exists
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )

    documents = [item['text'] for item in records if 'text' in item]

    metadatas = [{k: v for k, v in item.items() if k != 'text' and k != 'id'} for item in records if 'text' in item and 'id' in item]

    ids = [item['id'] for item in records if 'id' in item]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

if __name__ == "__main__":
    records = load_records(DATA_PATH)
    build_collection(records)
    print(f"Ingested {len(records)} records into '{CHROMA_PATH}'.")