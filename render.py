#!/usr/bin/env python3
# ==========================================================
# POR DO SOM — Render do catálogo (v3.1 — com BASE path)
#
# Fonte: content/albuns/*.md (editáveis pelo painel)
# Gera:
#   - albuns/{slug}.html (páginas dos álbuns, com Schema.org)
#   - data/catalogo.json (para o JS da vitrine/gravadora)
#   - sitemap.xml
#
# ⚠️ REGRA DA BASE (documentada no mapa de ação):
#   BASE = caminho onde o site está hospedado.
#   - No GitHub Pages de projeto: '/pordosom-site'
#   - No dia do domínio próprio (pordosom.com.br na raiz): ''
#     (trocar AQUI e no js/catalogo.js + sed inverso nos HTMLs)
#
# Uso:  python3 render.py
# ==========================================================
import os, re, json, html
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_MD = os.path.join(BASE_DIR, 'content', 'albuns')
OUT_ALBUNS = os.path.join(BASE_DIR, 'albuns')
OUT_JSON = os.path.join(BASE_DIR, 'data', 'catalogo.json')
OUT_SITEMAP = os.path.join(BASE_DIR, 'sitemap.xml')

# ════════════════════════════════════════════════════════
# A BASE — único ponto de configuração (com render.py e
# js/catalogo.js — os 2 lugares para trocar no domínio próprio)
# ════════════════════════════════════════════════════════
BASE = '/pordosom-site'
DOMINIO = 'https://kleber-albuquerque.github.io' + BASE

GENEROS = {
    'samba-de-raiz': 'Samba de Raiz',
    'instrumental': 'Instrumental',
    'mpb': 'MPB/Nova MPB',
    'brasilidades': 'Brasilidades',
    'cultura-popular': 'Cultura Popular',
    'afro-brasileira': 'Afro-brasileira',
    'infantil': 'Infantil',
}

# ---------- Parser de frontmatter (YAML simples) ----------
def parse_md(caminho):
    """Lê um .md e retorna (meta: dict, corpo: str)."""
    with open(caminho, encoding='utf-8') as f:
        texto = f.read()

    meta, corpo = {}, texto
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', texto, re.DOTALL)
    if m:
        bloco, corpo = m.group(1), m.group(2)
        lista_atual = None
        for linha in bloco.split('\n'):
            m_item = re.match(r'^\s+-\s+(\S+)\s*$', linha)
            if m_item and lista_atual:
                meta[lista_atual].append(m_item.group(1))
                continue
            m_kv = re.match(r'^(\w[\w_-]*):\s*(.*)$', linha)
            if m_kv:
                chave, valor = m_kv.group(1), m_kv.group(2).strip()
                lista_atual = chave
                m_str = re.match(r'^"(.*)"$', valor) or re.match(r"^'(.*)'$", valor)
                if m_str:
                    meta[chave] = m_str.group(1)
                elif valor == '':
                    meta[chave] = []
                elif re.match(r'^\d+$', valor):
                    meta[chave] = int(valor)
                elif valor in ('true', 'false'):
                    meta[chave] = valor == 'true'
                else:
                    meta[chave] = valor
    return meta, corpo.strip()

def esc(t):
    return html.escape(str(t or ''))

def caminho(c):
    """Junta a BASE com um caminho. Uso em TODO o template."""
    if not c:
        return c
    return BASE + c if c.startswith('/') else c

def embed_spotify(url):
    if not url:
        return ''
    return url.replace('open.spotify.com/', 'open.spotify.com/embed/')

def embed_youtube(url):
    if not url:
        return ''
    m = re.search(r'(?:v=|youtu\.be/|embed/)([\w-]{11})', url)
    if m:
        return 'https://www.youtube.com/embed/' + m.group(1)
    return ''

