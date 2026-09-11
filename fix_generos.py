path = "render.py"
src = open(path, encoding="utf-8").read()

old = "meta['slug'] = slug"
new = ("meta['slug'] = slug\n"
       "        g = meta.get('generos', [])\n"
       "        if isinstance(g, str):\n"
       "            g = [x.strip() for x in g.replace('[', '').replace(']', '').split(',') if x.strip()]\n"
       "        meta['generos'] = g")
if old in src and "isinstance(g, str)" not in src:
    src = src.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(src)
    print("OK: render.py normaliza generos (string -> lista)")
else:
    print("ja aplicado ou ancora mudou — me mande: grep -n \"meta['slug']\" render.py")
