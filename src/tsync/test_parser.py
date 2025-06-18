try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup


class Answer:
    def __init__(self, val, sortId):
        self.val = val
        self.sortId = sortId

    def __str__(self):
        return self.val


class Question:
    def __init__(self, q, html_q, a):
        self.q = q
        self.html_q = html_q
        self.a = a
        self.qtype = None

    def __str__(self):
        return f"{self.q}: {self.a}"


class TopQuestion:
    def __init__(self, h: str, html_h: str, q: list[Question]):
        self.h = h
        self.html_h = html_h
        self.q: list[Question] = q
        self.qtype = None

    def sort(self):
        self.q = sorted(self.q, key=lambda q: q.a.sortId)


class ETest:
    def __init__(self, ttype, name, q):
        self.ttype = ttype
        self.name = name
        self.q: list[TopQuestion] = q

    def sort(self):
        for q in self.q:
            q.sort()


def answers_ds(phtml):
    anst = phtml.body.findAll('td', attrs={'class': 'answers'})
    ans = []
    for a in anst:
        ans.append(a.find('input').get('value'))
    return ans


def questions_ds(phtml):
    qst = phtml.body.findAll('td', attrs={'class': 'question'})
    qs = []
    for a in qst:
        qs.append(a.decode_contents())
    return qs


def path(phtml):
    path = phtml.body.findAll('li', attrs={'class': 'breadcrumb-item'})
    names = []
    for n in path:
        names.append(n.get_text().strip())
    return names


def get_text(tag):
    imgs = tag.findAll('img')
    res = "\n".join([img['href'] for img in imgs])
    return res + tag.get_text()


def parse_ti(phtml) -> ETest:
    questions = phtml.body.find('form', attrs={'id': 'responseform'}).findAll(
        'div', attrs={'class': 'que'})
    tq = []
    for question in questions:
        content = question.find('div', attrs={'class': 'content'})
        if 'multianswer' in question['class']:
            table = question.find('table')
            q = []
            if table:
                tr = content.findAll('tr')
                for r in tr[1:]:
                    answer = r.find(
                        'option', attrs={'selected': 'selected'})
                    row = r.findAll('td')[:-1]
                    rowq = ",".join([s.get_text() for s in row])
                    rowq_html = " | ".join([s.decode_contents() for s in row])
                    q.append(Question(rowq, rowq_html, answer.get_text()))
                for sel in content.findAll('select'):
                    sel.decompose()
            else:
                subs = question.findAll('span', attrs={'class': 'subquestion'})
                i = 1
                for sub in subs:
                    i += 1
                    answer = sub.find(
                        'option', attrs={'selected': 'selected'})
                    q.append(Question(f"Frage {i}", f"Frage {i}", answer.get_text()))

            top_question = TopQuestion(
                content.get_text(), content.decode_contents(), q)
            tq.append(top_question)

        if 'calculated' in question['class']:
            qtext = content.find('div', attrs={'class': 'qtext'})
            ablock = content.find('div', attrs={'class': 'ablock'})
            inp = ablock.find('input')
            label = ablock.find('label')
            q = [Question(label.get_text(),
                          label.decode_contents(), inp.get('value'))]
            top_question = TopQuestion(
                qtext.get_text(), qtext.decode_contents(), q)
            tq.append(top_question)

    return ETest('ti', '', tq)


