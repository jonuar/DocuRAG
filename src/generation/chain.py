import os
import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from loguru import logger

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

# ── Embeddings — siempre Ollama en local, nomic via HF en cloud ───────
IS_CLOUD = os.getenv("DEPLOYMENT") == "cloud"

if IS_CLOUD:
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="nomic-ai/nomic-embed-text-v1",
        model_kwargs={"trust_remote_code": True},
    )
else:
    embeddings = OllamaEmbeddings(
        model=cfg["embeddings"]["model"],
        base_url=cfg["embeddings"]["base_url"],
    )

# ── LLM — Ollama local o HF Inference API en cloud ───────────────────
if IS_CLOUD:
    from langchain_huggingface import HuggingFaceEndpoint
    llm = HuggingFaceEndpoint(
        repo_id="ibm-granite/granite-3.2-8b-instruct",
        huggingfacehub_api_token=os.getenv("HF_TOKEN"),
        temperature=cfg["llm"]["temperature"],
        max_new_tokens=cfg["llm"]["max_tokens"],
    )
    logger.info("Using HuggingFace Inference API (cloud mode)")
else:
    from langchain_ollama import OllamaLLM
    llm = OllamaLLM(
        model=cfg["llm"]["model"],
        base_url=cfg["llm"]["base_url"],
        temperature=cfg["llm"]["temperature"],
    )
    logger.info("Using Ollama local (local mode)")

# ── Vector store ──────────────────────────────────────────────────────
vectorstore = Chroma(
    collection_name=cfg["vectorstore"]["collection_name"],
    embedding_function=embeddings,
    persist_directory=cfg["vectorstore"]["persist_directory"],
)

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": cfg["retrieval"]["k"],
        "fetch_k": cfg["retrieval"]["fetch_k"],
    },
)

# ── Prompt ────────────────────────────────────────────────────────────
prompt = ChatPromptTemplate.from_template("""
You are an expert technical documentation assistant.
Answer ONLY based on the context provided below.
If the information is not in the context, say exactly:
"I could not find information about this in the indexed documentation."

Always mention which documentation sections you used.

Context:
{context}

Question: {question}

Answer:
""")

def format_docs(docs):
    return "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source_url', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )

chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
    | StrOutputParser()
)

def query(question: str) -> dict:
    docs = retriever.invoke(question)
    answer = chain.invoke(question)

    seen_urls = set()
    sources = []
    for doc in docs:
        url = doc.metadata.get("source_url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            sources.append({
                "url": url,
                "technology": doc.metadata.get("technology", ""),
                "section": doc.metadata.get("section", ""),
            })

    return {"answer": answer, "sources": sources}