def link_nav(slug, titulo, seta):
    """Gera o link de navegação anterior/próximo — construído por
    concatenação (sem f-string aninhada: imune a erro de aspas)."""
    href = caminho('/albuns/' + slug + '.html')
    return ('<a class="album-nav-link" href="' + href + '">'
            + seta + ' ' + esc(titulo) + '</a>')

# ---------- Lê todos os álbuns ----------
albuns = []
if os.path.isdir(PASTA_MD):
    for nome in sorted(os.listdir(PASTA_MD)):
        if not nome.endswith('.md'):
            continue
        meta, corpo = parse_md(os.path.join(PASTA_MD, nome))
        slug = nome[:-3]
        meta.setdefault('titulo', slug.replace('-', ' ').title())
        meta.setdefault('artista', '')
        meta.setdefault('ano', '')
        meta.setdefault('generos', [])
        meta.setdefault('destaque', False)
        meta.setdefault('faixas', '')
        meta['slug'] = slug
        meta['texto_pt'] = corpo
        albuns.append(meta)

albuns.sort(key=lambda a: (str(a.get('ano', '')), a['titulo']), reverse=True)

# ---------- Le as noticias (content/posts/*.md) ----------
PASTA_POSTS = os.path.join(BASE_DIR, 'content', 'posts')
posts = []
if os.path.isdir(PASTA_POSTS):
    for nome in sorted(os.listdir(PASTA_POSTS)):
        if not nome.endswith('.md'):
            continue
        meta, corpo = parse_md(os.path.join(PASTA_POSTS, nome))
        meta.setdefault('title', nome[:-3])
        meta.setdefault('date', '')
        meta.setdefault('resumo', '')
        meta.setdefault('rascunho', False)
        meta.setdefault('imagem', '')
        meta['corpo'] = corpo
        posts.append(meta)
posts = [p for p in posts if not p.get('rascunho')]
posts.sort(key=lambda p: str(p.get('date', '')), reverse=True)

