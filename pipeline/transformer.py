from models.schema import Record


def transform(raw_data):
    """
    Normalize raw USGS earthquake data into Record objects.
    """

    records = []

    for item in raw_data.get("features", []):
        props = item.get("properties", {})
        geometry = item.get("geometry", {})

        record = Record(
            record_id=item.get("id"),
            timestamp=props.get("time"),
            location=geometry.get("coordinates"),
            magnitude=props.get("mag"),
        )

        records.append(record)

    return records