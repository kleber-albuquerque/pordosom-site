#!/usr/bin/env python3
# ==========================================================
# POR DO SOM — render.py v4 (consolidado)
#
# Lê:  content/albuns/*.md      (catálogo)
#      content/posts/*.md       (notícias)
#      content/audiovisual/*.md (clips)
# Gera: albuns/*.html, data/catalogo.json,
#       blog.html, audiovisual.html, sitemap.xml
#
# ⚠️ REGRA DA BASE: '/pordosom-site' no Pages | '' no domínio
# ==========================================================
import os, re, json, html
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_MD = os.path.join(BASE_DIR, 'content', 'albuns')
PASTA_POSTS = os.path.join(BASE_DIR, 'content', 'posts')
PASTA_AV = os.path.join(BASE_DIR, 'content', 'audiovisual')
OUT_ALBUNS = os.path.join(BASE_DIR, 'albuns')
OUT_JSON = os.path.join(BASE_DIR, 'data', 'catalogo.json')
OUT_SITEMAP = os.path.join(BASE_DIR, 'sitemap.xml')

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

GRUPOS_AV = {
    'sotaques': 'Série Sotaques do Brasil',
    'malungo': 'Festival Malungo',
    'mestres': 'Festival Mestres dos Saberes',
    'outros': 'Outros vídeos do canal',
}

# ---------- Parser de frontmatter ----------
def parse_md(caminho):
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
                if not isinstance(meta.get(lista_atual), list):
                    if lista_atual in meta:
                        meta[lista_atual] = [meta[lista_atual]]
                    else:
                        meta[lista_atual] = []
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
    if not c:
        return c
    if isinstance(c, list):
        c = c[0] if c else ''
    if not isinstance(c, str):
        c = str(c)
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

# ---------- Lê os álbuns ----------
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
        if isinstance(meta.get('generos'), str):
            meta['generos'] = [x.strip() for x in meta['generos'].replace('[','').replace(']','').split(',') if x.strip()]
        if isinstance(meta.get('capa'), list):
            meta['capa'] = meta['capa'][0] if meta['capa'] else ''
        albuns.append(meta)

# Ordenação: com ordem: primeiro; sem: ano desc
def _tem_ordem(a):
    o = a.get('ordem')
    if isinstance(o, list):
        o = o[0] if o else None
    try:
        return o is not None and str(o).strip() != ''
    except Exception:
        return False

_com = [a for a in albuns if _tem_ordem(a)]
_sem = [a for a in albuns if not _tem_ordem(a)]
_com.sort(key=lambda a: int(str(a.get('ordem')).strip()))
_sem.sort(key=lambda a: (str(a.get('ano', '')), a['titulo']), reverse=True)
albuns[:] = _com + _sem

# ---------- Lê as notícias ----------
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

# ---------- Lê os clips ----------
clips = []
if os.path.isdir(PASTA_AV):
    for nome in sorted(os.listdir(PASTA_AV)):
        if not nome.endswith('.md'):
            continue
        meta, corpo = parse_md(os.path.join(PASTA_AV, nome))
        meta.setdefault('titulo', nome[:-3])
        meta.setdefault('grupo', 'outros')
        meta.setdefault('ano', '')
        meta.setdefault('artista', '')
        meta.setdefault('yt_id', '')
        clips.append(meta)
clips.sort(key=lambda c: str(c.get('ano', '')))

# ---------- Lê os projetos ----------
PASTA_PROJ = os.path.join(BASE_DIR, 'content', 'projetos')
projetos = []
if os.path.isdir(PASTA_PROJ):
    for nome in sorted(os.listdir(PASTA_PROJ)):
        if not nome.endswith('.md'):
            continue
        meta, corpo = parse_md(os.path.join(PASTA_PROJ, nome))
        meta.setdefault('titulo', nome[:-3])
        meta.setdefault('status', 'realizado')
        meta.setdefault('badge', 'Projeto')
        meta.setdefault('ano', '')
        meta.setdefault('imagem', '')
        meta.setdefault('link', '')
        meta.setdefault('relatorio', '')
        meta.setdefault('tags', [])
        meta['corpo'] = corpo
        if isinstance(meta.get('tags'), str):
            meta['tags'] = [t.strip() for t in meta['tags'].split(',') if t.strip()]
        projetos.append(meta)
projetos.sort(key=lambda p: str(p.get('ano', '')), reverse=True)

# ---------- Le o config do site ----------
SITE_CFG = {}
cfg_path = os.path.join(BASE_DIR, 'content', 'config', 'site.md')
if os.path.exists(cfg_path):
    cfg_meta, _ = parse_md(cfg_path)
    SITE_CFG = cfg_meta

