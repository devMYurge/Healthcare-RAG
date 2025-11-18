"""DEPRECATED: rag_system module removed.

The implementation has been moved to `backend.app.rag_impl`.
Do not import from `backend.app.rag_system` — update your imports to:

	from backend.app.rag_impl import HealthcareRAG

This module raises an ImportError to prevent accidental usage of the old
path. Remove this file once all callers have been updated.
"""

raise ImportError(
	"backend.app.rag_system has been removed. Import HealthcareRAG from backend.app.rag_impl instead."
)
