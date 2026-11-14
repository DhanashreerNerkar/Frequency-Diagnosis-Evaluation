import math

from config.db import mongodb
from fastapi import HTTPException
from utils.cache_client import CacheClient
from pymongo import UpdateOne, InsertOne
from datetime import datetime, timedelta

class InMemoryLockManager:
    def __init__(self):
        self.active_locks = {}
        self.lock_timeout_seconds = 30
    
    def try_lock(self, icd11_code, synonym_id, reviewer_id):
        key = (icd11_code, synonym_id)
        now = datetime.utcnow()
        
        if key in self.active_locks:
            lock_info = self.active_locks[key]
            locked_at = datetime.fromisoformat(lock_info["locked_at"])
            
            if now - locked_at > timedelta(seconds=self.lock_timeout_seconds):
                del self.active_locks[key]
            else:
                if lock_info["reviewer_id"] != reviewer_id:
                    return False, "Item is being reviewed by another user"
                else:
                    self.active_locks[key]["locked_at"] = now.isoformat()
                    return True, None
        
        self.active_locks[key] = {
            "reviewer_id": reviewer_id,
            "locked_at": now.isoformat()
        }
        return True, None
    
    def release_lock(self, icd11_code, synonym_id):
        key = (icd11_code, synonym_id)
        if key in self.active_locks:
            del self.active_locks[key]
    
    def cleanup_expired_locks(self):
        now = datetime.utcnow()
        expired_keys = [
            key for key, lock_info in self.active_locks.items()
            if now - datetime.fromisoformat(lock_info["locked_at"]) > timedelta(seconds=self.lock_timeout_seconds)
        ]
        for key in expired_keys:
            del self.active_locks[key]
        return len(expired_keys)