# ---------- Template da página de álbum ----------
NAV_HTML = (
    '        <a href="' + BASE + '/" class="nav-link">Home</a>\n'
    '        <a href="' + BASE + '/gravadora.html" class="nav-link">Gravadora</a>\n'
    '        <a href="' + BASE + '/projetos.html" class="nav-link">Projetos</a>\n'
    '        <a href="' + BASE + '/audiovisual.html" class="nav-link">Audiovisual</a>\n'
    '        <a href="' + BASE + '/blog.html" class="nav-link">Notícias</a>\n'
    '        <a href="' + BASE + '/manifesto.html" class="nav-link">Manifesto</a>\n'
    '        <a href="' + BASE + '/quem-somos.html" class="nav-link">Quem Somos</a>\n'
)

FOOTER_HTML = (
'<footer class="footer">\n'
'    <div class="container">\n'
'        <span class="footer-logo">PÔR DO SOM</span>\n'
'        <p class="footer-tagline">Selo Independente · Brasilidades</p>\n'
'        <p class="footer-text">© ' + str(datetime.now().year) + ' Por do Som</p>\n'
'    </div>\n'
'</footer>\n'
)

def page_album(a, prev, next_):
    generos_str = ' · '.join(GENEROS.get(g, g) for g in (a.get('generos') or []))
    schema = {
        "@context": "https://schema.org",
        "@type": "MusicAlbum",
        "name": a['titulo'],
        "byArtist": {"@type": "MusicGroup", "name": a['artista']},
        "genre": generos_str,
        "datePublished": str(a.get('ano', '')),
        "publisher": {"@type": "Organization", "name": "Por do Som"},
    }
    embeds_html = ''
    sp = embed_spotify(a.get('spotify', ''))
    if sp:
        embeds_html += '\n        <iframe src="' + esc(sp) + '" height="152" loading="lazy" title="Ouvir no Spotify"></iframe>'
    yt = embed_youtube(a.get('youtube', ''))
    if yt:
        embeds_html += '\n        <iframe src="' + esc(yt) + '" style="aspect-ratio:16/9" loading="lazy" allowfullscreen title="Vídeo do álbum"></iframe>'

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

    prev_html = '<span></span>'
    if prev:
        href_p = caminho('/albuns/' + prev['slug'] + '.html')
        prev_html = '<a class="album-nav-link" href="' + href_p + '">&#8592; ' + esc(prev['titulo']) + '</a>'
    next_html = '<span></span>'
    if next_:
        href_n = caminho('/albuns/' + next_['slug'] + '.html')
        next_html = '<a class="album-nav-link" href="' + href_n + '">' + esc(next_['titulo']) + ' &#8594;</a>'

    faixas_txt = ''
    if a.get('faixas'):
        faixas_txt = str(a['faixas']) + ' faixas · '

    capa_val = a.get('capa', '')
    if isinstance(capa_val, list):
        capa_val = capa_val[0] if capa_val else ''
    capa_attr = esc(capa_val) if capa_val else ''

    return (
'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n'
'<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>' + esc(a['titulo']) + ' — ' + esc(a['artista']) + ' | Por do Som</title>\n'
'<meta name="description" content="' + esc((a['texto_pt'] or a['titulo'])[:155]) + '">\n'
'<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + BASE + '/css/style.css">\n'
'<script type="application/ld+json">\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n</script>\n'
'</head>\n<body class="page-interna">\n\n'
'<header class="header" id="header">\n'
'    <a href="' + BASE + '/" class="logo">\n'
'        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n'
'    </a>\n'
'    <nav class="nav" id="nav">\n' + NAV_HTML + '    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n'
'</header>\n\n'
'<main class="album-page">\n'
'    <div class="container">\n'
'        <div class="album-hero">\n'
'            <div class="album-capa-grande">\n'
'                <img src="' + esc(caminho(capa_val)) + '" alt="Capa do álbum ' + esc(a['titulo']) + '"\n'
'                     onerror="this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 600 600%22%3E%3Crect fill=%22%231a0e0e%22 width=%22600%22 height=%22600%22/%3E%3Ccircle cx=%22300%22 cy=%22260%22 r=%22100%22 fill=%22%23a83030%22 opacity=%220.75%22/%3E%3C/svg%3E\'">\n'
'            </div>\n'
'            <div>\n'
'                <span class="album-kicker">Álbum · ' + esc(a.get('ano', '')) + ' · ' + esc(generos_str) + '</span>\n'
'                <h1 class="album-titulo-grande">' + esc(a['titulo']) + '</h1>\n'
'                <div class="album-artista-grande">' + esc(a['artista']) + '</div>\n'
'                <div class="album-meta-info">' + faixas_txt + 'Por do Som</div>\n\n'
'                <p class="album-descricao">' + esc(a['texto_pt']) + '</p>\n'
+ en_html + '\n'
'                <div class="album-embeds">' + embeds_html + '\n                </div>\n'
'                <div class="album-plataformas">' + plats_html + '</div>\n'
'            </div>\n'
'        </div>\n\n'
'        <div class="album-navegacao">\n'
'            ' + prev_html + '\n'
'            <a class="album-nav-link" href="' + BASE + '/gravadora.html">Voltar ao catálogo</a>\n'
'            ' + next_html + '\n'
'        </div>\n'
'    </div>\n'
'</main>\n\n'
+ FOOTER_HTML +
'<script>\n'
'const menuBtn = document.getElementById(\'mobileMenuBtn\');\n'
'const nav = document.getElementById(\'nav\');\n'
'menuBtn.addEventListener(\'click\', () => nav.classList.toggle(\'active\'));\n'
'</script>\n'
'</body>\n</html>\n')

