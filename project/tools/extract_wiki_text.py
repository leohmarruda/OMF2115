from html.parser import HTMLParser
from pathlib import Path
import re
import sys


class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "mw-parser-output" in attrs.get("class", "").split():
                self.depth = 1
        if not self.depth:
            return
        if tag in ("script", "style", "svg"):
            self.skip += 1
        if tag in ("p", "li", "tr", "h1", "h2", "h3", "h4", "br"):
            self.parts.append("\n")
        if tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ("script", "style", "svg") and self.skip:
            self.skip -= 1
        if tag == "div":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


for name in sys.argv[1:]:
    path = Path("omf3k/docs/OMF2097/omfwiki") / name
    article = Article()
    article.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = "".join(article.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    print("\n### " + name + " ###\n" + text[:9000])
