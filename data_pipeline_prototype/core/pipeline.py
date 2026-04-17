class Pipeline:

    def __init__(self, provider, storage):
        self.provider = provider
        self.storage = storage

    async def run(self):
        raw = await self.provider.fetch()

        records = []
        for item in raw["features"]:
            props = item["properties"]
            records.append({
                "id": item["id"],
                "mag": props["mag"],
                "time": props["time"]
            })

        # dedup
        seen = set()
        deduped = []
        for r in records:
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(r)

        self.storage.save(deduped)
        return len(deduped)