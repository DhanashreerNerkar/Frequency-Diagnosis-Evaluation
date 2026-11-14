from fastapi import HTTPException
from schemas.accuracy_schema import AccuracyRequest
from config.db import mongodb
import math

ALPHA = 1
BETA = 1
GAMMA = 1
KAPPA = 1
COLLECTION_NAME = "ai_responses"
CONFIRMED_COLLECTION = "confirmed_response"
MODEL_ACCURACY_COLLECTION = "model_accuracy"
ACCURACY_SUMMARY_COLLECTION = "engine_accuracy_summary"

def parse_probability(p: str) -> float:
    return float(p.replace('%', '')) / 100 if p else 0

async def process_diagnosis(request, cid, confirmed, ent):
    diag = ent.get("diagnosis", "").strip().lower()
    icd = ent.get("icd11_code", "NULL")

    if request.disease and request.disease.lower() != diag:
        return None
    if request.icd11_code and request.icd11_code != icd:
        return None

    prob = parse_probability(ent.get("probability", "0%"))
    c = 1 if diag in confirmed else 0
    m = 1 if prob > 0 or c else 0
    F = c / m if m else 0
    TP, FP = prob * c, prob * (1 - c)
    invF = 1 / F if F else 0
    Pmean = prob if m else 0
    dPmTP = abs(Pmean - TP) if F else 1
    dPmF = 1 if not Pmean else abs(Pmean - F)
    dTPF = abs(TP - F) if c else 1
    dTPC = abs(prob - F) if c and prob else 1
    A = 0
    if TP and c:
        num = (
                ALPHA * (dTPC ** 2) +
                BETA * (dTPF ** 2) +
                GAMMA * (dPmF ** 2) +
                KAPPA * (dPmTP ** 2)
        )
        A = 1 - math.sqrt(num / (ALPHA + BETA + GAMMA + KAPPA))
    A_pct = round(A * 100, 2)

    existing = await mongodb.database[MODEL_ACCURACY_COLLECTION].find_one({
        "model_name": request.model_name,
        "case_id": cid,
        "diagnosis": diag
    })

    if existing:
        return None

    return {
        "model_name": request.model_name,
        "case_id": cid,
        "diagnosis": diag,
        "confirmed_diagnosis": confirmed,
        "icd11_code": icd,
        "probability": prob,
        "TP": TP, "FP": FP, "C": c, "M": m, "F": F,
        "1/F": invF, "P": prob, "Pmean": Pmean,
        "dPmTP": dPmTP, "dPmF": dPmF,
        "dTPF": dTPF, "dTPC": dTPC, "A": A_pct
    }

async def calculate_detailed_metrics(request: AccuracyRequest):
    try:
        filters = {}
        if request.model_name:filters["model_name"] = request.model_name
        if request.disease: filters["disease"] = request.disease
        if request.icd11_code: filters["icd11_code"] = request.icd11_code
        if request.start_date: filters["start_date"] = request.start_date
        if request.end_date: filters["end_date"] = request.end_date

        if not request.disease and not request.icd11_code and not request.start_date and not request.end_date:
            await mongodb.database[MODEL_ACCURACY_COLLECTION].delete_many({"model_name": request.model_name})

        q = {}
        if request.model_name:
            q["model_name"] = request.model_name
        if request.disease:
            q["diagnoses.diagnosis"] = {"$regex": request.disease, "$options": "i"}
        if request.icd11_code:
            q["diagnoses.icd11_code"] = request.icd11_code
        if request.start_date or request.end_date:
            q["dob"] = {}
            if request.start_date:
                q["dob"]["$gte"] = request.start_date
            if request.end_date:
                q["dob"]["$lte"] = request.end_date

        raw_docs = await mongodb.database[COLLECTION_NAME].find(q).to_list(length=None)
        if not raw_docs:
            raise HTTPException(status_code=404, detail="No AI response found for model and filters.")

        results = []
        for doc in raw_docs:
            cid = doc.get("case id")
            preds = doc.get("diagnoses", [])
            if not cid or not preds:
                continue

            conf_doc = await mongodb.database[CONFIRMED_COLLECTION].find_one({"case_id": cid})
            if not conf_doc or not conf_doc.get("confirmed_diagnosis"):
                continue
            confirmed = [c.lower() for c in conf_doc["confirmed_diagnosis"]]

            for ent in preds:
                record = await process_diagnosis(request, cid, confirmed, ent)
                if record:
                    await mongodb.database[MODEL_ACCURACY_COLLECTION].insert_one(record)
                    results.append(record)

        summary_query = {"model_name": request.model_name}
        if request.disease:
            summary_query["diagnosis"] = {"$regex": request.disease, "$options": "i"}
        if request.icd11_code:
            summary_query["icd11_code"] = request.icd11_code

        cached_records = await mongodb.database[MODEL_ACCURACY_COLLECTION].find(summary_query).to_list(length=None)
        sums = [(doc.get("diagnosis", ""), doc.get("A", 0), doc.get("F", 0)) for doc in cached_records]
        valid = [(d, A, F) for d, A, F in sums if A > 0 and F > 0]

        if not sums:
            raise HTTPException(status_code=404, detail="No accuracy records found.")

        simple_all = round(sum(A for _, A, _ in sums) / len(sums), 2)
        simple_valid = round(sum(A for _, A, _ in valid) / len(valid), 2) if valid else 0
        weighted = round(sum(A * (1 / F) for _, A, F in valid) / sum(1 / F for _, _, F in valid), 2) if valid else 0

        await mongodb.database[ACCURACY_SUMMARY_COLLECTION].insert_one({
            "model_name": request.model_name,
            "simple_accuracy_all": simple_all,
            "simple_accuracy_valid": simple_valid,
            "weighted_accuracy": weighted,
            **filters
        })

        return {
            "message": f"Stored {len(results)} new records (if any) and computed summary.",
            "simple_accuracy_all": {"points": simple_all, "percentage": f"{simple_all}%"},
            "simple_accuracy_valid": {"points": simple_valid, "percentage": f"{simple_valid}%"},
            "weighted_accuracy": {"points": weighted, "percentage": f"{weighted}%"},
            "filters_applied": filters,
            "cached": False
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