# ---------- Template da página de álbum ----------
def page_album(a, prev, next_):
    generos_str = ' · '.join(GENEROS.get(g, g) for g in a.get('generos', []))

    schema = {
        "@context": "https://schema.org",
        "@type": "MusicAlbum",
        "name": a['titulo'],
        "byArtist": {"@type": "MusicGroup", "name": a['artista']},
        "genre": generos_str,
        "datePublished": str(a.get('ano', '')),
        "publisher": {"@type": "Organization", "name": "Por do Som"},
    }
    if a.get('faixas'):
        schema["numTracks"] = a['faixas']

    embeds_html = ''
    sp = embed_spotify(a.get('spotify', ''))
    if sp:
        embeds_html += ('\n        <iframe src="' + esc(sp) + '" height="152"'
                        ' loading="lazy" title="Ouvir no Spotify"></iframe>')
    yt = embed_youtube(a.get('youtube', ''))
    if yt:
        embeds_html += ('\n        <iframe src="' + esc(yt) + '" style="aspect-ratio:16/9"'
                        ' loading="lazy" allowfullscreen title="Vídeo do álbum"></iframe>')

    plats = []
    if a.get('spotify'):  plats.append(('Spotify', a['spotify']))
    if a.get('youtube'):  plats.append(('YouTube', a['youtube']))
    if a.get('apple'):    plats.append(('Apple Music', a['apple']))
    if a.get('deezer'):   plats.append(('Deezer', a['deezer']))
    plats_html = ''.join(
        '<a class="plat-link" href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(n) + '</a>'
        for n, u in plats)

    en_html = ''
    if a.get('texto_en'):
        en_html = '<p class="album-descricao-en">' + esc(a['texto_en']) + '</p>'

    # Navegação anterior/próximo (função link_nav — sem f-string aninhada)
    prev_html = link_nav(prev['slug'], prev['titulo'], '&#8592;') if prev else '<span></span>'
    next_html = link_nav(next_['slug'], next_['titulo'], '&#8594;') if next_ else '<span></span>'

    faixas_txt = ''
    if a.get('faixas'):
        faixas_txt = str(a['faixas']) + ' faixas · '

    # Links do menu (com BASE)
    menu = (
        '        <a href="' + caminho('/gravadora.html') + '" class="nav-link">Gravadora</a>\n'
        '        <a href="' + caminho('/projetos.html') + '" class="nav-link">Projetos</a>\n'
        '        <a href="' + caminho('/audiovisual.html') + '" class="nav-link">Audiovisual</a>\n'
        '        <a href="' + caminho('/blog.html') + '" class="nav-link">Notícias</a>\n'
        '        <a href="' + caminho('/manifesto.html') + '" class="nav-link">Manifesto</a>\n'
        '        <a href="' + caminho('/quem-somos.html') + '" class="nav-link">Quem Somos</a>\n'
        '        <a href="' + caminho('/contato.html') + '" class="nav-link nav-cta">Fale com o Selo</a>\n'
    )

    pagina = (
'<!DOCTYPE html>\n'
'<html lang="pt-BR">\n'
'<head>\n'
'<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>' + esc(a['titulo']) + ' — ' + esc(a['artista']) + ' | Por do Som</title>\n'
'<meta name="description" content="' + esc((a['texto_pt'] or a['titulo'])[:155]) + '">\n'
'<meta property="og:title" content="' + esc(a['titulo']) + '">\n'
'<meta property="og:description" content="' + esc((a['texto_pt'] or '')[:110]) + '">\n'
'<meta property="og:type" content="music.album">\n'
'<link rel="icon" type="image/jpeg" href="' + caminho('/pordosom-profile.jpg') + '">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + caminho('/css/style.css') + '">\n'
'<script type="application/ld+json">\n'
+ json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
'</script>\n'
'</head>\n'
'<body class="page-interna">\n'
'\n'
'<header class="header" id="header">\n'
'    <a href="' + caminho('/') + '" class="logo">\n'
'        <span class="logo-mark"><img src="' + caminho('/pordosom-profile.jpg') + '" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n'
'    </a>\n'
'    <nav class="nav" id="nav">\n'
+ menu +
'    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n'
'</header>\n'
'\n'
'<main class="album-page">\n'
'    <div class="container">\n'
'        <div class="album-hero">\n'
'            <div class="album-capa-grande">\n'
'                <img src="' + caminho(a.get('capa', '')) + '" alt="Capa do álbum ' + esc(a['titulo']) + '"\n'
'                     onerror="this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 600 600%22%3E%3Crect fill=%22%231a0e0e%22 width=%22600%22 height=%22600%22/%3E%3Ccircle cx=%22300%22 cy=%22260%22 r=%22100%22 fill=%22%23a83030%22 opacity=%220.75%22/%3E%3C/svg%3E\'">\n'
'            </div>\n'
'            <div>\n'
'                <span class="album-kicker">Álbum · ' + esc(a.get('ano', '')) + ' · ' + esc(generos_str) + '</span>\n'
'                <h1 class="album-titulo-grande">' + esc(a['titulo']) + '</h1>\n'
'                <div class="album-artista-grande">' + esc(a['artista']) + '</div>\n'
'                <div class="album-meta-info">' + faixas_txt + 'Por do Som</div>\n'
'\n'
'                <p class="album-descricao">' + esc(a['texto_pt']) + '</p>\n'
'                ' + en_html + '\n'
'\n'
'                <div class="album-embeds">' + embeds_html + '\n'
'                </div>\n'
'                <div class="album-plataformas">' + plats_html + '</div>\n'
'            </div>\n'
'        </div>\n'
'\n'
'        <div class="album-navegacao">\n'
'            ' + prev_html + '\n'
'            <a class="album-nav-link" href="' + caminho('/gravadora.html') + '">Voltar ao catálogo</a>\n'
'            ' + next_html + '\n'
'        </div>\n'
'    </div>\n'
'</main>\n'
'\n'
'<footer class="footer">\n'
'    <div class="container">\n'
'        <span class="footer-logo">PÔR DO SOM</span>\n'
'        <p class="footer-tagline">Selo Independente · Brasilidades</p>\n'
'        <p class="footer-text">© ' + str(datetime.now().year) + ' Por do Som</p>\n'
'    </div>\n'
'</footer>\n'
'\n'
'<script>\n'
'const menuBtn = document.getElementById(\'mobileMenuBtn\');\n'
'const nav = document.getElementById(\'nav\');\n'
'menuBtn.addEventListener(\'click\', () => nav.classList.toggle(\'active\'));\n'
'</script>\n'
'</body>\n'
'</html>\n')
    return pagina


