import datetime
import os
import bleach
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    current_app,
    session,
    jsonify,
    g,
)
from markupsafe import Markup
from .auth import login_required, api_key_required
from .db import get_db
from .test_parserv2 import (
    parse_test,
    ETest,
    Answer,
)
from .ai_answer import (
    AIModel,
    SingleChoice,
    MultipleChoice,
    TextAnswer,
)

bp = Blueprint("tsync", __name__)
aiModel = AIModel()


def get_etest_v2(cmid, user_id):
    db = get_db()
    res = db.cursor().execute(
        "SELECT name, html FROM etest_v2 WHERE cmid=? AND user_id=?", (cmid, user_id))
    etest = res.fetchone()
    if etest is None:
        return None, None
    etest = ETest(cmid, etest[0], [], [], etest[1])
    res = db.cursor().execute("""
                            SELECT id, value, text, type, hash
                            FROM answer_v2
                            WHERE cmid=? AND user_id=?
                            """,
                              (cmid, user_id))
    answers = res.fetchall()
    groups = []
    for i, ans in enumerate(answers):
        ans = Answer(ans[0], ans[1], ans[2], ans[3], text_hash=ans[4])
        answers[i] = ans
        res = db.cursor().execute(
            """
            SELECT
                answer_v2.value, user.username, user.type
            FROM
                answer_v2, user
            WHERE
                answer_v2.hash=?
                AND answer_v2.text=?
                AND user.id=answer_v2.user_id
            """,
            (ans.hash, ans.text))
        res = res.fetchall()
        group = {
            ans.value: []
        }
        for v in res:
            key = v[0]
            val = (v[1], v[2])
            if key in group:
                group[key].append(val)
            else:
                group[key] = [val]
        groups.append(group)
    etest.answers = answers
    return etest, groups


def save_answers(user_id, cmid, answers, questions=None):
    db = get_db()
    if questions is not None:
        for quest in questions:
            db.cursor().execute("""
                                INSERT into question_v2
                                    (id, question)
                                VALUES (?, ?)
                                ON CONFLICT(id)
                                DO NOTHING
                                """, (quest.hash, quest.text))

    for quest in answers:
        db.cursor().execute("""
                        INSERT into answer_v2
                            (cmid, id, user_id, hash, text, value, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(cmid, id, user_id)
                        DO UPDATE SET
                            hash = excluded.hash,
                            text = excluded.text,
                            value = excluded.value,
                            type = excluded.type
                        """,
                            (cmid,
                             quest.id,
                             user_id,
                             quest.hash,
                             quest.text,
                             bleach.clean(quest.value),
                             quest.type,
                             ))
        db.commit()


def save_etest(user_id, etest):
    db = get_db()
    db.cursor().execute("""
                        INSERT into etest_v2
                            (user_id, cmid, name, html)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(cmid, user_id)
                        DO UPDATE SET
                            html = excluded.html
                        """,
                        (user_id, etest.cmid, etest.name, etest.html))
    save_answers(user_id, etest.cmid, etest.answers, etest.questions)
    db.commit()


def backup_test(etest, content, user_id):
    now = datetime.date.today()
    filename = f"uploads/{user_id}/{now.strftime('%d-%m-%Y')}/test-{etest.cmid}.html"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)


def handle_upload_v2(content: str, user_id: str):
    try:
        etest = parse_test(content)
    except Exception as e:
        raise e
        return None, ("Input file is invalid.", 400)
    save_etest(user_id, etest)
    if False:
        backup_test(etest, content, user_id)
    return etest.cmid, None


def get_history(user_id):
    db = get_db()
    res = db.cursor().execute(
        "SELECT cmid, name FROM etest_v2 WHERE user_id=?", (user_id, ))
    res = res.fetchall()

    return res


def answer_to_html(ans, group, ai_answer):
    s = ""
    for i, v in enumerate(group):
        ai_answer = ai_answer and i == 0
        users = group[v]
        for j, u in enumerate(users):
            users[j] = u[0]
            if u[1] == "ai":
                users[j] = f"<strong>{users[j]}</strong> (🤖)"
        if ans.value == v:
            if len(users) == 1:
                tp = "answer-unknown"
            else:
                tp = "answer-same"
        else:
            tp = "answer-different"
        ai_button = ""
        if ai_answer:
            ai_button = f"""
            <button
            id='tsync-ai-btn-{ans.id}'
            class='tsync-btn tsync-ai-btn'>
                <span>ask ai ✨</span>
            </button>
            """
        s += f"<div class='tsync-answer-list {tp}'>{v}: {', '.join(users)}{ai_button}</div>"
    return s


def contains_ai(group):
    for k in group:
        users = group[k]
        for u in users:
            if u[1] == "ai":
                return True
    return False


