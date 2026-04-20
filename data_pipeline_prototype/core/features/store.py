import sqlite3
import pandas as pd


class FeatureStore:
    def __init__(self, db_path="features.db"):
        self.conn = sqlite3.connect(db_path)

    def write(self, df: pd.DataFrame):
        df.to_sql("features", self.conn, if_exists="append", index=False)

    def read(self):
        return pd.read_sql("features", self.conn)
