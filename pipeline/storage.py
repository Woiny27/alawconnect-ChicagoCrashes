import json
import pandas as pd


def save_json(records, path="data/output.json"):
    with open(path, "w") as f:
        json.dump([r.to_dict() for r in records], f, indent=2)


def save_csv(records, path="data/output.csv"):
    df = pd.DataFrame([r.to_dict() for r in records])
    df.to_csv(path, index=False)