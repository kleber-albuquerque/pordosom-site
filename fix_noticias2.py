path = "admin/index.html"
src = open(path, encoding="utf-8").read()
n = 0

# FIX 6 (universal): apos QUALQUER chamada de carregarAlbuns() dentro de
# entrar()/init, chamar carregarNoticias() — via regex tolerante a indentacao
import re

# captura "carregarAlbuns();" (com await ou nao) que NAO seja seguida de carregarNoticias
padrao = re.compile(r"(?<!await )(?<!\n\s{4}carregarNoticias\(\);\n)([ \t]*)(await )?carregarAlbuns\(\);(?![ \t]*\n[ \t]*carregarNoticias\(\);)")
def substitui(m):
    prefixo, await_ = m.group(1), m.group(2) or ''
    return prefixo + await_ + "carregarAlbuns();\n" + prefixo + "carregarNoticias();"
src2 = padrao.sub(substitui, src)
if src2 != src:
    n += 1
    src = src2

# FIX 7 (universal): insere o stat de noticias apos o stat-generos
if 'stat-noticias' not in src:
    m = re.search(r'<div class="stat-card"><div class="stat-num" id="stat-generos">[^<]*</div><div class="stat-label">[^<]*</div></div>', src)
    if m:
        bloco = m.group(0) + '\n        <div class="stat-card"><div class="stat-num" id="stat-noticias">—</div><div class="stat-label">Notícias publicadas</div></div>'
        src = src[:m.start()] + bloco + src[m.end():]
        n += 1

open(path, "w", encoding="utf-8").write(src)
print("fixes aplicados:", n, "de 2")
