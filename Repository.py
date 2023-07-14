import sqlite3


class Repository():
    def __init__(self, db_location):
        self.connection = db_location

    def create_table(self):
        cur = self.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS players_data
            username    STRING  NOT NULL,
            password    STRING  NOT NULL,
            score       INTEGER,
            is_creator  BOOLEAN,
            id          INTEGER PRIMARY KEY NOT NULL,
            sid         STRING""")
        cur.close()

    def close_db(self):
        self.connection.commit()
        self.connection.close()

    def update_player_sid(self, sid: str, player_id: int):
        cur = self.connection.cursor()
        cmd = """
            UPDATE players_data 
            SET sid = ? WHERE id = ?
        """
        cur.execute(cmd, sid, player_id)
        cur.close()

    def get_max_id(self):
        cur = self.connection.cursor()
        cmd = "SELECT MAX(id) FROM players_data"
        cur.execute(cmd)
        max_id = cur.fetchone()
        cur.close()
        return max_id[0]

    def add_player(self, username: str, password: str, is_creator: bool,
                   player_id: int, sid: str = None):
        cur = self.connection.cursor()
        cmd = """
            INSERT INTO players_data
            (username, password, score, is_creator, id, sid)
            VALUES(?, ?, ?, ?, ?, ?)
        """
        cur.execute(cmd, username, password, 0, is_creator, player_id, sid)
        cur.close()

    def username_exists(self, username: str) -> bool:
        """
        check if username exists in the db
        :param username: a name of a user
        """
        cur = self.connection.cursor()
        cmd = "SELECT username FROM players_data WHERE username = ?"
        cur.execute(cmd, username)
        res = cur.fetchone()
        cur.close()
        return res is not None