# ---------- Gera as páginas de álbum ----------
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

# ---------- Gera o catalogo.json (nasce limpo) ----------
def _norm_json(a):
    capa = a.get('capa', '')
    if isinstance(capa, list):
        capa = capa[0] if capa else ''
    capa = str(capa) if capa else ''
    generos = a.get('generos', [])
    if isinstance(generos, str):
        generos = [x.strip() for x in generos.replace('[', '').replace(']', '').split(',') if x.strip()]
    ano = a.get('ano', '')
    if isinstance(ano, list):
        ano = ano[0] if ano else ''
    ordem = a.get('ordem', '')
    if isinstance(ordem, list):
        ordem = ordem[0] if ordem else ''
    return {
        'slug': a['slug'],
        'titulo': str(a.get('titulo', '')),
        'artista': str(a.get('artista', '')),
        'ano': ano,
        'capa': capa,
        'generos': generos,
        'destaque': bool(a.get('destaque', False)),
        'ordem': str(ordem) if ordem else '',
        'spotify': str(a.get('spotify', '') or ''),
        'youtube': str(a.get('youtube', '') or ''),
    }

posts_js = [{
    'title': str(p.get('title', '')),
    'resumo': str(p.get('resumo', '')),
    'date': str(p.get('date', '')),
    'imagem': str(p.get('imagem', '') or ''),
} for p in posts[:3]]   # as 3 ultimas