def parse_afi(phtml) -> ETest:
    div = phtml.body.find('form', attrs={'id': 'responseform'}).find('div')
    children = div.findAll('div', attrs={'class': 'que'})
    subqs = []
    tq = TopQuestion('', '', subqs)
    questions = [tq]
    etest = ETest('afi', '', questions)
    i = 0
    ac = 0
    for child in children:
        i += 1
        content = child.find('div', attrs={'class': 'content'})
        quest = content.find('div', attrs={'class': 'qtext'})
        q = quest.get_text()
        sanetize(quest)
        q_html = quest.decode_contents()
        answ = ""
        if 'numerical' in child['class']:
            answ = content.find('div', attrs={'class': 'ablock'}).find('input')
            answ = Answer(answ.get('value'), ac)
            ac += 1
            subqs.append(Question(q, q_html, answ))
        else:
            mcs = 'multichoiceset' in child['class']
            tf = 'truefalse' in child['class']
            if mcs or tf or 'multichoice' in child['class']:
                answers = content.find(
                    'div', attrs={'class': 'answer'}).findAll('div', attrs={'class': ['r0', 'r1']})
                answ = []
                for ans in answers:
                    if mcs:
                        inp = ans.find('input', attrs={'type': 'checkbox'})
                    else:
                        inp = ans.find('input', attrs={'type': 'radio'})
                    if tf:
                        a = ans.find('label')
                    else:
                        a = ans.find('div')
                    sanetize(a)
                    txt = a.get_text()
                    quest = a.decode_contents()
                    checked = inp.get('checked') == 'checked'
                    answ.append((txt, quest, checked))
                answ = list(set(answ))
            else:
                continue

            qs = None
            if isinstance(answ, list):
                qs = []
                for a, b, c in answ:
                    qs.append(Question(a, b, Answer('wahr' if c else 'falsch', ac)))
                    ac += 1
                hint = q
                html_hint = q_html
            else:
                qs = [Question(q, q_html, Answer(answ, ac))]
                ac += 1
                hint = 'Frage ' + str(i)
                html_hint = 'Frage ' + str(i)
            questions.append(TopQuestion(hint, html_hint, qs))
    return etest


def parse_ds(phtml) -> ETest:
    tq = parse_ds_la(phtml)
    return ETest('ds', '', tq)


def parse_la(phtml) -> ETest:
    tq = parse_ds_la(phtml)
    return ETest('la', '', tq)


def parse_ds_la(phtml):
    div = phtml.body.find('div', attrs={'class': 'okutable'})
    tqs = div.find('table').findAll('tr')
    ctq = None
    cq = None
    ac = 0
    tq = []
    for idx, qst in enumerate(tqs):
        tds = qst.findAll('td')
        ctq = TopQuestion("", "", [])
        for td in tds:
            sanetize(td)
            contents = td.decode_contents()
            text = td.get_text()
            if 'extext' in td['class']:
                ctq = TopQuestion(text, contents, [])
                tq.append(ctq)
            elif 'question' in td['class']:
                cq = Question(text, contents, None)
                ctq.q.append(cq)
            elif 'answers' in td['class']:
                inps = td.findAll('input', attrs={'type': 'radio'})
                if len(inps) == 0:
                    inps = td.findAll('input')
                    if len(inps) > 1:
                        labels = td.findAll('label')
                        for label, i in zip(labels, inps):
                            if i.get('value') == 1:
                                cq.a = label.get_text()
                    else:
                        ans = inps[0].get('value')
                        cq.a = ans
                        cq.a = Answer(ans, ac)
                        ac += 1
                else:
                    labels = td.findAll('label')
                    for label, i in zip(labels, inps):
                        if i.get('checked') == 'checked':
                            cq.a = label.get_text()
                            cq.a = Answer(label.get_text(), ac)
                            ac += 1
        if len(ctq.q) > 0:
            tq.append(ctq)

    return tq


def sanetize(a):
    dupls = a.findAll('span', attrs={'class': 'MJX_Assistive_MathML'})
    for dupl in dupls:
        dupl.decompose()
    imgs = a.findAll('img')
    for img in imgs:
        img['src'] = "/".join(img['src'].split('/')[1:])


def make_compatible(content):
    return content.decode('utf-8').replace('\r\n', '\n').replace('\n', ' ')


def parse_test(content: str) -> ETest:
    content = make_compatible(content)
    parsed_html = BeautifulSoup(content, 'html.parser')
    names = path(parsed_html)
    print(names)
    if names[0] == '(UE) Diskrete Strukturen':
        etest = parse_ds(parsed_html)
    elif names[0] == '(VO) Analysis für Informatik':
        etest = parse_afi(parsed_html)
    elif names[0] == '(VU) Einführung in die Technische Informatik':
        etest = parse_ti(parsed_html)
    elif names[0] == '(UE) Lineare Algebra für Informatik (Tutorien)':
        print("yes")
        etest = parse_la(parsed_html)
    etest.name = names[-1]
    return etest


if __name__ == "__main__":
    html = open("data/Blatt 9ds.html", "r").read()
    etest = parse_test(html.encode('utf-8'))
    print(etest.name)
    print(etest.ttype)
    print(len(etest.q))