@bp.get("/test/<testid>")
@login_required
def test_page(testid):
    user_id = session['id']
    test, groups = get_etest_v2(testid, user_id)
    if test is None:
        return render_template("testnotfoundtmpl.html"), 404
    render = test.html
    for ans, group in zip(test.answers, groups):
        s = answer_to_html(ans, group, False)
        render = render.replace(f"%{ans.id.upper()}%", s)
    render = Markup(render)
    return render_template("testtmpl_v2.html", name=test.name, test_render=render)


@bp.post('/upload')
@login_required
def upload_file():
    user_id = session["id"]
    f = request.files['file']
    content = f.read()
    id, err = handle_upload_v2(content, user_id)
    if err:
        flash(err[0], 'error')
        return render_template("indextmpl.html"), err[1]
    return redirect(f"/test/{id}")


@bp.post("/api/upload")
@api_key_required
def api_upload():
    user_id = g.user_id
    content = request.get_data()
    id, err = handle_upload_v2(content, user_id)
    if err:
        return err
    return jsonify({"testid": id}), 200


@bp.get("/api/solutions/<cmid>")
@api_key_required
def api_solutions(cmid):
    user_id = g.user_id
    test, groups = get_etest_v2(cmid, user_id)
    if test is None:
        return None, 404

    res = {}
    for ans, group in zip(test.answers, groups):
        ai = contains_ai(group)
        res[ans.id] = answer_to_html(ans, group, not ai)
    return jsonify(res), 200


@bp.get("/api/aianswer/<aid>")
@api_key_required
def api_ai_answer(aid):
    db = get_db()
    ai_user_id = current_app.config['AI_USER_ID']
    res = db.cursor().execute("""
                        SELECT cmid, hash, value
                        FROM answer_v2
                        WHERE
                            id=?
                        """, (aid, )).fetchone()
    if res is None:
        return "Could not find answer id.", 404
    cmid, hash, value = res

    res = db.cursor().execute("""
                        SELECT COUNT(*) FROM answer_v2
                        WHERE
                            hash=? AND value=? AND user_id=?
                          """, (hash, value, ai_user_id)).fetchone()
    if res[0] > 0:
        return "", 200

    res = db.cursor().execute("""
                        SELECT question
                        FROM question_v2
                        WHERE id=?
                              """, (hash, )).fetchone()
    if res is None:
        return "Question not found.", 404

    question = res[0]

    answers = db.cursor().execute("""
                        SELECT text, type, id
                        FROM answer_v2
                        WHERE
                            hash=?
                        GROUP BY text, type
                              """, (hash, )).fetchall()

    tp = answers[0][1]
    answer_text = []
    if tp == "text":
        tp = TextAnswer
        answer_text = None
    elif tp == "radio":
        tp = SingleChoice
    elif tp == "checkbox":
        tp = MultipleChoice
    else:
        return "Answer type not supported.", 400

    if answer_text is not None:
        for e in answers:
            answer_text.append(e[0])

    res = aiModel.answer_question(question, tp, answer_text)
    # res = aiModel.answer_question_demo(question, tp, answer_text, 25)
    if res['confidence'] < 0.9:
        return "Ai confidence too low", 500

    for i, ans in enumerate(answers):
        if tp == TextAnswer:
            answers[i] = Answer(ans[2]+"-ai", res['answer'], ans[0], ans[1], text_hash=hash)
        elif tp == SingleChoice:
            val = '1' if i+1 == res['number'] else '0'
            answers[i] = Answer(ans[2]+"-ai", val, ans[0], ans[1], text_hash=hash)
        elif tp == MultipleChoice:
            val = '1' if res['numbers'][i] else '0'
            answers[i] = Answer(ans[2]+"-ai", val, ans[0], ans[1], text_hash=hash)

    save_answers(ai_user_id, cmid, answers)
    return "", 200


@bp.get("/tsync.user.js")
def tm_script():
    if "username" not in session:
        return redirect("/login")
    with open(os.path.join(current_app.static_folder, 'style.css'), "r") as f:
        return render_template("tsync.user.js",
                               url=current_app.config['URL'],
                               styles=f.read()), 200, {
            'Content-Type': 'application/javascript'
        }


@bp.route("/helloworld")
def hello_world():
    return "<p>Hello, World!</p>"


@bp.route("/secure-helloworld")
@api_key_required
def secure_hello_world():
    return "<p>Hello, World!</p>"


@bp.get("/resources")
def resources():
    return render_template("resourcestmpl.html", res_links=current_app.config['RESOURCE_LINKS'])


@bp.get("/tampermonkey")
def tampermonkey():
    return render_template("tampermonkeytmpl.html")


@bp.route("/")
@login_required
def index():
    user_id = session["id"]
    hist = get_history(user_id)
    return render_template("indextmpl.html", hist=hist)