catalogo_js = {
    'posts': posts_js,
    'base': BASE,
    'generos': [{'id': k, 'nome': v} for k, v in GENEROS.items()],
    'albuns': [_norm_json(a) for a in albuns]
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(catalogo_js, f, ensure_ascii=False, indent=2)


def md_para_html(texto):
    c = esc(texto)
    c = re.sub(r'^## (.+)$', r'<h2 style="font-size:1.3rem;text-transform:uppercase;letter-spacing:.5px;color:#f5ede0;margin:2.5rem 0 1rem">\1</h2>', c, flags=re.M)
    c = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#f5ede0">\1</strong>', c)
    c = re.sub(r'(?m)^\*(.+)\*$', r'<p style="font-style:italic;color:#7a6a5e">\1</p>', c)
    c = re.sub(r'\[(.+?)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener" style="color:#c84545">\1</a>', c)
    paragrafos = '\n<p>'.join(par for par in c.split('\n\n') if par.strip())
    c = '<p>' + paragrafos + '</p>'
    c = c.replace('<p><h2', '<h2').replace('</h2></p>', '</h2>')
    c = c.replace('<p><p style', '<p style').replace('</p></p>', '</p>')
    return c

# ---------- Gera o blog.html ----------
if True:
    itens = []
    for i, p in enumerate(posts):
        partes = str(p.get('date', '')).split('-')
        data_str = '/'.join(reversed(partes)) if len(partes) == 3 else str(p.get('date', ''))
        itens.append(
            '<a class="song-item fade-in" href="' + BASE + '/posts/' + re.sub(r'[^a-z0-9-]', '', str(p['title']).lower().replace(' ', '-')) + '.html">'
            '<div class="song-num">' + str(i + 1) + '</div>'
            '<div class="song-info">'
            '<div class="song-title">' + esc(p['title']) + '</div>'
            '<div class="song-artist">' + esc(p.get('resumo', '')) + '</div>'
            '</div>'
            '<span class="song-platform">' + data_str + '</span>'
            '<div class="song-play"><svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg></div>'
            '</a>')
    corpo_posts = []
    for i, p in enumerate(posts):
        partes = str(p.get('date', '')).split('-')
        data_str = '/'.join(reversed(partes)) if len(partes) == 3 else str(p.get('date', ''))
        img_html = ''
        if p.get('imagem'):
            img_html = ('<img src="' + caminho(p['imagem']) + '" alt="" style="width:100%;border-radius:4px;margin-bottom:1.5rem" loading="lazy">')
        corpo_posts.append(
            '<article id="noticia-' + str(i) + '" style="max-width:760px;margin:3.5rem auto 0;padding:2rem;background:#1a0e0e;border:1px solid rgba(168,48,48,.12);border-radius:4px">'
            '<div style="font-size:.65rem;letter-spacing:2px;text-transform:uppercase;color:#e8a04a;margin-bottom:.8rem">' + data_str + '</div>'
            '<h2 style="font-size:1.3rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:1rem;color:#f5ede0">' + esc(p['title']) + '</h2>'
            + img_html +
            '<div style="font-size:.95rem;line-height:1.9;color:#b8a89a;">' + md_para_html(p.get('corpo', '')) + '</div>'
            '</article>')
    lista_final = '\n'.join(itens) if itens else '<p style="text-align:center;color:var(--text-muted);padding:2rem">Em breve, as primeiras notícias do selo.</p>'
    blog_html = (
'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>Notícias | Por do Som</title>\n'
'<meta name="description" content="Notícias, lançamentos e novidades do Selo Por do Som.">\n'
'<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + BASE + '/css/style.css">\n</head>\n<body class="page-interna">\n'
'<header class="header" id="header">\n    <a href="' + BASE + '/" class="logo">\n'
'        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n'
'    <nav class="nav" id="nav">\n' + NAV_HTML + '    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
'<section class="musicas" style="padding-top:calc(var(--spacing-section) + 3rem)">\n'
'    <div class="container">\n'
'        <span class="section-subtitle">Notícias</span>\n'
'        <h1 class="section-title">Novidades <span class="gradient">do selo</span></h1>\n'
'        <p class="section-description">Lançamentos, projetos e histórias do Por do Som.</p>\n'
'        <div style="max-width:760px;margin:0 auto;display:grid;gap:1rem">\n'
+ lista_final + '\n        </div>\n'
+ '\n\n'.join(corpo_posts) + '\n    </div>\n</section>\n\n'
+ FOOTER_HTML +
'<script>\nconst menuBtn = document.getElementById(\'mobileMenuBtn\');\nconst nav = document.getElementById(\'nav\');\nmenuBtn.addEventListener(\'click\', () => nav.classList.toggle(\'active\'));\n</script>\n</body>\n</html>\n')
    with open(os.path.join(BASE_DIR, 'blog.html'), 'w', encoding='utf-8') as f:
        f.write(blog_html)

# ---------- Gera a audiovisual.html ----------
sec_template = (
'<section class="{bg}">\n'
'    <div class="container">\n'
'        <span class="section-subtitle">{sub}</span>\n'
'        <h2 class="section-title">{titulo}</h2>\n'
'        <div class="teaser-videos">\n{videos}\n        </div>\n'
'    </div>\n'
'</section>\n')

partes_pagina = []
for gid, gnome in GRUPOS_AV.items():
    do_grupo = [c for c in clips if str(c.get('grupo', '')) == gid]
    if not do_grupo:
        continue
    videos_html = []
    for c in do_grupo:
        videos_html.append(
            '            <iframe src="https://www.youtube.com/embed/' + str(c.get('yt_id', '')) + '" '
            'loading="lazy" allowfullscreen title="' + esc(c.get('titulo', '')) + '"></iframe>')
    bg = 'teaser' if len(partes_pagina) % 2 == 0 else 'teaser teaser-alt'
    partes_pagina.append(sec_template.format(bg=bg, sub='Audiovisual', titulo=esc(gnome), videos='\n'.join(videos_html)))

playlists_html = (
'<section class="teaser teaser-alt">\n'
'    <div class="container">\n'
'        <div class="teaser-head">\n'
'            <span class="section-subtitle">Playlists</span>\n'
'            <h2 class="section-title">Curadoria do <span class="gradient">selo</span></h2>\n'
'        </div>\n'
'        <div class="teaser-playlists">\n'
'            <iframe src="https://open.spotify.com/embed/playlist/' + str(SITE_CFG.get('playlist1_id','2lgoPMSE9e7lxEumGbBaGn')) + '" height="380" loading="lazy" title="Samba Raiz e Partido Alto"></iframe>\n'
'            <iframe src="https://open.spotify.com/embed/playlist/' + str(SITE_CFG.get('playlist2_id','2cyXUj8Qhe3nZ0rbng87nR')) + '" height="380" loading="lazy" title="Tambores do Brasil"></iframe>\n'
'        </div>\n'
'    </div>\n'
'</section>\n')

if partes_pagina:
    av_html = (
'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>Audiovisual &amp; Playlists | Por do Som</title>\n'
'<meta name="description" content="Vídeos e playlists curadas do Selo Por do Som — séries, festivais e o canal completo no YouTube.">\n'
'<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + BASE + '/css/style.css">\n</head>\n<body class="page-interna">\n'
'<header class="header" id="header">\n    <a href="' + BASE + '/" class="logo">\n'
'        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n'
'    <nav class="nav" id="nav">\n' + NAV_HTML + '    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
'<header class="page-header">\n    <div class="container">\n'
'        <span class="section-subtitle">Audiovisual</span>\n'
'        <h1 class="section-title">Veja e <span class="gradient">ouça</span></h1>\n'
'        <p class="section-description">A produção audiovisual do selo — séries, festivais e o canal no YouTube.</p>\n'
'    </div>\n</header>\n'
+ '\n'.join(partes_pagina) + '\n' + playlists_html + '\n'
+ FOOTER_HTML +
'<script>\nconst menuBtn = document.getElementById(\'mobileMenuBtn\');\nconst nav = document.getElementById(\'nav\');\nmenuBtn.addEventListener(\'click\', () => nav.classList.toggle(\'active\'));\n</script>\n</body>\n</html>\n')
    with open(os.path.join(BASE_DIR, 'audiovisual.html'), 'w', encoding='utf-8') as f:
        f.write(av_html)

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
# ---------- Gera a projetos.html ----------
def card_projeto(p):
    status_cls = 'status-realizado' if str(p.get('status')) == 'realizado' else 'status-captacao'
    status_lbl = '✓ Realizado' if str(p.get('status')) == 'realizado' else '★ Em captação'
    img = p.get('imagem') or ''
    if isinstance(img, list):
        img = img[0] if img else ''
    img_style = 'background-image:url(\'' + BASE + img + '\')' if img else 'background:#1a0e0e'
    tags_html = ''.join('<span class="project-tag">' + esc(t) + '</span>' for t in (p.get('tags') or []))
    rel_html = ''
    if p.get('relatorio'):
        rel_html = '<a href="' + esc(p['relatorio']) + '" target="_blank" rel="noopener" class="btn btn-ghost" style="margin-top:12px;padding:8px 16px;font-size:.65rem">📄 Relatório completo ↗</a>'
    link_html = ''
    if p.get('link'):
        link_html = '<a href="' + esc(p['link']) + '" target="_blank" rel="noopener" class="teaser-link" style="margin-top:14px">Ver projeto →</a>'
    return (
'<div class="projeto-card">'
'<div class="galeria"><img src="' + BASE + (img or '/pordosom-profile.jpg') + '" alt="' + esc(p['titulo']) + '" loading="lazy" onerror="this.style.display=\'none\'"></div>'
'<div class="projeto-corpo">'
'<span class="projeto-badge ' + status_cls + '">' + status_lbl + '</span>'
'<h3>' + esc(p['titulo']) + '</h3>'
'<p style="font-size:.9rem;line-height:1.8;color:var(--text-secondary)">' + esc(p.get('corpo', '')) + '</p>'
'<div class="project-tags">' + tags_html + '</div>'
+ link_html + rel_html +
'</div></div>')

if projetos:
    cards = '\n\n'.join(card_projeto(p) for p in projetos)
    projetos_html = (
'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>Projetos &amp; Festivais | Por do Som</title>\n'
'<meta name="description" content="Projetos culturais, festivais e séries realizados pelo Por do Som — celebrando mestres e saberes da cultura popular.">\n'
'<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + BASE + '/css/style.css">\n</head>\n<body class="page-interna">\n'
'<header class="header" id="header">\n    <a href="' + BASE + '/" class="logo">\n'
'        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n'
'    <nav class="nav" id="nav">\n' + NAV_HTML + '    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
'<header class="page-header">\n    <div class="container">\n'
'        <span class="section-subtitle">Projetos &amp; Festivais</span>\n'
'        <h1 class="section-title">Boas <span class="gradient">realizações</span></h1>\n'
'        <p class="section-description">A produção cultural do selo — do YouTube ao edital.</p>\n'
'    </div>\n</header>\n'
'<section style="padding-top:2rem">\n    <div class="container">\n'
+ cards + '\n    </div>\n</section>\n\n'
+ FOOTER_HTML +
'<script>\nconst menuBtn=document.getElementById("mobileMenuBtn");const nav=document.getElementById("nav");menuBtn.addEventListener("click",()=>nav.classList.toggle("active"));\n</script>\n</body>\n</html>\n')
    with open(os.path.join(BASE_DIR, 'projetos.html'), 'w', encoding='utf-8') as f:
        f.write(projetos_html)
    print('✔ projetos.html gerada com', len(projetos), 'projetos')


# [DESATIVADO — injetor em revisao]
# # ---------- Injeta textos do config nas paginas estaticas ----------
# def injeta_cfg(arquivo, mapa):
#     caminho = os.path.join(BASE_DIR, arquivo)
#     if not os.path.exists(caminho):
#         return
#     with open(caminho, encoding='utf-8') as f:
#         html = f.read()
#     alterado = False
#     for valor_antigo, chave_cfg in mapa:
#         novo = esc(SITE_CFG.get(chave_cfg, '')) or valor_antigo
#         if valor_antigo in html and novo != valor_antigo:
#             html = html.replace(valor_antigo, novo, 1)
#             alterado = True
#     if alterado:
#         with open(caminho, 'w', encoding='utf-8') as f:
#             f.write(html)
# 
# # hero (index)
# injeta_cfg('index.html', [
#     ('Onde a música <span class="gradient">nasce.</span>', 'hero_slogan_placeholder'),
# ])
# if SITE_CFG.get('hero_slogan'):
#     # o slogan tem span gradient — injeta por partes
#     ipath = os.path.join(BASE_DIR, 'index.html')
#     with open(ipath, encoding='utf-8') as f:
#         ih = f.read()
#     slog = str(SITE_CFG['hero_slogan'])
#     # divide na ultima palavra para o gradiente
#     partes_s = slog.rsplit(' ', 1)
#     if len(partes_s) == 2 and 'nasce' in ih:
#         ih = ih.replace('Onde a música <span class="gradient">nasce.</span>',
#                         esc(partes_s[0]) + ' <span class="gradient">' + esc(partes_s[1]) + '</span>', 1)
#     if SITE_CFG.get('hero_texto') and 'Um selo dedicado às' in ih:
#         ih = ih.replace(
#             'Um selo dedicado às <strong>Brasilidades</strong> — à cultura afro-brasileira,
#             aos mestres da tradição popular, aos tambores do norte e ao samba de raiz.
#             Onde a ancestralidade encontra o tempo presente.',
#             esc(SITE_CFG['hero_texto']), 1)
#     with open(ipath, 'w', encoding='utf-8') as f:
#         f.write(ih)
# 
# # manifesto
# if SITE_CFG.get('manifesto_texto1'):
#     mpath = os.path.join(BASE_DIR, 'manifesto.html')
#     with open(mpath, encoding='utf-8') as f:
#         mh = f.read()
#     for old, key in [
#         ('O <strong>Por do Som</strong> nasceu de uma certeza simples', 'manifesto_texto1'),
#     ]:
#         # injeta o texto completo substituindo o paragrafo antigo (aproximado)
#         pass
#     # abordagem mais segura: substitui o TEXTO entre tags <p class="manifesto-text">...</p> por ordem
#     import re as _re
#     textos = [SITE_CFG.get('manifesto_texto1',''), SITE_CFG.get('manifesto_texto2',''), SITE_CFG.get('manifesto_texto3','')]
#     idx = [0]
#     def _repl(m):
#         if idx[0] < len(textos) and textos[idx[0]]:
#             t = esc(textos[idx[0]])
#             idx[0] += 1
#             return '<p class="manifesto-text">' + t + '</p>'
#         return m.group(0)
#     mh = _re.sub(r'<p class="manifesto-text">[^<]*(?:<(?!/p>)[^<]*)*</p>', _repl, mh, count=3)
#     with open(mpath, 'w', encoding='utf-8') as f:
#         f.write(mh)
# 
# # quem somos
# if SITE_CFG.get('quemsomos_texto'):
#     qpath = os.path.join(BASE_DIR, 'quem-somos.html')
#     with open(qpath, encoding='utf-8') as f:
#         qh = f.read()
#     qh = qh.replace('[TEXTO DO CLIENTE — currículo do selo]', esc(SITE_CFG['quemsomos_texto']), 1)
#     with open(qpath, 'w', encoding='utf-8') as f:
#         f.write(qh)
# 
# # editora
# if SITE_CFG.get('editora_texto'):
#     epath = os.path.join(BASE_DIR, 'editora.html')
#     with open(epath, encoding='utf-8') as f:
#         eh = f.read()
#     eh = eh.replace('[TEXTO INSTITUCIONAL — a confirmar com o cliente]', esc(SITE_CFG['editora_texto']), 1)
#     with open(epath, 'w', encoding='utf-8') as f:
#         f.write(eh)

# ---------- Gera paginas estaticas (manifesto, quem-somos, editora) do config ----------
def _gera_pagina_estatica(arquivo, kicker, titulo_grad, textos, extra_html=''):
    """textos: lista de paragrafos (strings)"""
    paragrafos = '\n            '.join(
        '<p class="manifesto-text">' + esc(t) + '</p>' for t in textos if t)
    slog = str(SITE_CFG.get('hero_slogan', ''))
    return (
'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
'<title>' + kicker + ' | Por do Som</title>\n'
'<meta name="description" content="' + esc((textos[0] if textos else '')[:155]) + '">\n'
'<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
'<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
'<link rel="stylesheet" href="' + BASE + '/css/style.css">\n</head>\n<body class="page-interna">\n'
'<header class="header" id="header">\n    <a href="' + BASE + '/" class="logo">\n'
'        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
'        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n'
'    <nav class="nav" id="nav">\n' + NAV_HTML + '    </nav>\n'
'    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
'<section class="manifesto" style="padding-top:calc(var(--spacing-section) + 3rem)">\n'
'    <div class="container">\n'
'        <div class="manifesto-content">\n'
'            <span class="section-subtitle">' + kicker + '</span>\n'
'            <h1 class="section-title">' + titulo_grad + '</h1>\n'
'            ' + paragrafos + '\n'
+ extra_html +
'        </div>\n    </div>\n</section>\n\n'
+ FOOTER_HTML +
'<script>\nconst menuBtn=document.getElementById("mobileMenuBtn");const nav=document.getElementById("nav");menuBtn.addEventListener("click",()=>nav.classList.toggle("active"));\n</script>\n'
'</body>\n</html>\n')

def _stats_html():
    stats = [('31','Obras no catálogo'),('10+','Artistas'),('3','Festivais próprios'),('42','Vídeos produzidos')]
    linhas = '\n'.join(
        '<div class="stat-item fade-in"><div class="stat-num">' + n + '</div><div class="stat-label">' + l + '</div></div>'
        for n, l in stats)
    return '<div class="manifesto-stats">' + linhas + '</div>'

# manifesto
_textos_m = [SITE_CFG.get('manifesto_texto1',''), SITE_CFG.get('manifesto_texto2',''), SITE_CFG.get('manifesto_texto3','')]
if any(_textos_m):
    with open(os.path.join(BASE_DIR, 'manifesto.html'), 'w', encoding='utf-8') as f:
        f.write(_gera_pagina_estatica('manifesto.html', 'Manifesto',
            'Som que <span class="gradient">pulsa Brasil</span>', _textos_m,
            '<p class="manifesto-signature">— Por do Som Cultural</p>' + _stats_html()))
    print('✔ manifesto.html regenerada do config')

# quem somos
_textos_q = [SITE_CFG.get('quemsomos_texto','')]
if any(_textos_q):
    portfolio = str(SITE_CFG.get('portfolio_link','') or '')
    port_html = ''
    if portfolio:
        port_html = ('<div style="margin-top:3rem" class="fade-in">'
                     '<a href="' + esc(portfolio) + '" target="_blank" rel="noopener" class="btn btn-outline" style="text-decoration:none">'
                     'Currículo completo &amp; Portfolio ↗</a></div>')
    with open(os.path.join(BASE_DIR, 'quem-somos.html'), 'w', encoding='utf-8') as f:
        f.write(_gera_pagina_estatica('quem-somos.html', 'Quem Somos',
            'Mais de 20 anos <span class="gradient">cantando o Brasil</span>', _textos_q,
            port_html + _stats_html()))
    print('✔ quem-somos.html regenerada do config')

# editora
_textos_e = [SITE_CFG.get('editora_texto','')]
if any(_textos_e):
    with open(os.path.join(BASE_DIR, 'editora.html'), 'w', encoding='utf-8') as f:
        f.write(_gera_pagina_estatica('editora.html', 'Editora & Direitos',
            'Administração de <span class="gradient">obras musicais</span>', _textos_e,
            '<p class="manifesto-signature">Consultoria: <a href="' + BASE + '/contato.html" style="color:var(--brand-primary-light);text-decoration:none">fale com o selo</a></p>'))
    print('✔ editora.html regenerada do config')

# hero do index (slogan + texto)
if SITE_CFG.get('hero_slogan') or SITE_CFG.get('hero_texto'):
    ipath = os.path.join(BASE_DIR, 'index.html')
    with open(ipath, encoding='utf-8') as f:
        ih = f.read()
    slog = str(SITE_CFG.get('hero_slogan', ''))
    if slog and 'Onde a música' in ih:
        partes = slog.rsplit(' ', 1)
        if len(partes) == 2:
            ih = ih.replace('Onde a música <span class="gradient">nasce.</span>',
                            esc(partes[0]) + ' <span class="gradient">' + esc(partes[1]) + '</span>', 1)
    htxt = str(SITE_CFG.get('hero_texto', ''))
    if htxt and 'Um selo dedicado às' in ih:
        import re as _r2
        ih = _r2.sub(r'Um selo dedicado às[\s\S]*?tempo presente\.', esc(htxt), ih, count=1)
    with open(ipath, 'w', encoding='utf-8') as f:
        f.write(ih)
    print('✔ hero do index atualizado do config')

# ---------- Injeta titulos/descricoes das secoes (todas as paginas) ----------
def _troca(arquivo, pares):
    """pares: lista de (texto_antigo, chave_cfg)"""
    caminho = os.path.join(BASE_DIR, arquivo)
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding='utf-8') as f:
        h = f.read()
    mudou = False
    for antigo, chave in pares:
        novo = SITE_CFG.get(chave, '')
        if novo and antigo in h:
            h = h.replace(antigo, esc(str(novo)), 1)
            mudou = True
    if mudou:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(h)

