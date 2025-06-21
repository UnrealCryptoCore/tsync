import sqlite3
import bcrypt
import uuid
import sys
import os
from dotenv import load_dotenv

load_dotenv()

salt = os.getenv('SALT').encode("utf-8")


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

    cur.execute(
        "CREATE TABLE user(id CHAR(36), username VARCHAR(63), passhash CHAR(60), admin BOOL, api_key CHAR(32))")

    cur.execute(
        "CREATE TABLE etest(id CHAR(36), ttype VARCHAR(255), name VARCHAR(255))")
    cur.execute(
        "CREATE TABLE top_question(id CHAR(36), tid CHAR(36), user_id VARCHAR(63), question VARCHAR(1023), html_question VARCHAR(2047))")
    cur.execute(
        "CREATE TABLE question(id CHAR(36), topid CHAR(36), user_id CHAR(36), question VARCHAR(1024),html_question TEXT)")
    cur.execute(
        "CREATE TABLE answer(id CHAR(36), tid CHAR(36), q_id CHAR(36), user_id CHAR(36), answer VARCHAR(511), sort_id INTEGER)")

    add_user("admin", "admin", True)
    add_user("test", "test", False)


def add_user(username, password, admin=False):
    con = sqlite3.connect("tsync.db")
    cur = con.cursor()

    id = str(uuid.uuid4())
    hash = bcrypt.hashpw(password.encode("utf-8"), salt)
    cur.execute("INSERT INTO user (id, username, passhash, admin) VALUES (?, ?, ?, ?)",
                (id, username, hash, admin))
    con.commit()


if __name__ == "__main__":
    main()
