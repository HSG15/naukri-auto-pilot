import sqlite3
#===========================sqlite support for nkparam token ===============
class NkparamDB:
    def __init__(self, db_path="nkparams.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nkparams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nkparam TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
        """)

        conn.commit()
        conn.close()


    def add_nkparam(self, nkparam):
        conn = self._connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT OR IGNORE INTO nkparams (nkparam, is_active) VALUES (?, 1)",
                (nkparam,)
            )
            conn.commit()
        finally:
            conn.close()


    def get_nkparam(self):
        conn = self._connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, nkparam 
                FROM nkparams 
                WHERE is_active = 1 
                LIMIT 1
            """)
            row = cursor.fetchone()

            if row:
                nk_id, nkparam = row

                cursor.execute(
                    "UPDATE nkparams SET is_active = 0 WHERE id = ?",
                    (nk_id,)
                )
                conn.commit()

                return nkparam

            return None

        finally:
            conn.close()