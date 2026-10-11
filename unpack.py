import os
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read().replace("\r\n", "\n")
n = 0
for m in re.finditer(r"^````[a-z]* file=(\S+)\n(.*?)\n````$", src, re.S | re.M):
    path, body = m.group(1), m.group(2)
    if path.endswith(".bat"):
        body = body.replace("\n", "\r\n")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(body + ("\r\n" if path.endswith(".bat") else "\n"))
    n += 1
print(n, "files created")
