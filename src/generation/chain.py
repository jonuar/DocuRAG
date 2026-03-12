from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import yaml

# Cargar config
with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

# Modelos
llm = OllamaLLM(
    model=cfg["llm"]["model"],
    base_url=cfg["llm"]["base_url"],
    temperature=cfg["llm"]["temperature"],
)

embeddings = OllamaEmbeddings(
    model=cfg["embeddings"]["model"],
    base_url=cfg["embeddings"]["base_url"],
)

# Vector store
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

# Prompt
prompt = ChatPromptTemplate.from_template("""
Eres un asistente experto en documentación técnica.
Responde ÚNICAMENTE basándote en el contexto proporcionado.
Si la información no está en el contexto, di exactamente: 
"No encontré información sobre esto en la documentación indexada."

Contexto:
{context}

Pregunta: {question}

Respuesta (menciona las secciones de documentación que usaste):
""")

def format_docs(docs):
    return "\n\n---\n\n".join(
        f"[Fuente: {doc.metadata.get('source_url', 'desconocida')}]\n{doc.page_content}"
        for doc in docs
    )

# Chain principal
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
    """Hace una pregunta al RAG y devuelve respuesta + fuentes."""
    docs = retriever.invoke(question)
    answer = chain.invoke(question)

    # Deduplicar fuentes por URL — varios chunks pueden venir de la misma página
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