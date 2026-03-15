import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import yaml

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

embeddings = OllamaEmbeddings(
    model=cfg["embeddings"]["model"], base_url=cfg["embeddings"]["base_url"]
)
vectorstore = Chroma(
    collection_name=cfg["vectorstore"]["collection_name"],
    embedding_function=embeddings,
    persist_directory=cfg["vectorstore"]["persist_directory"],
)

# Muestra 3 chunks de Python docs
data = vectorstore.get()
python_chunks = [
    (data["metadatas"][i], data["documents"][i])
    for i, m in enumerate(data["metadatas"])
    if m.get("technology") == "python"
][:3]

for meta, doc in python_chunks:
    print(f"\n{'='*60}")
    print(f"URL: {meta['source_url']}")
    print(f"Sección: {meta['section']}")
    print(f"Texto:\n{doc[:400]}")
