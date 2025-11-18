# rag_pipeline/generator.py
# This module builds a simple prompt and returns a string to pass to an LLM.
# Avoid importing LangChain prompt classes directly here to keep compatibility
# across different LangChain layouts (we only need a text prompt).

SYSTEM_PROMPT = """You are a healthcare information assistant. 
- Use ONLY the provided context to answer.
- Cite source titles and IDs.
- Do NOT provide medical advice, diagnosis, or treatment instructions.
- If uncertain, say so and suggest consulting a professional."""


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