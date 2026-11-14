from config.db import mongodb
from fastapi import HTTPException
from config.collections import CONFIRMED_COLLECTION, CASES_COLLECTION

class DiagnosisController:
    def __init__(self):
        self.confirmed_collection = CONFIRMED_COLLECTION
        self.cases_collection = CASES_COLLECTION


    async def update_confirmed_diagnosis(self, case_id: str, confirmed_diagnosis: list):
        try:
            await mongodb.database[self.confirmed_collection].update_one(
                {"case_id": case_id},
                {"$set": {"confirmed_diagnosis": confirmed_diagnosis}},
                upsert=True
            )
            updated_case = await mongodb.database[self.confirmed_collection].find_one(
                {"case_id": case_id}, {"_id": 0}
            )

            await mongodb.database[self.cases_collection].update_one(
                {"case_id": case_id},
                {"$set": {"confirmed_diagnosis": True}}
            )

            return updated_case

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update confirmed diagnosis: {str(e)}")
