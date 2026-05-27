import psycopg
from psycopg.rows import dict_row
import json


class CanBusLogPersistor:
    def __init__(self, dsn: str, schema: str = "public"):
        self.dsn = dsn
        self.schema = schema

    def _connect(self):
        conn = psycopg.connect(self.dsn, row_factory=dict_row)

        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {self.schema}")

        return conn

    @property
    def table(self):
        return f"{self.schema}.canbuslog"

    def create(self, timestamp, canid, frame_type, frame_format, data):
        sql = f"""
        INSERT INTO {self.table}
        ("timestamp", canid, frame_type, frame_format, data)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING *
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        timestamp,
                        canid,
                        frame_type,
                        frame_format,
                        json.dumps(data),
                    ),
                )
                return cur.fetchone()

    def add(self, can_message: dict):
        """
        Inserts CAN JSON like:

        {
            "timeStamp": "...",
            "canId": "0x45a",
            "dlc": 8,
            "data": [...],
            "frameType": "Standard Frame",
            "frameFormat": "Data Frame",
            "raw": "..."
        }
        """

        return self.create(
            timestamp=can_message.get("timeStamp"),
            canid=can_message.get("canId"),
            frame_type=can_message.get("frameType"),
            frame_format=can_message.get("frameFormat"),
            data=can_message.get("data"),
        )

    def get_all(self, limit=100, offset=0):
        sql = """
        SELECT *
        FROM public.canbuslog
        ORDER BY "timestamp" DESC
        LIMIT %s OFFSET %s
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (limit, offset))
                return cur.fetchall()

    def get_by_canid(self, canid: str):
        sql = """
        SELECT *
        FROM public.canbuslog
        WHERE canid = %s
        ORDER BY "timestamp" DESC
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (canid,))
                return cur.fetchall()

    def get_one(self, timestamp: str, canid: str):
        sql = """
        SELECT *
        FROM public.canbuslog
        WHERE "timestamp" = %s AND canid = %s
        LIMIT 1
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (timestamp, canid))
                return cur.fetchone()

    def update(self, timestamp: str, canid: str, updates: dict):
        allowed_columns = {
            "timestamp": '"timestamp"',
            "canid": "canid",
            "frame_type": "frame_type",
            "frame_format": "frame_format",
            "data": "data",
        }

        set_parts = []
        values = []

        for key, value in updates.items():
            if key not in allowed_columns:
                raise ValueError(f"Invalid column: {key}")

            if key == "data":
                set_parts.append(f"{allowed_columns[key]} = %s::jsonb")
                values.append(json.dumps(value))
            else:
                set_parts.append(f"{allowed_columns[key]} = %s")
                values.append(value)

        if not set_parts:
            raise ValueError("No updates provided")

        values.extend([timestamp, canid])

        sql = f"""
        UPDATE public.canbuslog
        SET {", ".join(set_parts)}
        WHERE "timestamp" = %s AND canid = %s
        RETURNING *
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                return cur.fetchone()

    def delete(self, timestamp: str, canid: str):
        sql = """
        DELETE FROM public.canbuslog
        WHERE "timestamp" = %s AND canid = %s
        RETURNING *
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (timestamp, canid))
                return cur.fetchone()
           