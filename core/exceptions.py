class NCERTRagError(Exception):
    """Root exception for the entire application."""


class DomainError(NCERTRagError):
    """Violation of a domain/business rule."""


class ValidationError(DomainError):
    """Input failed domain-level validation."""


class RepositoryError(NCERTRagError):
    """Database operation failed."""


class DocumentNotFoundError(RepositoryError):
    """Requested document does not exist."""

    def __init__(self, collection: str, identifier: str):
        super().__init__(f"Document not found in {collection}: {identifier}")
        self.collection = collection
        self.identifier = identifier


class DuplicateDocumentError(RepositoryError):
    """Insert would create a duplicate key."""

    def __init__(self, collection: str, key: str):
        super().__init__(f"Duplicate key in {collection}: {key}")
        self.collection = collection
        self.key = key


class ServiceError(NCERTRagError):
    """Business logic / orchestration failed."""


class IngestionError(ServiceError):
    """PDF ingestion pipeline failed."""

    def __init__(self, message: str, stage: str, page_no: int | None = None):
        super().__init__(message)
        self.stage = stage
        self.page_no = page_no


class ExtractionError(ServiceError):
    """LLM concept extraction failed."""
