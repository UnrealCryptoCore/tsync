import ...src.tsync.test_parserv2 as parser

html = open("data/afi13.html", "r").read()
test = parser.parse_test(html)
print(test.cmid)
print(test.name)
print(test.answers)
