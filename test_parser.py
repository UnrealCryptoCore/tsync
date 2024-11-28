try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup


class Question:
    def __init__(self, q, html_q, a):
        self.q = q
        self.html_q = html_q
        self.a = a
        self.qtype = None

    def __str__(self):
        return f"{self.q}: {self.a}"


class TopQuestion:
    def __init__(self, h: str, html_h: str, q: [Question]):
        self.h = h
        self.html_h = html_h
        self.q = q
        self.qtype = None


class ETest:
    def __init__(self, ttype, name, q):
        self.ttype = ttype
        self.name = name
        self.q: [TopQuestion] = q


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
        names.append(n.get_text())
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
            tr = content.findAll('tr')
            q = []
            for r in tr[1:]:
                answer = r.find(
                    'option', attrs={'selected': 'selected'})
                row = r.findAll('td')[:-1]
                rowq = ",".join([s.get_text() for s in row])
                rowq_html = " | ".join([s.decode_contents() for s in row])
                q.append(Question(rowq, rowq_html, answer.get_text()))
            for sel in content.findAll('select'):
                sel.decompose()

            top_question = TopQuestion(content.get_text(), content.decode_contents(), q)
            tq.append(top_question)
        if 'calculated' in question['class']:
            qtext = content.find('div', attrs={'class': 'qtext'})
            ablock = content.find('div', attrs={'class': 'ablock'})
            inp = ablock.find('input')
            label = ablock.find('label')
            q = [Question(label.get_text(), label.decode_contents(), inp.get('value'))]
            top_question = TopQuestion(qtext.get_text(), qtext.decode_contents(), q)
            tq.append(top_question)

    return ETest('ti', '', tq)


def parse_afi(phtml) -> ETest:
    div = phtml.body.find('form', attrs={'id': 'responseform'}).find('div')
    children = div.findAll('div', attrs={'class': 'que'})
    questions = []
    tq = TopQuestion('', '', questions)
    etest = ETest('afi', '', [tq])
    for child in children:
        content = child.find('div', attrs={'class': 'content'})
        quest = content.find('div', attrs={'class': 'qtext'})
        q = quest.get_text()
        sanetize(quest)
        q_html = quest.decode_contents()
        answ = ""
        if 'numerical' in child['class']:
            answ = content.find('div', attrs={'class': 'ablock'}).find('input')
            answ = answ.get('value')
        else:
            mcs = 'multichoiceset' in child['class']
            if mcs or 'multichoice' in child['class']:
                answers = content.find(
                    'div', attrs={'class': 'answer'}).findAll('div', attrs={'class': ['r0', 'r1']})
                answ = []
                for ans in answers:
                    if mcs:
                        inp = ans.find('input', attrs={'type': 'checkbox'})
                    else:
                        inp = ans.find('input', attrs={'type': 'radio'})
                    if inp.get('checked') == 'checked':
                        a = ans.find('div')
                        sanetize(a)
                        answ.append(a.decode_contents())
                answ = "; ".join(list(set(answ)))

        questions.append(
            Question(q, q_html, answ))
    return etest


def parse_ds(phtml) -> ETest:
    div = phtml.body.find('div', attrs={'class': 'okutable'})
    tqs = div.find('table').findAll('tr')
    ctq = None
    cq = None
    tq = []
    for idx, qst in enumerate(tqs):
        tds = qst.findAll('td')
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
                else:
                    labels = td.findAll('label')
                    for label, i in zip(labels, inps):
                        if i.get('checked') == 'checked':
                            cq.a = label.get_text()

    return ETest('ds', '', tq)


def sanetize(a):
    dupls = a.findAll('span', attrs={'class': 'MJX_Assistive_MathML'})
    for dupl in dupls:
        dupl.decompose()


def make_compatible(content):
    return content.decode('utf-8').replace('\r\n', '\n').replace('\n', '')


def parse_test(content: str) -> ETest:
    content = make_compatible(content)
    parsed_html = BeautifulSoup(content, 'html.parser')
    names = path(parsed_html)
    if names[0] == ' (UE) Diskrete Strukturen ':
        etest = parse_ds(parsed_html)
    elif names[0] == ' (VO) Analysis für Informatik ':
        etest = parse_afi(parsed_html)
    elif names[0] == ' (VU) Einführung in die Technische Informatik ':
        etest = parse_ti(parsed_html)
    etest.name = names[-1]
    return etest


if __name__ == "__main__":
    html = open("data/ti7.html", "r").read()
    etest = parse_test(html.encode('utf-8'))
    print(etest.name)
    print(etest.ttype)
    print(etest.q[0].html_h)
