from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

from db.models.base import MongoBase
from db.models.base import PyObjectId

T = TypeVar("T", bound=MongoBase)
""" Allows MongoBase inherited classes to work"""


class AbstractRepository(ABC, Generic[T]):
    """
    Read/write contract for a single MongoDB collection that it must follow.
    Allows only MongoBase inherited classes to work.
    Concrete implementations in repos/mongo/*.
    """

    @abstractmethod
    async def exists(self, filter_: dict) -> bool:
        """checks if the collection exists"""
        ...

    @abstractmethod
    async def insert(self, document: T) -> PyObjectId:
        """Persist a new document. Returns the inserted _id as str."""
        ...

    @abstractmethod
    async def find_by_id(self, doc_id: PyObjectId | str) -> Optional[T]:
        """Fetch one document by its _id. Returns None if not found."""
        ...

    @abstractmethod
    async def find_many(self, filter_: dict, limit: int = 100) -> list[T]:
        """Fetch documents matching filter_."""
        ...

    @abstractmethod
    async def update(self, doc_id: str, updates: dict) -> bool:
        """Patch fields on an existing document. Returns True if matched."""
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Hard-delete a document. Returns True if deleted."""
        ...

    @abstractmethod
    async def insert_many(self, documents: list[T]) -> list[PyObjectId]:
        """Insert multiple documents at once"""
        ...

    @abstractmethod
    async def count(self, filter_: dict) -> int:
        """Count the no of elements"""
        ...