_troca('gravadora.html', [
    ('O catálogo <span class="gradient">completo</span>', 'grav_titulo_raw'),
])
_troca('index.html', [
    ('Lançamentos & <span class="gradient">clássicos do selo</span>', 'idx_vitrine_titulo'),
])
_troca('projetos.html', [
    ('Onde a <span class="gradient">tradição encontra palco</span>', 'projetos_titulo_raw'),
])

# abordagem robusta para todos: substitui o CONTEUDO dos spans por chave mapeada
_MAPA_TITULOS = [
    ('gravadora.html', 'O catálogo', 'grav_titulo'),
    ('gravadora.html', 'Artistas que', 'artistas_titulo'),
    ('projetos.html', 'Onde a tradição', 'projetos_titulo'),
    ('audiovisual.html', 'Veja e', 'audio_titulo'),
    ('blog.html', 'Novidades', 'noticias_titulo'),
    ('quem-somos.html', 'Mais de 20 anos', 'quemsomos_titulo'),
    ('index.html', 'Lançamentos', 'idx_vitrine_titulo'),
]

# descricoes (textos simples, mais faceis)
_MAPA_DESC = [
    ('gravadora.html', 'Cada obra com página própria', 'grav_descricao'),
    ('gravadora.html', 'Compositores, intérpretes e mestres', 'artistas_descricao'),
    ('projetos.html', 'Séries audiovisuais, festivais e homenagens', 'projetos_descricao'),
    ('audiovisual.html', 'A produção audiovisual do selo', 'audio_descricao'),
    ('blog.html', 'Lançamentos, projetos e histórias do Por do Som', 'noticias_descricao'),
]

