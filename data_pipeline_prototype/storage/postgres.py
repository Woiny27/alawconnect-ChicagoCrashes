import psycopg2
from storage.base import BaseStorage

class PostgresStorage(BaseStorage):

    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)

    def save(self, records):
        cur = self.conn.cursor()
        for r in records:
            cur.execute(
                "INSERT INTO earthquakes VALUES (%s, %s, %s)",
                (r["id"], r["mag"], r["time"])
            )
        self.conn.commit()