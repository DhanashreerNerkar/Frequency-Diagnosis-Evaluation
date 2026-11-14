from fastapi import HTTPException
from datetime import datetime
import traceback
import math

from config.db import mongodb
from schemas.responses import GenericResponse
from schemas.exceptions import ExceptionHandler

from utils.icd11_connector import ICD11TableBuilder


class StandardICDController:

    def __init__(self):
        self.COLLECTION = "standard_icd_11"
        self.exception_handler = ExceptionHandler()
        self.nih = ICD11TableBuilder()
    async def build_standard_icd_collection(self):

        try:
            print("\n[INFO] Fetching NIH ICD-11 codes...")

            nih_total, first_batch = self.nih.search_codes(count=500)
            if not first_batch:
                raise HTTPException(status_code=502, detail="NIH returned no records")

            nih_records = first_batch
            offset = len(first_batch)

            while offset < nih_total:
                _, batch = self.nih.search_codes(count=500, offset=offset)
                if not batch:
                    break
                nih_records.extend(batch)
                offset += len(batch)

            print(f"[INFO] NIH loaded: {len(nih_records)} codes")

            nih_dict = {}
            for rec in nih_records:
                code = rec.get("code")
                if not code:
                    continue

                title = rec.get("title") or rec.get("definition")
                if not title:
                    continue

                nih_dict[code] = title

            if not nih_dict:
                raise HTTPException(status_code=500, detail="NIH returned unusable data")

            print("[INFO] Merging NIH names...")

            merged = []
            for code, nih_name in nih_dict.items():
                merged.append({
                    "code": code,
                    "names": [nih_name],
                    "source": ["NIH"],
                    "last_updated": datetime.utcnow().isoformat()
                })

            print(f"[INFO] Final merged count: {len(merged)}")
            await mongodb.database[self.COLLECTION].delete_many({})

            CHUNK = 500
            total = len(merged)
            pages = math.ceil(total / CHUNK)

            for i in range(pages):
                start = i * CHUNK
                end = start + CHUNK
                chunk = merged[start:end]
                print(f"[INFO] inserting chunk {i+1}/{pages} ({len(chunk)} docs)")
                await mongodb.database[self.COLLECTION].insert_many(chunk)

            print("[INFO] Triggering Lookup Table refresh...")
            from controllers.lookup_controller import AuditLookupController
            audit = AuditLookupController()
            refresh_result = await audit.refresh_lookup_from_standard()

            return GenericResponse(
                success=True,
                message="Standard ICD-11 table rebuilt and Lookup table refreshed",
                data={
                    "standard_count": len(merged),
                    "lookup_inserted": refresh_result["inserted"],
                    "lookup_updated": refresh_result["updated"]
                }
            )

        except Exception as e:
            print("ERROR in build_standard_icd_collection:", e)
            traceback.print_exc()
            self.exception_handler.handle_exception(e)

    async def fetch_standard_codes(self, limit: int = 50):
        cursor = mongodb.database[self.COLLECTION].find({}, {"_id": 0}).limit(limit)
        data = await cursor.to_list(length=limit)
        return GenericResponse(success=True, data=data)
    async def search_code(self, code: str):
        doc = await mongodb.database[self.COLLECTION].find_one({"code": code}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Code not found")
        return GenericResponse(success=True, data=doc)


icd_controller = StandardICDController()