def _troca_desc(arquivo, inicio_antigo, chave):
    caminho = os.path.join(BASE_DIR, arquivo)
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding='utf-8') as f:
        h = f.read()
    novo = SITE_CFG.get(chave, '')
    if not novo or inicio_antigo not in h:
        return
    import re as _rd
    # substitui o paragrafo de descricao que comeca com o texto antigo
    h = _rd.sub(_rd.escape(inicio_antigo) + r'[^<]*', esc(str(novo)), h, count=1)
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(h)

for arq, ini, chave in _MAPA_DESC:
    _troca_desc(arq, ini, chave)
print('✔ teasers da home atualizados do config')


# ---------- TROCADOR DE TEXTOS (home e paginas, por contexto) ----------
def _set_titulo_com_gradient(h, chave, tag='h2'):
    """Troca o conteudo de <tag class="section-title">...<span gradient>X</span></tag>
       preservando o gradient na ultima palavra do novo texto."""
    novo = SITE_CFG.get(chave, '')
    if not novo:
        return h, False
    pat = r'<' + tag + r' class="section-title">([^<]*)<span class="gradient">([^<]*)</span></' + tag + r'>'
    m = re.search(pat, h)
    if not m:
        return h, False
    partes = str(novo).rsplit(' ', 1)
    if len(partes) != 2:
        partes = [str(novo), '']
    novo_html = ('<' + tag + ' class="section-title">' + esc(partes[0]) +
                 (' <span class="gradient">' + esc(partes[1]) + '</span>' if partes[1] else '') +
                 '</' + tag + '>')
    h = h[:m.start()] + novo_html + h[m.end():]
    return h, True

