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

# YAML de configuración — se llama app_config, nunca sources
with open("config/sources.yaml") as f:
    app_config = yaml.safe_load(f)

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 DocRAG")
    st.caption("Documentación técnica con IA local")
    st.divider()

    tech_options = list(app_config["technologies"].keys())
    selected_tech = st.selectbox(
        "Tecnología activa",
        tech_options,
        format_func=lambda x: app_config["technologies"][x]["name"]
    )

    st.divider()
    mode = st.radio(
        "Modo de respuesta",
        ["RAG directo", "Agente (AG2)"],
        help="Agente hace múltiples consultas y razona antes de responder"
    )

    st.divider()
    st.subheader("📊 Base de conocimiento")
    stats = get_stats()
    st.metric("Total chunks", stats["total_chunks"])
    for tech, count in stats["by_technology"].items():
        st.caption(f"  {tech}: {count} chunks")

    st.divider()
    st.subheader("⚙️ Ingestar documentación")
    ingest_mode = st.radio("Modo", ["URLs del config", "URL personalizada"])

    if ingest_mode == "URLs del config":
        if st.button(f"Ingestar {selected_tech}", use_container_width=True):
            tech_cfg = app_config["technologies"][selected_tech]
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
st.header(f"💬 Pregunta sobre {app_config['technologies'][selected_tech]['name']}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📎 {len(msg['sources'])} fuentes"):
                for src in msg["sources"]:
                    label = src["section"] if src.get("section") else src["url"]
                    st.markdown(f"🔗 [{label}]({src['url']})")

# Input
if prompt := st.chat_input(f"Pregunta sobre {selected_tech}..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        spinner_text = "Pensando..." if mode == "RAG directo" else "El agente está razonando..."
        with st.spinner(spinner_text):
            start = time.time()

            if mode == "RAG directo":
                rag_result = query(prompt)
                answer = rag_result["answer"]
                sources = rag_result["sources"]  # lista de dicts con url/section
            else:
                from src.agents.assistant_agent import run_agent
                agent_question = f"Tecnología preferida: {selected_tech}\n\nPregunta: {prompt}"
                answer = run_agent(agent_question)
                sources = []  # el agente incluye fuentes en su texto

            latency = int((time.time() - start) * 1000)

        st.write(answer)

        col1, col2, col3 = st.columns(3)
        col1.caption(f"⏱️ {_format_latency(latency)}")
        col2.caption(f"🤖 {'granite3.2 + AG2' if mode == 'Agente (AG2)' else 'granite3.2'}")
        col3.caption(f"📄 {len(sources)} chunks" if sources else "")

        if sources:
            with st.expander(f"📎 {len(sources)} fuentes"):
                for src in sources:
                    label = src["section"] if src.get("section") else src["url"]
                    st.markdown(f"🔗 [{label}]({src['url']})")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })