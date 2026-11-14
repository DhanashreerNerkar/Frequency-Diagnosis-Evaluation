from typing import Dict, Any
from fastapi import HTTPException
from datetime import datetime

from config.db import mongodb
from config.collections import ONSPOT_DIAGNOSIS
from schemas.onspot_diagnosis_schema import OnspotDiagnosisCreate

def _coll():
    if mongodb.database is None:
        raise RuntimeError("Database not initialized. Did you call mongodb.connect()?")
    return mongodb.database[ONSPOT_DIAGNOSIS]

async def create_onspot_diagnosis(payload: OnspotDiagnosisCreate) -> Dict[str, Any]:
    coll = _coll()
    doc = {
        "case_id": payload.case_id,
        "diagnoses": [d.model_dump() for d in payload.diagnoses],
        "created_at": datetime.utcnow(),
    }

    await coll.update_one({"case_id": payload.case_id}, {"$set": doc}, upsert=True)

    saved = await coll.find_one({"case_id": payload.case_id})
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save on-spot diagnosis")

    saved["_id"] = str(saved["_id"])
    return saved

async def get_onspot_by_case(case_id: str) -> Dict[str, Any]:
    coll = _coll()
    doc = await coll.find_one({"case_id": case_id})
    if not doc:
        raise HTTPException(status_code=404, detail="On-spot diagnosis not found")
    doc["_id"] = str(doc["_id"])
    return doc

async def list_onspot_diagnoses(skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    coll = _coll()
    # sort newest first; tweak as you prefer
    cursor = coll.find({}, projection={"_id": 1, "case_id": 1, "diagnoses": 1, "created_at": 1}).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    for it in items:
        it["_id"] = str(it["_id"])
    total = await coll.count_documents({})
    return {
        "items": items,
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(items),
        },
    }