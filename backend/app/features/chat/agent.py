from __future__ import annotations

import logging
from typing import Annotated, Any, AsyncGenerator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.services.embeddings import embed_query
from app.services.gemini import stream_text
from app.services.qdrant import search_chunks

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    analysis_id: str
    video_a_id: str
    video_b_id: str
    video_a_meta: dict[str, Any]
    video_b_meta: dict[str, Any]
    retrieved_context: str
    citations: list[dict[str, Any]]


def _build_system_prompt(state: AgentState) -> str:
    meta_a = state.get("video_a_meta", {})
    meta_b = state.get("video_b_meta", {})

    def fmt(meta: dict, label: str) -> str:
        er = meta.get("engagement_rate")
        er_str = f"{er:.2f}%" if er is not None else "N/A"
        return (
            f"Video {label}: {meta.get('title', 'Unknown')} by {meta.get('creator', 'Unknown')}\n"
            f"  Platform: {meta.get('platform', 'unknown')} | Views: {meta.get('views', 'N/A'):,} | "
            f"Likes: {meta.get('likes', 'N/A')} | Comments: {meta.get('comments', 'N/A')}\n"
            f"  Engagement Rate: {er_str} | Followers: {meta.get('followers', 'N/A')} | "
            f"Duration: {meta.get('duration', 'N/A')}s | Uploaded: {meta.get('upload_date', 'N/A')}"
        )

    return f"""You are HookIQ, an expert video content analyst helping creators understand why videos perform differently.

You have access to two videos that have been analyzed:

{fmt(meta_a, 'A')}

{fmt(meta_b, 'B')}

CRITICAL RULES:
1. ALWAYS cite sources using [A-Chunk-N] or [B-Chunk-N] format for every claim.
2. Never make claims without citing a specific chunk.
3. End every response with a "Sources:" section listing all cited chunks.
4. Use the retrieved context below to answer questions.
5. Be specific, data-driven, and actionable.
6. When asked follow-up questions, remember the video context from this conversation.

Retrieved Context:
{state.get("retrieved_context", "No context retrieved yet.")}"""


def retrieve_node(state: AgentState) -> dict[str, Any]:
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_context": "", "citations": []}

    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    if not last_human:
        return {"retrieved_context": "", "citations": []}

    query = last_human.content if isinstance(last_human.content, str) else str(last_human.content)
    query_vector = embed_query(query)
    analysis_id = state.get("analysis_id", "")

    chunks_a = search_chunks(query_vector, analysis_id, "A", top_k=5)
    chunks_b = search_chunks(query_vector, analysis_id, "B", top_k=5)

    context_parts = []
    citations = []

    for chunk in chunks_a:
        tag = f"A-Chunk-{chunk['chunk_id']}"
        context_parts.append(f"[{tag}]\n{chunk['content']}")
        citations.append({"tag": tag, "label": "A", "chunk_id": chunk["chunk_id"], "score": chunk["score"]})

    for chunk in chunks_b:
        tag = f"B-Chunk-{chunk['chunk_id']}"
        context_parts.append(f"[{tag}]\n{chunk['content']}")
        citations.append({"tag": tag, "label": "B", "chunk_id": chunk["chunk_id"], "score": chunk["score"]})

    return {
        "retrieved_context": "\n\n".join(context_parts),
        "citations": citations,
    }


def _messages_to_dicts(messages: list[BaseMessage]) -> list[dict[str, str]]:
    result = []
    for m in messages:
        if isinstance(m, HumanMessage):
            result.append({"role": "user", "content": m.content if isinstance(m.content, str) else str(m.content)})
        elif isinstance(m, AIMessage):
            result.append({"role": "assistant", "content": m.content if isinstance(m.content, str) else str(m.content)})
    return result


def build_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", END)
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


compiled_graph = build_graph()


async def stream_agent_response(
    analysis_id: str,
    session_id: str,
    message: str,
    video_a_meta: dict[str, Any],
    video_b_meta: dict[str, Any],
) -> AsyncGenerator[tuple[str, list[dict[str, Any]]], None]:
    config = {"configurable": {"thread_id": session_id}}

    input_state: AgentState = {
        "messages": [HumanMessage(content=message)],
        "analysis_id": analysis_id,
        "video_a_id": video_a_meta.get("id", ""),
        "video_b_id": video_b_meta.get("id", ""),
        "video_a_meta": video_a_meta,
        "video_b_meta": video_b_meta,
        "retrieved_context": "",
        "citations": [],
    }

    result = await compiled_graph.ainvoke(input_state, config=config)
    citations = result.get("citations", [])
    system_prompt = _build_system_prompt(result)

    all_messages = result.get("messages", [])
    msg_dicts = _messages_to_dicts(all_messages)

    full_response = ""
    async for chunk in stream_text(system_prompt, msg_dicts):
        full_response += chunk
        yield chunk, []

    citation_tags = [c["tag"] for c in citations if c["tag"] in full_response or True]
    yield "", citations
