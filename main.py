import asyncio

from repos.mongo.media_asset_repo import (
    MediaAssetRepository,
)
from services.storage.minio_service import (
    MinioStorageService,
)

OBJECT_ID = "6a3997eeb2942a34db90da8b"


async def main():
    repo = MediaAssetRepository()

    storage = MinioStorageService()

    asset = await repo.find_by_id(OBJECT_ID)

    if asset is None:
        print("Not found")
        return

    storage.delete(asset.object_key)

    await repo.delete(OBJECT_ID)

    print("Deleted")


if __name__ == "__main__":
    asyncio.run(main())
