import test_parserv2 as parser

if __name__ == "__main__":
    html = open("data/la10.html", "rb").read()
    html2 = open("data/afi13.html", "rb").read()
    test = parser.parse_test(html2)
    print(test.html)
    print(test.cmid)
    print(test.name)
    print(test.answers)
    for ans in test.answers:
        print(ans.hash, ans.id, ans.value)
