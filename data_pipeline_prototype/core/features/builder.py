import pandas as pd


class FeatureBuilder:

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:

        df = df.copy()

        # ----------------------------
        # Clean inputs (REAL WORLD DATA)
        # ----------------------------
        df["lat"] = pd.to_numeric(df.get("lat"), errors="coerce")
        df["lon"] = pd.to_numeric(df.get("lon"), errors="coerce")

        # ----------------------------
        # Time features
        # ----------------------------
        df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
        df["hour"] = df["timestamp"].dt.hour.fillna(-1)

        df["is_night"] = df["hour"].apply(
            lambda x: 1 if x != -1 and (x < 6 or x > 20) else 0
        )

        # ----------------------------
        # Missing data signals (VERY IMPORTANT IN REAL SYSTEMS)
        # ----------------------------
        df["missing_location"] = df.apply(
            lambda r: 1 if pd.isna(r["lat"]) or pd.isna(r["lon"]) else 0,
            axis=1
        )

        return df
