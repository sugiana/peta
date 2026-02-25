import sys
import json


key = sys.argv[1]
with open('nama.json') as f:
    s = f.read()
d = json.loads(s)
print(d)

nama = d['title'].split(',')[0]
print(','.join([key, nama]))