BLOG_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Notícias | Por do Som</title>
<meta name="description" content="Notícias, lançamentos e novidades do Selo Por do Som.">
<link rel="icon" type="image/jpeg" href="BASE/pordosom-profile.jpg">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="BASE/css/style.css">
</head>
<body class="page-interna">
<header class="header" id="header">
    <a href="BASE/" class="logo">
        <span class="logo-mark"><img src="BASE/pordosom-profile.jpg" alt="Por do Som"></span>
        <span class="logo-text">PÔR DO SOM</span>
    </a>
    <nav class="nav" id="nav">
        <a href="BASE/gravadora.html" class="nav-link">Gravadora</a>
        <a href="BASE/projetos.html" class="nav-link">Projetos</a>
        <a href="BASE/audiovisual.html" class="nav-link">Audiovisual</a>
        <a href="BASE/blog.html" class="nav-link" style="color:var(--brand-primary-light)">Notícias</a>
        <a href="BASE/manifesto.html" class="nav-link">Manifesto</a>
        <a href="BASE/quem-somos.html" class="nav-link">Quem Somos</a>
        <a href="BASE/contato.html" class="nav-link nav-cta">Fale com o Selo</a>
    </nav>
    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>
</header>
<section class="musicas" style="padding-top:calc(var(--spacing-section) + 3rem)">
    <div class="container">
        <span class="section-subtitle">Notícias</span>
        <h1 class="section-title">Novidades <span class="gradient">do selo</span></h1>
        <p class="section-description">Lançamentos, projetos e histórias do Por do Som.</p>
        <div style="max-width:760px;margin:0 auto;display:grid;gap:1rem">
<!-- POSTS LISTA -->
        </div>
<!-- POSTS CORPO -->
    </div>
</section>
<footer class="footer">
    <div class="container">
        <span class="footer-logo">PÔR DO SOM</span>
        <p class="footer-tagline">Selo Independente · Brasilidades</p>
        <p class="footer-text">© 2026 Por do Som</p>
    </div>
