import sqlite3
import bcrypt
import uuid
import sys
import os
from dotenv import load_dotenv

load_dotenv()

pepper = os.getenv('PEPPER').encode("utf-8")
ai_username = os.getenv('AI_USERNAME')


def main():
    if len(sys.argv) <= 1:
        return

    cmd = sys.argv[1]
    if cmd == "setup":
        setup_db()
        return
    if cmd == "user" and len(sys.argv) == 4:
        add_user(sys.argv[2], sys.argv[3])
        return
    if cmd == "exec" and len(sys.argv) == 3:
        print(sys.argv[2])
        print(execute(sys.argv[2]))
        return
    if cmd == "reset":
        os.remove("tsync.db")
        setup_db()
        return
    print(f"could not find cmd {cmd}")


def execute(cmd):
    con = sqlite3.connect("tsync.db")
    cur = con.cursor()

    res = cur.execute(cmd)
    res = res.fetchall()
    con.commit()
    return res


def setup_db():
    con = sqlite3.connect("tsync.db")
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE user(
            id CHAR(36),
            username VARCHAR(64),
            passhash CHAR(60),
            type VARCHAR(16),
            api_key CHAR(32),
            PRIMARY KEY (id))
        """)

    cur.execute("""
        CREATE TABLE answer_v2(
            cmid VARCHAR(255),
            id VARCHAR(255),
            user_id CHAR(36),
            hash INTEGER,
            text VARCHAR(255),
            value VARCHAR(255),
            type VARCHAR(32),
            PRIMARY KEY (cmid, id, user_id))
        """)

    cur.execute("""
        CREATE TABLE question_v2(
            id INTEGER,
            question TEXT,
            PRIMARY KEY (id))
        """)

    cur.execute("""
        CREATE TABLE etest_v2(
            cmid VARCHAR(255),
            user_id CHAR(36),
            name VARCHAR(255),
            html TEXT,
            PRIMARY KEY (cmid, user_id))
        """)

    add_user("admin", "admin", "admin")
    add_user("test", "test")
    add_user(ai_username, ai_username, "ai")


def add_user(username, password, userType="user"):
    con = sqlite3.connect("tsync.db")
    cur = con.cursor()

    id = str(uuid.uuid4())
    hash = bcrypt.hashpw(password.encode("utf-8"), pepper)
    cur.execute("INSERT INTO user (id, username, passhash, type) VALUES (?, ?, ?, ?)",
                (id, username, hash, userType))
    con.commit()


if __name__ == "__main__":
    main()
