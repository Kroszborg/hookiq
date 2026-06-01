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

    def _fmt_num(v, suffix="") -> str:
        """Format a number with commas, or return N/A if None."""
        if v is None:
            return "N/A"
        try:
            return f"{int(v):,}{suffix}"
        except (TypeError, ValueError):
            return str(v)

    def fmt(meta: dict, label: str) -> str:
        er = meta.get("engagement_rate")
        er_str = f"{er:.2f}%" if er is not None else "N/A"
        return (
            f"Video {label}: {meta.get('title') or 'Unknown'} by {meta.get('creator') or 'Unknown'}\n"
            f"  Platform: {meta.get('platform') or 'unknown'} | "
            f"Views: {_fmt_num(meta.get('views'))} | "
            f"Likes: {_fmt_num(meta.get('likes'))} | "
            f"Comments: {_fmt_num(meta.get('comments'))}\n"
            f"  Engagement Rate: {er_str} | "
            f"Followers: {_fmt_num(meta.get('followers'))} | "
            f"Duration: {meta.get('duration') or 'N/A'}s | "
            f"Uploaded: {meta.get('upload_date') or 'N/A'}"
        )

    # Determine which video is stronger for the LLM context
    er_a = meta_a.get("engagement_rate")
    er_b = meta_b.get("engagement_rate")
    if er_a is not None and er_b is not None:
        performance_note = f"Video {'A' if er_a > er_b else 'B'} has a higher engagement rate ({er_a:.2f}% vs {er_b:.2f}%)."
    elif er_b is not None:
        performance_note = f"Video B has measurable engagement ({er_b:.2f}%). Video A's engagement cannot be calculated (no view data from Instagram)."
    elif er_a is not None:
        performance_note = f"Video A has measurable engagement ({er_a:.2f}%). Video B's engagement cannot be calculated."
    else:
        performance_note = "Neither video has computable engagement rate. Compare based on likes, comments, and content quality."

    return f"""You are HookIQ, an expert video content analyst. Your job is to help creators understand why videos perform differently and how to improve their content.

VIDEOS BEING COMPARED:
{fmt(meta_a, 'A')}

{fmt(meta_b, 'B')}

PERFORMANCE CONTEXT: {performance_note}

CITATION RULES (follow strictly):
- Cite every factual claim with [A-Chunk-N] or [B-Chunk-N]
- DO NOT add a "Sources:" section at the end — citations will be shown automatically in the UI
- If data is unavailable (e.g. Instagram views=N/A), say so clearly and base analysis on likes/comments/transcript instead

RETRIEVED TRANSCRIPT CONTEXT:
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
