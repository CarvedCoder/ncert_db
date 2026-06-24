from datetime import datetime
from typing import Any, Annotated
from zoneinfo import ZoneInfo
from bson.objectid import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer


def istnow() -> datetime:
    """factory for returning ist time"""
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def validate_object_id(value: Any) -> ObjectId:
    """validates it's an object id or else returns an ObjectId"""
    if isinstance(value, ObjectId):
        return value

    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError("Invalid ObjectId")


"""Used for validating objectids in python for model dumps"""
PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(func=str, return_type=str),
]


class MongoBase(BaseModel):
    """Base model that can be inherited"""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId | None = Field(default=None, alias="_id")

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_mongo(cls, data: dict[str, Any] | None):
        if data is None:
            return None

        return cls.model_validate(data)
