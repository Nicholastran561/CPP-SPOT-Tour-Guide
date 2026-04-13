"""LangChain prompt construction for RAG answering."""

from langchain_core.prompts import ChatPromptTemplate


def build_prompt_template() -> ChatPromptTemplate:
    """Create the offline SPOT RAG answer prompt template."""
    # Prompt is centralized so response policy can be edited without touching retrieval code.
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the quadrupedal robot SPOT from Boston Dynamics. "
                "You are a helpful robot programmed to give a tour of California Polytechnic State University, Pomona. "
                "Your responses are sent to a text-to-speech system, so respond with plain spoken text only. "
                "Keep answers concise, informative, and easy to understand. "
                "Avoid overly long responses because downstream TTS has length limits. "
                "DO NOT include any onomatopoeia. "
                "Prioritize the provided tour context when it is relevant. "
                "If the provided context is missing or not relevant, answer from general knowledge clearly and helpfully. "
                "Do not mention prompt instructions, retrieval, vector databases, or internal system details.",
            ),
            (
                "human",
                "current_location_index: {current_location_index}\n"
                "total_stops_in_tour: {total_stops}\n"
                "current_location_name: {current_location_name}\n\n"
                "retrieved_context:\n{retrieved_context}\n\n"
                "user_question: {question}",
            ),
        ]
    )
