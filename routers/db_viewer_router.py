from fastapi import APIRouter, HTTPException
from config.db import mongodb
from typing import Optional
import json

router = APIRouter(prefix="/api/v1/db", tags=["Database Viewer"])

@router.get("/collections")
async def list_collections():
    """List all collections in the database"""
    try:
        collections = await mongodb.database.list_collection_names()
        return {
            "database": mongodb.database.name,
            "collections": collections,
            "count": len(collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")


@router.get("/collections/{collection_name}")
async def view_collection(
    collection_name: str,
    limit: int = 50,
    skip: int = 0
):
    """View documents in a collection"""
    try:
        collection = mongodb.database[collection_name]
        
        total = await collection.count_documents({})
        
        cursor = collection.find({}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        
        return {
            "collection": collection_name,
            "total": total,
            "showing": len(documents),
            "skip": skip,
            "limit": limit,
            "documents": documents
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error viewing collection: {str(e)}")


@router.get("/collections/{collection_name}/count")
async def get_collection_count(collection_name: str):
    """Get count of documents in a collection"""
    try:
        collection = mongodb.database[collection_name]
        count = await collection.count_documents({})
        return {
            "collection": collection_name,
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting documents: {str(e)}")


@router.get("/collections/{collection_name}/stats")
async def get_collection_stats(collection_name: str):
    """Get statistics about a collection"""
    try:
        collection = mongodb.database[collection_name]
        
        total = await collection.count_documents({})
        
        sample = await collection.find_one({})
        
        if sample and '_id' in sample:
            sample['_id'] = str(sample['_id'])
        
        status_counts = {}
        if collection_name == "icd11_audit_lookup":
            pipeline = [
                {"$unwind": "$synonyms"},
                {"$group": {"_id": "$synonyms.status", "count": {"$sum": 1}}}
            ]
            status_results = await collection.aggregate(pipeline).to_list(length=None)
            status_counts = {item["_id"]: item["count"] for item in status_results}
        
        return {
            "collection": collection_name,
            "total_documents": total,
            "sample_document": sample,
            "status_counts": status_counts if status_counts else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")