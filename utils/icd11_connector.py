import requests
import time
from typing import List, Dict, Tuple


class ICD11TableBuilder:
    def __init__(self):
        self.base_url = "https://clinicaltables.nlm.nih.gov/api/icd11_codes/v3/search"
        self.session = requests.Session()

    def search_codes(self, terms: str = "", count: int = 500, offset: int = 0) -> Tuple[int, List[Dict]]:
        params = {
            "terms": terms,
            "count": count,
            "offset": offset,
            "ef": "code,title,definition,type,chapter",
        }
        RETRIES = 5
        for attempt in range(RETRIES):
            try:
                response = self.session.get(self.base_url, params=params, timeout=20)
                response.raise_for_status()

                data = response.json()
                total_count = data[0]
                codes = data[1]
                extra_data = data[2] if len(data) > 2 else {}

                records = []
                for i, code in enumerate(codes):
                    record = {"code": code}
                    for field in ["code", "title", "definition", "type", "chapter"]:
                        if field in extra_data and i < len(extra_data[field]):
                            record[field] = extra_data[field][i]
                        else:
                            record[field] = None
                    records.append(record)

                return total_count, records

            except Exception as e:
                print(f"[NIH] Error at offset {offset}, attempt {attempt+1}: {e}")
                time.sleep(1.5)  # backoff

        print(f"[NIH] FAILED permanently at offset {offset}")
        return 0, []

    def get_all_codes(self, max_records: int = None) -> List[Dict]:
        all_records = []
        offset = 0
        while True:
            if max_records and len(all_records) >= max_records:
                break
            total_count, records = self.search_codes(count=500, offset=offset)
            if not records:
                break
            all_records.extend(records)
            if len(records) < 500 or (max_records and len(all_records) >= max_records):
                break
            offset += len(records)
            time.sleep(0.1)
        return all_records
