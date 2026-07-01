"""Campaign module retrieval services for CoC7."""
from .search import ModuleSearchService, ModuleSearchError, ModuleSearchHit
__all__ = ["ModuleSearchService", "ModuleSearchError", "ModuleSearchHit"]
