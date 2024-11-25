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
                inps = td.findAll('input')
                if len(inps) > 1:
                    labels = td.findAll('label')
                    for label, i in zip(labels, zip):
                        if i.get('value') == 1:
                            cq.a = label.get_text()
                else:
                    ans = inps[0].get('value')
                    cq.a = ans
    return ETest('ds', '', tq)

def sanetize(a):
    dupls = a.findAll('span', attrs={'class': 'MJX_Assistive_MathML'})
    for dupl in dupls:
        dupl.decompose()


def parse_test(content: str) -> ETest:
    parsed_html = BeautifulSoup(content, 'html.parser')
    names = path(parsed_html)
    if names[0] == '\n(UE) Diskrete Strukturen\n':
        etest = parse_ds(parsed_html)
    if names[0] == '\n(VO) Analysis für Informatik\n':
        etest = parse_afi(parsed_html)
    etest.name = names[-1]
    return etest


if __name__ == "__main__":
    html = open("data/bl05ds.html", "r").read()
    etest = parse_test(html)
    print(etest.name)
    print(etest.ttype)
    print(etest.q[0].q[0])
