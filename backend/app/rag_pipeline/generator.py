# rag_pipeline/generator.py
# This module builds a simple prompt and returns a string to pass to an LLM.
# Avoid importing LangChain prompt classes directly here to keep compatibility
# across different LangChain layouts (we only need a text prompt).

SYSTEM_PROMPT = """You are an expert in healthcare and medicinal information integrated into a Retrieval-Augmented Generation (RAG) system.

- Use ONLY the context provided from retrieved documents. Do not rely on outside knowledge.
- Always cite sources explicitly using [1], [2], etc., corresponding to the retrieved context chunks.
- Do NOT provide medical advice, diagnosis, or treatment instructions. Your role is informational only.
- If the context does not contain relevant information, respond clearly: "No relevant information found in retrieved sources."
- Keep answers concise, factual, and well-structured. Use short paragraphs or bullet points when appropriate.
- Maintain a neutral, professional tone. Avoid speculation or unsupported claims.
- If uncertain, state that clearly and suggest consulting a qualified healthcare professional.
"""

def make_prompt(query, context_docs):
    context = "\n\n".join(
        [
            f"[{i}] {doc.metadata.get('title','')} (id={doc.metadata.get('doc_id','')})\n{getattr(doc, 'page_content', getattr(doc, 'content', ''))}"
            for i, doc in enumerate(context_docs, 1)
        ]
    )
    return f"{SYSTEM_PROMPT}\n\nQuery: {query}\n\nContext:\n{context}\n\nAnswer with citations like [1], [2]."


def generate_answer(llm, query, docs):
    prompt = make_prompt(query, docs)
    # Different LLM wrappers have different call styles (llm(prompt), llm.invoke(prompt)).
    # Try the most common call patterns.
    try:
        return llm(prompt)
    except Exception:
        try:
            return llm.invoke(prompt)
        except Exception:
            # Fallback: if llm is a callable returning dict-like response
            try:
                out = llm(prompt)
                if isinstance(out, dict):
                    return out.get('text') or out.get('answer') or str(out)
                return str(out)
            except Exception:
                raise