class AuditLookupController:

    def __init__(self):
        self.audit_collection = "icd11_audit_lookup"
        self.standard_collection = "standard_icd_11"
        self.cache = CacheClient()
        self.lock_manager = InMemoryLockManager()  

    @property
    def db(self):
        return mongodb.database

    async def create_lookup(self, payload):
        existing = await self.db[self.audit_collection].find_one(
            {"icd11_code": payload.icd11_code}
        )
        if existing:
            raise HTTPException(status_code=400, detail="ICD11 code already exists")

        doc = {
            "icd11_code": payload.icd11_code,
            "standard_diagnoses": payload.standard_diagnoses,
            "created_timestamp": payload.created_timestamp,
            "updated_timestamp": payload.created_timestamp,
            "status": "new",
            "synonyms": []
        }

        await self.db[self.audit_collection].insert_one(doc)
        return doc

    async def get_lookup_entries(self, query):
        mongo_query = {}

        if query.icd11_code:
            mongo_query["icd11_code"] = query.icd11_code
        if query.status:
            mongo_query["status"] = query.status
        if query.updated_after:
            mongo_query["updated_timestamp"] = {"$gt": query.updated_after}

        skip = (query.page - 1) * query.limit

        audit_docs = await self.db[self.audit_collection].find(
            mongo_query
        ).skip(skip).limit(query.limit).to_list(length=None)

        results = []

        for doc in audit_docs:
            icd_code = doc["icd11_code"]

            standard = await self.db[self.standard_collection].find_one({"code": icd_code})

            results.append({
                "icd11_code": icd_code,
                "standard_diagnoses": standard.get("names", []) if standard else doc["standard_diagnoses"],
                "synonyms": doc.get("synonyms", []),
                "status": doc.get("status"),
                "created_timestamp": doc.get("created_timestamp"),
                "updated_timestamp": doc.get("updated_timestamp")
            })

        return results

    async def add_synonym(self, icd11_code, payload):

        record = await self.db[self.audit_collection].find_one({"icd11_code": icd11_code})
        if not record:
            raise HTTPException(status_code=404, detail="ICD11 code not found")

        existing_ids = [s["synonym_id"] for s in record.get("synonyms", [])]
        new_id = (max(existing_ids) + 1) if existing_ids else 1

        synonym = {
            "synonym_id": new_id,
            "text": payload.synonymous_diagnosis,
            "status": payload.status,
            "added_timestamp": payload.added_timestamp
        }

        await self.db[self.audit_collection].update_one(
            {"icd11_code": icd11_code},
            {
                "$push": {"synonyms": synonym},
                "$set": {"updated_timestamp": datetime.utcnow().isoformat()}
            }
        )

        return synonym

    async def update_synonym_status(self, icd11_code, synonym_id, payload):

        result = await self.db[self.audit_collection].update_one(
            {"icd11_code": icd11_code, "synonyms.synonym_id": int(synonym_id)},
            {
                "$set": {
                    "synonyms.$.status": payload.status,
                    "synonyms.$.reviewed_by": payload.reviewed_by,
                    "updated_timestamp": datetime.utcnow().isoformat()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Synonym not found")

        return {"message": "Synonym status updated"}

    async def get_pending_synonyms(self, page, limit):
        skip = (page - 1) * limit

        cursor = self.db[self.audit_collection].aggregate([
            {"$unwind": "$synonyms"},
            {"$match": {"synonyms.status": "new"}},
            {
                "$project": {
                    "_id": 0,
                    "id": "$synonyms.synonym_id",
                    "icd11_code": "$icd11_code",
                    "synonym": "$synonyms.text",
                    "standard_diagnoses": "$standard_diagnoses",
                    "status": "$synonyms.status"
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ])

        return await cursor.to_list(length=None)

    async def get_synonyms_by_status(self, status: str, page: int, limit: int, search: str = None):
        skip = (page - 1) * limit

        match_stage = {}
        if status != "all":
            match_stage["synonyms.status"] = status
        
        # Add search filter
        if search:
            match_stage["$or"] = [
                {"icd11_code": {"$regex": search, "$options": "i"}},
                {"synonyms.text": {"$regex": search, "$options": "i"}}
            ]

        cursor = self.db[self.audit_collection].aggregate([
            {"$unwind": "$synonyms"},
            {"$match": match_stage},

            # WHO lookup
            {
                "$lookup": {
                    "from": self.standard_collection,
                    "let": {"icd_code": "$icd11_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$code", "$$icd_code"]},
                                        {"$in": ["WHO", "$source"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "who_info"
                }
            },

            # NIH lookup
            {
                "$lookup": {
                    "from": self.standard_collection,
                    "let": {"icd_code": "$icd11_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$code", "$$icd_code"]},
                                        {"$in": ["NIH", "$source"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "nih_info"
                }
            },

            {
                "$project": {
                    "_id": 0,
                    "synonym_id": "$synonyms.synonym_id",
                    "icd11_code": "$icd11_code",
                    "synonym_text": "$synonyms.text",
                    "status": "$synonyms.status",
                    "reviewed_by": "$synonyms.reviewed_by",
                    "updated_timestamp": "$synonyms.updated_timestamp",
                    "who_info": {"$arrayElemAt": ["$who_info", 0]},
                    "nih_info": {"$arrayElemAt": ["$nih_info", 0]},
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ])

        results = await cursor.to_list(length=None)

        items = []
        for r in results:
            who = r.get("who_info") or {}
            nih = r.get("nih_info") or {}

            items.append({
                "synonym_id": r["synonym_id"],
                "icd11_code": r["icd11_code"],
                "synonym_text": r["synonym_text"],
                "status": r["status"],
                "reviewed_by": r.get("reviewed_by"),
                "updated_timestamp": r.get("updated_timestamp"),
                "who_code": who.get("code", "N/A"),
                "who_diagnosis": (who.get("names") or ["WHO data not available"])[0],
                "nih_code": nih.get("code", "N/A"),
                "nih_diagnosis": (nih.get("names") or ["NIH data not available"])[0],
            })

        count_pipeline = [
            {"$unwind": "$synonyms"},
            {"$match": match_stage},
            {"$count": "total"}
        ]
        
        count_result = await self.db[self.audit_collection].aggregate(count_pipeline).to_list(length=1)
        total = count_result[0]["total"] if count_result else 0

        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": math.ceil(total / limit) if total else 0
        }


    async def sync_to_cache(self):
        cleared = await self.db[self.audit_collection].aggregate([
            {"$unwind": "$synonyms"},
            {"$match": {"synonyms.status": {"$in": ["cleared", "wrong"]}}},
            {
                "$project": {
                    "_id": 0,
                    "icd11_code": "$icd11_code",
                    "synonym_id": "$synonyms.synonym_id",
                    "text": "$synonyms.text",
                    "status": "$synonyms.status"
                }
            }
        ]).to_list(length=None)

        await self.cache.push_updates(cleared)

        return {
            "synonyms_sent_to_cache": len(cleared),
            "details": cleared
        }

    async def sync_from_cache(self):
        new_synonyms = await self.cache.get_new_synonyms()

        added = 0
        for item in new_synonyms:
            await self.add_synonym(
                item["icd11_code"],
                payload=type("obj", (object,), {
                    "synonymous_diagnosis": item["text"],
                    "status": "new",
                    "added_timestamp": datetime.utcnow().isoformat()
                })
            )
            added += 1

        return {
            "new_synonyms_added": added,
            "details": new_synonyms
        }

    async def refresh_lookup_from_standard(self):

        standard_docs = await self.db[self.standard_collection].find({}).to_list(length=None)

        bulk_ops = []
        inserted = 0
        updated = 0

        # Convert standard docs to dictionary for fast lookup
        std_map = {doc["code"]: doc.get("names", []) for doc in standard_docs}

        # Fetch existing lookup entries
        lookup_docs = await self.db[self.audit_collection].find({}).to_list(length=None)
        lookup_map = {doc["icd11_code"]: doc for doc in lookup_docs}

        for icd_code, std_names in std_map.items():
            if icd_code not in lookup_map:

                bulk_ops.append(
                    InsertOne({
                        "icd11_code": icd_code,
                        "standard_diagnoses": std_names,
                        "synonyms": [],
                        "created_timestamp": datetime.utcnow().isoformat(),
                        "updated_timestamp": datetime.utcnow().isoformat()
                    })
                )
                inserted += 1

            else:

                existing_std = lookup_map[icd_code].get("standard_diagnoses", [])

                if sorted(existing_std) != sorted(std_names):
                    bulk_ops.append(
                        UpdateOne(
                            {"icd11_code": icd_code},
                            {
                                "$set": {
                                    "standard_diagnoses": std_names,
                                    "updated_timestamp": datetime.utcnow().isoformat()
                                }
                            }
                        )
                    )
                    updated += 1

        if bulk_ops:
            await self.db[self.audit_collection].bulk_write(bulk_ops)

        return {
            "inserted": inserted,
            "updated": updated,
            "message": "Lookup table synced using bulk write"
        }

    async def get_new_synonyms_for_review(self, page: int = 1, limit: int = 100, search: str = None):
        """
        Fetch new synonyms with WHO and NIH standardized diagnoses
        """
        self.lock_manager.cleanup_expired_locks()
        await self.sync_from_cache()

        skip = (page - 1) * limit
        
        # Build match stage with search filter
        match_stage = {"synonyms.status": "new"}
        if search:
            match_stage["$or"] = [
                {"icd11_code": {"$regex": search, "$options": "i"}},
                {"synonyms.text": {"$regex": search, "$options": "i"}}
            ]

        cursor = self.db[self.audit_collection].aggregate([
            {"$unwind": "$synonyms"},
            {"$match": match_stage},
            # Lookup WHO data
            {
                "$lookup": {
                    "from": self.standard_collection,
                    "let": {"icd_code": "$icd11_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$code", "$$icd_code"]},
                                        {"$in": ["WHO", "$source"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "who_info"
                }
            },
            # Lookup NIH data
            {
                "$lookup": {
                    "from": self.standard_collection,
                    "let": {"icd_code": "$icd11_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$code", "$$icd_code"]},
                                        {"$in": ["NIH", "$source"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "nih_info"
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "synonym_id": "$synonyms.synonym_id",
                    "icd11_code": "$icd11_code",
                    "synonym_text": "$synonyms.text",
                    "who_info": {"$arrayElemAt": ["$who_info", 0]},
                    "nih_info": {"$arrayElemAt": ["$nih_info", 0]},
                    "added_timestamp": "$synonyms.added_timestamp",
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ])

        results = await cursor.to_list(length=None)

        review_items = []
        for item in results:
            who_info = item.get("who_info", {})
            nih_info = item.get("nih_info", {})
            code = item["icd11_code"]
        
            who_names = who_info.get("names", [])
            who_code = who_info.get("code", "N/A") if who_info else "N/A" 
            who_diagnosis = who_names[0] if who_names else "WHO data not available"

            nih_names = nih_info.get("names", [])
            nih_code = nih_info.get("code", "N/A") if nih_info else "N/A"  
            nih_diagnosis = nih_names[0] if nih_names else "NIH data not available"
        
            review_items.append({
                "synonym_id": item["synonym_id"],
                "icd11_code": code,
                "synonym_text": item["synonym_text"],
            
                "who_code": who_code,
                "who_diagnosis": who_diagnosis,
            
                "nih_code": nih_code,
                "nih_diagnosis": nih_diagnosis,
            
                "source": "cache",
                "added_timestamp": item.get("added_timestamp"),
            })
        
        count_pipeline = [
            {"$unwind": "$synonyms"},
            {"$match": match_stage},
            {"$count": "total"}
        ]
        
        count_result = await self.db[self.audit_collection].aggregate(count_pipeline).to_list(length=1)
        total_count = count_result[0]["total"] if count_result else 0

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 0

        return {
            "items": review_items,
            "page": page,
            "limit": limit,
            "total": total_count,
            "total_pages": total_pages
        }

    async def doctor_review_synonym(self, payload):
        """
        Doctor reviews a synonym and marks it as correct or wrong.
        """
        icd11_code = payload.icd11_code
        synonym_id = payload.synonym_id
        action = payload.action.lower()  
        reviewed_by = payload.reviewed_by
        
        if action not in ["correct", "wrong"]:
            raise HTTPException(
                status_code=400, 
                detail="Action must be 'correct' or 'wrong'"
            )
        
        success, error = self.lock_manager.try_lock(icd11_code, synonym_id, reviewed_by)
        if not success:
            raise HTTPException(status_code=409, detail=error)
        
        try:
            status = "cleared" if action == "correct" else "wrong"
            
            record = await self.db[self.audit_collection].find_one(
                {"icd11_code": icd11_code}
            )
            
            if not record:
                raise HTTPException(status_code=404, detail="ICD11 code not found")
            
            synonym = next(
                (s for s in record.get("synonyms", []) if s.get("synonym_id") == synonym_id),
                None
            )
            
            if not synonym:
                raise HTTPException(status_code=404, detail="Synonym not found")
            
            # Allow editing of any status (removed the status check)
            
            update_data = {
                "synonyms.$.status": status,
                "synonyms.$.reviewed_by": reviewed_by,
                "updated_timestamp": datetime.utcnow().isoformat(),
                "synonyms.$.action": action,
                "synonyms.$.updated_timestamp": datetime.utcnow().isoformat()
            }
            
            if payload.notes:
                update_data["synonyms.$.notes"] = payload.notes
            
            result = await self.db[self.audit_collection].update_one(
                {"icd11_code": icd11_code, "synonyms.synonym_id": synonym_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Synonym not found")
            
            return {
                "message": f"Synonym marked as {action} successfully",
                "icd11_code": icd11_code,
                "synonym_id": synonym_id,
                "status": status,
                "reviewed_by": reviewed_by
            }
        
        finally:
            self.lock_manager.release_lock(icd11_code, synonym_id)
            
    async def doctor_review_synonyms_batch(self, payload):

        reviewed_by = payload.reviewed_by
        results = {"successful": 0, "failed": 0, "errors": []}
    
        for item in payload.items:
            try:
                success, error = self.lock_manager.try_lock(
                    item.icd11_code, 
                    item.synonym_id, 
                    reviewed_by
                )
            
                if not success:
                    results["failed"] += 1
                    results["errors"].append({
                        "icd11_code": item.icd11_code,
                        "synonym_id": item.synonym_id,
                       "error": error
                    })
                    continue
            
                try:
                    status = "cleared" if item.action.lower() == "correct" else "wrong"
                
                    record = await self.db[self.audit_collection].find_one(
                        {"icd11_code": item.icd11_code}
                    )
                
                    if not record:
                        results["failed"] += 1
                        results["errors"].append({
                            "icd11_code": item.icd11_code,
                            "synonym_id": item.synonym_id,
                            "error": "ICD11 code not found"
                        })
                        continue
                
                    synonym = next(
                        (s for s in record.get("synonyms", []) 
                         if s.get("synonym_id") == item.synonym_id),
                        None
                    )
                
                    if not synonym:
                        results["failed"] += 1
                        results["errors"].append({
                            "icd11_code": item.icd11_code,
                            "synonym_id": item.synonym_id,
                            "error": "Synonym not found"
                        })
                        continue
                
                    # Allow editing of any status (removed the status check)
                
                    update_data = {
                        "synonyms.$.status": status,
                       "synonyms.$.reviewed_by": reviewed_by,
                        "synonyms.$.action": item.action,
                        "synonyms.$.updated_timestamp": datetime.utcnow().isoformat(),
                        "updated_timestamp": datetime.utcnow().isoformat()
                    }
                
                    if payload.notes:
                        update_data["synonyms.$.notes"] = payload.notes
                
                    result = await self.db[self.audit_collection].update_one(
                        {"icd11_code": item.icd11_code, "synonyms.synonym_id": item.synonym_id},
                        {"$set": update_data}
                    )
                
                    if result.matched_count > 0:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                    
                finally:
                    self.lock_manager.release_lock(item.icd11_code, item.synonym_id)
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "icd11_code": item.icd11_code,
                    "synonym_id": item.synonym_id,
                    "error": str(e)
                })
    
        return results