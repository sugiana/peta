from pprint import pprint
from parsel import Selector
from jaccard_index.jaccard import jaccard_index


with open('google.html') as f:
    s = f.read()
sel = Selector(s)
cari = sel.xpath('//textarea[@name="q"]').xpath('@value').extract()[0]
cari = cari.split(',')[0]
daftar = []
for row in sel.xpath('//span/a[@data-ved]'):
    title = row.xpath('h3/text()').extract()
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