</footer>
<script>
const menuBtn = document.getElementById('mobileMenuBtn');
const nav = document.getElementById('nav');
menuBtn.addEventListener('click', () => nav.classList.toggle('active'));
</script>
</body>
</html>"""

os.makedirs(OUT_ALBUNS, exist_ok=True)
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

geradas = []
for i, a in enumerate(albuns):
    prev = albuns[i - 1] if i > 0 else None
    next_ = albuns[i + 1] if i < len(albuns) - 1 else None
    path = os.path.join(OUT_ALBUNS, a['slug'] + '.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page_album(a, prev, next_))
    geradas.append(a['slug'])

# ---------- Gera o data/catalogo.json (com a BASE para o JS) ----------
catalogo_js = {
    'base': BASE,
    'generos': [{'id': k, 'nome': v} for k, v in GENEROS.items()],
    'albuns': [{
        'slug': a['slug'],
        'titulo': a['titulo'],
        'artista': a['artista'],
        'ano': a.get('ano', ''),
        'capa': a.get('capa', ''),
        'generos': a.get('generos', []),
        'destaque': a.get('destaque', False),
        'spotify': a.get('spotify', ''),
        'youtube': a.get('youtube', ''),
    } for a in albuns]
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(catalogo_js, f, ensure_ascii=False, indent=2)

# ---------- Gera o sitemap.xml ----------
paginas_estaticas = ['', 'gravadora.html', 'manifesto.html', 'quem-somos.html',
                     'editora.html', 'audiovisual.html', 'projetos.html',
                     'blog.html', 'contato.html']
urls = [DOMINIO + '/' + p for p in paginas_estaticas] + \
       [DOMINIO + '/albuns/' + s + '.html' for s in geradas]
hoje = datetime.now().strftime('%Y-%m-%d')
sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for u in urls:
    sitemap += '  <url><loc>' + u + '</loc><lastmod>' + hoje + '</lastmod></url>\n'
sitemap += '</urlset>\n'
with open(OUT_SITEMAP, 'w', encoding='utf-8') as f:
    f.write(sitemap)

# ---------- Relatório ----------
# ---------- Gera o blog.html ----------
if True:   # gera sempre
    itens = []
    for i, p in enumerate(posts):
        data_br = str(p.get('date', '')).split('-')[::-1]
        data_str = '/'.join(data_br[:3]) if len(data_br) == 3 else str(p.get('date', ''))
        img_html = ''
        if p.get('imagem'):
            img_html = ('<img src="' + caminho(p['imagem']) + '" alt="" style="width:110px;height:74px;'
                        'object-fit:cover;border-radius:2px;flex-shrink:0" loading="lazy">')
        itens.append(
            '<a class="song-item fade-in" href="#noticia-' + str(i) + '">'
            '<div class="song-num">' + str(i + 1) + '</div>'
            '<div class="song-info">'
            '<div class="song-title">' + esc(p['title']) + '</div>'
            '<div class="song-artist">' + esc(p['resumo']) + '</div>'
            '</div>'
            '<span class="song-platform">' + data_str + '</span>'
            '<div class="song-play"><svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg></div>'
            '</a>'
        )
    corpo_posts = '\n\n'.join(
        '<article id="noticia-' + str(i) + '" style="max-width:760px;margin:3.5rem auto 0;padding:2rem;'
        'background:var(--bg-card);border:1px solid var(--border-color-light);border-radius:4px">'
        '<div style="font-size:.65rem;letter-spacing:2px;text-transform:uppercase;color:var(--brand-accent);margin-bottom:.8rem">'
        + '/'.join(str(p.get('date', '')).split('-')[::-1]) + '</div>'
        '<h2 style="font-size:1.3rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:1rem">' + esc(p['title']) + '</h2>'
        + ('<img src="' + caminho(p['imagem']) + '" alt="" style="width:100%;border-radius:4px;margin-bottom:1.5rem" loading="lazy">' if p.get('imagem') else '')
        + '<div style="font-size:.95rem;line-height:1.9;color:var(--text-secondary);white-space:pre-line">' + esc(p['corpo']) + '</div>'
        '</article>'
        for i, p in enumerate(posts)
    )
    blog_html = BLOG_TEMPLATE.replace('BASE', BASE).replace('<!-- POSTS LISTA -->', '\n'.join(itens)).replace('<!-- POSTS CORPO -->', corpo_posts)
    with open(os.path.join(BASE_DIR, 'blog.html'), 'w', encoding='utf-8') as f:
        f.write(blog_html)
    print('✔ blog.html gerado com ' + str(len(posts)) + ' notícias')

print('✔ ' + str(len(geradas)) + ' páginas de álbum geradas (BASE = ' + (BASE or '(raiz)') + ')')
for s in geradas:
    print('   albuns/' + s + '.html')
print('✔ data/catalogo.json regenerado (base: ' + BASE + ')')
print('✔ sitemap.xml com ' + str(len(urls)) + ' URLs → ' + DOMINIO)
if not geradas:
    print('⚠ NENHUM .md encontrado em content/albuns/ — crie os arquivos primeiro!')
