from pprint import pprint
from parsel import Selector
from jaccard_index.jaccard import jaccard_index


with open('duckduckgo.html') as f:
    s = f.read()
sel = Selector(s)
daftar = []
cari = sel.xpath('//meta[@name="apple-mobile-web-app-title"]')
cari = cari[0].xpath('@content').extract()[0]
for row in sel.xpath('//h2/a'):
    title = row.xpath('span/text()').extract()
    if not title:
        continue
    title = title[0]
    url = row.xpath('@href').extract()
    if not url:
        continue
    url = url[0]
    title = title.split(',')[0]
    index = jaccard_index(title, cari)
    daftar.append((index, title, url))
daftar.sort()
daftar.reverse()
pprint(daftar)
