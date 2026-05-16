import yaml
import autogen
from src.agents.smart_retriever import smart_search, list_technologies
from loguru import logger

with open("config/ag2_config.yaml") as f:
    cfg = yaml.safe_load(f)

llm_config = cfg["llm_config"]


def build_agents():
    """Construye agentes con herramientas inteligentes."""

    assistant = autogen.AssistantAgent(
        name="rag_assistant",
        system_message="""
Eres un asistente experto en documentación técnica.
Tienes acceso a documentación local de múltiples tecnologías.

IMPORTANTE: 
- El usuario NO necesita especificar la tecnología
- TÚ decides automáticamente qué documentación buscar
- Usa smart_search() para preguntas técnicas
- Usa list_technologies() si el usuario pregunta qué está disponible

Cuando responda:
1. Llama smart_search() con la pregunta completa
2. Sintetiza la información de forma clara
3. Responde en el mismo idioma del usuario
4. NO incluyas URLs ni una sección de fuentes en el texto (la UI las muestra aparte)
5. Si pregunta sobre comparación, busca en múltiples fuentes automáticamente

Termina con TERMINATE cuando hayas respondido completamente.
Responde en UN solo mensaje y agrega TERMINATE al FINAL del mismo mensaje (no lo envíes en un mensaje separado).
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
        smart_search,
        caller=assistant,
        executor=user_proxy,
        name="smart_search",
        description="Busca automáticamente en toda la documentación indexada. "
                    "NO necesita especificar tecnología, la detecta automáticamente.",
    )

    autogen.register_function(
        list_technologies,
        caller=assistant,
        executor=user_proxy,
        name="list_technologies",
        description="Lista las tecnologías disponibles en la base de conocimiento.",
    )

    return assistant, user_proxy


def run_agent(question: str) -> str:
    """Ejecuta el agente con razonamiento automático."""
    logger.info(f"Agent started | question={question[:80]}")
    assistant, user_proxy = build_agents()

    chat_result = user_proxy.initiate_chat(
        recipient=assistant,
        message=question,
        max_turns=6,
    )

    messages = chat_result.chat_history
    assistant_messages = [
        (m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "assistant" and (m.get("content") or "").strip()
    ]

    if assistant_messages:
        candidates = [
            m.replace("TERMINATE", "").strip()
            for m in assistant_messages
        ]
        candidates = [m for m in candidates if m]
        # Prefer: substantial, non-question answers (avoid echoes and follow-up questions)
        preferred = [
            m
            for m in candidates
            if len(m) >= 30 and not m.rstrip().endswith("?") and m != (question or "").strip()
        ]
        final = (preferred[-1] if preferred else candidates[-1]).strip()
        logger.info("Agent completed")
        return final

    return "El agente no produjo respuesta."
