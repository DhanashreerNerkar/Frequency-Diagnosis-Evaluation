class CacheClient:

    async def push_updates(self, cleared_synonyms):

        print("[CACHE] Received cleared/wrong synonyms:", len(cleared_synonyms))
        # Push updated synonym statuses (cleared/wrong) to Aggregation Cach
        return True

    async def get_new_synonyms(self):

        # Fetch NEW synonyms created by Aggregation/Super-Learner.
        return []