def _set_texto(h, chave, inicio_antigo):
    """Troca o texto que comeca com inicio_antigo ate a proxima tag <."""
    novo = SITE_CFG.get(chave, '')
    if not novo or inicio_antigo not in h:
        return h, False
    h, n = re.subn(re.escape(inicio_antigo) + r'[^<]*', esc(str(novo)), h, count=1)
    return h, n > 0

def _processa(arquivo, operacoes, h1=False):
    caminho = os.path.join(BASE_DIR, arquivo)
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding='utf-8') as f:
        h = f.read()
    mudou = False
    for op in operacoes:
        if op[0] == 'titulo':
            h, ok = _set_titulo_com_gradient(h, op[1], 'h1' if h1 else 'h2')
        else:
            h, ok = _set_texto(h, op[1], op[2])
        if ok: mudou = True
    if mudou:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(h)
        print('  ✔ ' + arquivo)

# HOME — os teasers na ordem em que aparecem ao rolar
_processa('index.html', [
    ('titulo', 'home_vitrine_titulo'),
    ('texto', 'home_vitrine_descricao', 'Uma seleção do catálogo'),
    ('titulo', 'home_projetos_titulo'),
    ('texto', 'home_projetos_descricao', 'Séries audiovisuais e festivais'),
    ('titulo', 'home_audio_titulo'),
    ('titulo', 'home_playlists_titulo'),
])

