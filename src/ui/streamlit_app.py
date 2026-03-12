import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
import streamlit as st
from src.generation.chain import query
from src.ingestion.pipeline import ingest_crawl, ingest_urls, get_stats
import yaml

def _format_latency(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.0f}s"

# ── Configuración de página ───────────────────────────────────────────
st.set_page_config(
    page_title="DocRAG",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open("config/sources.yaml") as f:
    sources = yaml.safe_load(f)

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 DocRAG")
    st.caption("Documentación técnica con IA local")
    st.divider()

    # Selector de tecnología
    tech_options = list(sources["technologies"].keys())
    selected_tech = st.selectbox(
        "Tecnología activa",
        tech_options,
        format_func=lambda x: sources["technologies"][x]["name"]
    )

    st.divider()

    # Stats del vectorstore
    st.subheader("📊 Base de conocimiento")
    stats = get_stats()
    st.metric("Total chunks", stats["total_chunks"])
    for tech, count in stats["by_technology"].items():
        st.caption(f"  {tech}: {count} chunks")

    st.divider()

    # Ingesta manual
    st.subheader("⚙️ Ingestar documentación")
    ingest_mode = st.radio("Modo", ["URLs del config", "URL personalizada"])

    if ingest_mode == "URLs del config":
        if st.button(f"Ingestar {selected_tech}", use_container_width=True):
            tech_cfg = sources["technologies"][selected_tech]
            selector = tech_cfg.get("selectors", {}).get("content", "main")
            with st.spinner(f"Ingesting {selected_tech}..."):
                result = ingest_urls(
                    urls=tech_cfg["docs_urls"],
                    technology=selected_tech,
                    content_selector=selector,
                )
            st.success(f"✅ {result['chunks_ingested']} chunks añadidos")
    else:
        custom_url = st.text_input("URL de documentación")
        if st.button("Ingestar URL", use_container_width=True) and custom_url:
            with st.spinner("Crawleando..."):
                result = ingest_crawl(
                    start_url=custom_url,
                    technology=selected_tech,
                    max_pages=20,
                )
            st.success(f"✅ {result['chunks_ingested']} chunks · {result['pages_crawled']} páginas")

    st.divider()
    if st.button("🗑️ Limpiar historial", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Chat principal ────────────────────────────────────────────────────
st.header(f"💬 Pregunta sobre {sources['technologies'][selected_tech]['name']}")

# Inicializar historial
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📎 {len(msg['sources'])} fuentes"):
                for src in msg["sources"]:
                    st.markdown(f"🔗 [{src['section'] or src['url']}]({src['url']})")

# Input del usuario
if prompt := st.chat_input(f"Pregunta sobre {selected_tech}..."):

    # Añadir mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Buscando en la documentación..."):
            start = time.time()
            result = query(prompt)
            latency = int((time.time() - start) * 1000)

        st.write(result["answer"])

        # Métricas inline
        col1, col2, col3 = st.columns(3)
        col1.caption(f"⏱️ {_format_latency(latency)}")
        col2.caption(f"📄 {len(result['sources'])} chunks")
        col3.caption(f"🤖 granite3.2")

        # Fuentes expandibles
        if result["sources"]:
            with st.expander(f"📎 {len(result['sources'])} fuentes"):
                for src in result["sources"]:
                    st.markdown(f"🔗 [{src['section'] or src['url']}]({src['url']})")

    # Guardar en historial
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })