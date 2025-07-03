from flask import Flask, redirect, render_template, request, session, g, flash, jsonify
from dotenv import load_dotenv
import sqlite3
import bcrypt
import os
import uuid
import sys
import secrets
from . import test_parser

DATABASE = 'tsync.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def get_etest(id, user_id) -> test_parser.ETest:
    db = get_db()
    res = db.cursor().execute("SELECT ttype, name FROM etest WHERE id=?", (id,))
    testpath = res.fetchone()
    if testpath is None:
        return None
    res = db.cursor().execute(
        "SELECT id, question, html_question FROM top_question WHERE tid=?", (id,))
    tqs = res.fetchall()
    topqs = []
    test = test_parser.ETest(testpath[0], testpath[1], topqs)
    for tq in tqs:
        topq = test_parser.TopQuestion(tq[1], tq[2], [])
        res = db.cursor().execute(
            "SELECT question, html_question, answer, answer.sort_id, question.id FROM question, answer WHERE answer.q_id=question.id AND topid=? AND answer.user_id=?", (tq[0], user_id))
        qs = res.fetchall()
        questions = []
        for q in qs:
            quest = test_parser.Question(
                q[0], q[1], test_parser.Answer(q[2], q[3]))
            questions.append(quest)
            res = db.cursor().execute(
                "SELECT answer, user.username FROM answer, user WHERE user_id!=? AND user.id=answer.user_id AND answer.tid=? AND answer.q_id=?", (user_id, id, q[4]))
            others = res.fetchall()
            quest.others = {}
            for other in others:
                if other[0] in quest.others:
                    quest.others[other[0]].append(other[1])
                else:
                    quest.others[other[0]] = [other[1]]

        topq.q = questions
        topqs.append(topq)
    test.sort()
    return test

def get_test_by_path(ttype, name, mktest):
    db = get_db()
    res = db.cursor().execute(
        "SELECT id FROM etest WHERE ttype=? AND name=?", (ttype, name))

    test = res.fetchone()
    if test is None and mktest:
        id = str(uuid.uuid4())
        res = db.cursor().execute(
            "INSERT INTO etest (id, ttype, name) VALUES (?, ?, ?)", (id, ttype, name))
        db.commit()
        test = id
    else:
        test = test[0]
    return test

def clear_questions(user_id, tid):
    db = get_db()
    db.cursor().execute("DELETE FROM answer WHERE user_id=? AND tid=?", (user_id, tid))
    db.commit()

def save_top_question(user_id, tid, tqs: [test_parser.TopQuestion]):
    db = get_db()
    res = db.cursor().execute(
        "SELECT id FROM top_question WHERE tid=? AND question=?", (tid, tqs.h))
    id = res.fetchone()
    if id is None:
        id = str(uuid.uuid4())
        db.cursor().execute(
            "INSERT INTO top_question (id, tid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (id, tid, user_id, tqs.h, tqs.html_h))
    else:
        id = id[0]
    for q in tqs.q:
        res = db.cursor().execute(
            "SELECT id FROM question WHERE topid=? AND question=?", (id, q.q))
        res = res.fetchone()
        if res is None:
            qid = str(uuid.uuid4())
            db.cursor().execute(
                "INSERT INTO question (id, topid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (qid, id, user_id, q.q, q.html_q))
        else:
            qid = res[0]
            db.cursor().execute(
                "DELETE FROM answer WHERE tid=? AND q_id=? AND user_id=?", (tid, qid, user_id))
        aid = str(uuid.uuid4())
        db.cursor().execute(
            "INSERT INTO answer (id, tid, q_id, user_id, answer, sort_id) VALUES (?, ?, ?, ?, ?, ?)", (aid, tid, qid, user_id, q.a.val, q.a.sortId))

    db.commit()

def handle_upload(content: str, user_id: str):
    try:
        etest = test_parser.parse_test(content)
    except Exception:
        return None, ("Input file is invalid", 400)
    # mktest = 'admin' in session and session['admin']
    mktest = True
    id = get_test_by_path(etest.ttype, etest.name, mktest)
    if id is None:
        return None, ("Test does not exist", 403)
    for tq in etest.q:
        save_top_question(user_id, id, tq)
    return id, None

def get_history():
    db = get_db()
    res = db.cursor().execute("SELECT id, name, ttype FROM etest")
    res = res.fetchall()

    modules = {
        'afi': [],
        'ds': [],
        'ti': [],
        'la': [],
        'fosap': []}

    for (id, name, ttype) in res:
        modules[ttype].append((id, name, ttype))

    return modules

def load_resource_links():
    """
    Loads links for page /resources
    Format: {link}={name}
    """

    try:
        lines = open("resourcelinks.txt").readlines()
        links = [line.split("=") for line in lines]
        links = [(link[0].strip(), link[1].strip()) for link in links]
        print(links)
        return links
    except FileNotFoundError:
        return []
