import yaml
import autogen
from src.agents.rag_tool import query_docs, list_technologies
from loguru import logger

with open("config/ag2_config.yaml") as f:
    cfg = yaml.safe_load(f)

llm_config = cfg["llm_config"]


def build_agents():
    """Construye y conecta los agentes con sus herramientas."""

    # Agente asistente — tiene acceso a las tools
    assistant = autogen.AssistantAgent(
        name="rag_assistant",
        system_message="""
Eres un asistente experto en documentación técnica.
Tienes acceso a documentación oficial de tecnologías como FastAPI y Python.

Cuando el usuario haga una pregunta técnica:
1. Usa list_technologies para ver qué está disponible si no estás seguro
2. Usa query_docs con la tecnología correcta y una pregunta clara
3. Para preguntas complejas, haz múltiples llamadas a query_docs
4. Sintetiza la información en una respuesta clara y estructurada
5. Cita siempre las fuentes que encontraste

Si la información no está en la documentación indexada, dilo claramente.
No inventes información que no esté en las fuentes.

Cuando hayas completado la tarea satisfactoriamente, termina tu mensaje con TERMINATE.
""",
        llm_config=llm_config,
    )

    # UserProxy — ejecuta las herramientas y representa al usuario
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        code_execution_config=False,
    )

    # Registrar herramientas
    autogen.register_function(
        query_docs,
        caller=assistant,
        executor=user_proxy,
        name="query_docs",
        description="Busca respuestas en la documentación técnica indexada. "
                    "Parámetros: question (str), technology (str: 'fastapi' o 'python')",
    )

    autogen.register_function(
        list_technologies,
        caller=assistant,
        executor=user_proxy,
        name="list_technologies",
        description="Lista las tecnologías disponibles en la base de conocimiento RAG.",
    )

    return assistant, user_proxy


def run_agent(question: str) -> str:
    """
    Ejecuta el agente con una pregunta y retorna la respuesta final.
    Úsable desde Streamlit o desde CLI.
    """
    logger.info(f"Agent started | question={question[:80]}")
    assistant, user_proxy = build_agents()

    chat_result = user_proxy.initiate_chat(
        recipient=assistant,
        message=question,
        max_turns=8,
    )

    # Extraer la última respuesta del asistente
    messages = chat_result.chat_history
    assistant_messages = [
        m["content"] for m in messages
        if m.get("role") == "assistant" and m.get("content")
    ]

    if assistant_messages:
        # Limpiar TERMINATE del mensaje final
        final = assistant_messages[-1].replace("TERMINATE", "").strip()
        logger.info("Agent completed successfully")
        return final

    return "El agente no produjo una respuesta."