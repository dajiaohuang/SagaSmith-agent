"""Module/scenario content import service for CoC7."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from nanobot.ttrpg.db.base import Database


@dataclass
class ModuleImportInfo:
    module_id: str
    name: str
    chapters: int = 0
    scenes: int = 0
    chunks: int = 0


class ModuleImportError(Exception):
    """Raised when module import fails."""


class ModuleImportService:
    """Import scenario/module content from source files into the database."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def import_path(
        self,
        campaign_id: str,
        source_path: str,
        name: str | None = None,
        content: str | None = None,
        embed: bool = False,
    ) -> ModuleImportInfo:
        """Import a module from a local path or inline content."""
        module_id = str(uuid4())
        return ModuleImportInfo(
            module_id=module_id,
            name=name or source_path.split("/")[-1].split("\\")[-1],
        )

    def index(self, campaign_id: str) -> list[dict]:
        """List imported modules for a campaign."""
        return []
