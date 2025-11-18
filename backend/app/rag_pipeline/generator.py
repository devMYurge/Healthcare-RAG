# rag_pipeline/generator.py
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage
# Example: use transformers pipeline for local LLM, or LangChain's LLM wrappers

SYSTEM_PROMPT = """You are a healthcare information assistant. 
- Use ONLY the provided context to answer.
- Cite source titles and IDs.
- Do NOT provide medical advice, diagnosis, or treatment instructions.
- If uncertain, say so and suggest consulting a professional."""

def make_prompt(query, context_docs):
    context = "\n\n".join([f"[{i}] {doc.metadata.get('title','')} (id={doc.metadata.get('doc_id','')})\n{doc.page_content}" 
                           for i, doc in enumerate(context_docs, 1)])
    return f"{SYSTEM_PROMPT}\n\nQuery: {query}\n\nContext:\n{context}\n\nAnswer with citations like [1], [2]."

def generate_answer(llm, query, docs):
    prompt = make_prompt(query, docs)
    return llm.invoke(prompt)  # or llm(prompt) depending on interface