# GRAVADORA (a pagina)
_processa('gravadora.html', [
    ('titulo', 'grav_titulo'),
    ('texto', 'grav_descricao', 'Cada obra com página própria'),
    ('titulo', 'artistas_titulo'),
    ('texto', 'artistas_descricao', 'Compositores, intérpretes e mestres'),
])

# PROJETOS
_processa('projetos.html', [
    ('titulo', 'projetos_titulo'),
    ('texto', 'projetos_descricao', 'Séries audiovisuais, festivais e homenagens'),
])

# BLOG
_processa('blog.html', [
    ('titulo', 'noticias_titulo'),
    ('texto', 'noticias_descricao', 'Lançamentos, projetos e histórias'),
])

print('✔ ' + str(len(geradas)) + ' páginas de álbum geradas (BASE = ' + (BASE or '(raiz)') + ')')
print('✔ blog.html gerado com ' + str(len(posts)) + ' notícias')
print('✔ audiovisual.html gerada com ' + str(len(clips)) + ' vídeos em ' + str(len(partes_pagina)) + ' grupos')
print('✔ data/catalogo.json regenerado (base: ' + BASE + ')')
print('✔ sitemap.xml com ' + str(len(urls)) + ' URLs → ' + DOMINIO)
if not geradas:
    print('⚠ NENHUM .md em content/albuns/!')
