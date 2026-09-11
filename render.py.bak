#!/usr/bin/env python3
# ==========================================================
# POR DO SOM — Render do catálogo (v3 — com BASE path)
#
# Fonte de dados: content/albuns/*.md (editáveis pelo painel)
# Gera:
#   - albuns/{slug}.html (páginas dos álbuns, com Schema.org)
#   - data/catalogo.json (para o JS da vitrine/gravadora)
#   - sitemap.xml
#
# ⚠️ REGRA DA BASE (documentada no mapa de ação):
#   BASE = caminho onde o site está hospedado.
#   - No GitHub Pages de projeto: '/pordosom-site'
#   - No dia do domínio próprio (pordosom.com.br na raiz): ''
#     (trocar AQUI, no js/catalogo.js e rodar o sed inverso nos
#      HTMLs da raiz — 3 pontos documentados, nada mais muda)
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
# A BASE — único ponto de configuração de caminho daqui
# ════════════════════════════════════════════════════════
BASE = '/pordosom-site'
DOMINIO = 'https://kleber-albuquerque.github.io' + BASE   # sitemap aponta para o Pages real

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
    """Junta a BASE com um caminho — a função usada em TODO o template."""
    return f'{BASE}{c}' if c.startswith('/') else c

def embed_spotify(url):
    if not url:
        return ''
    return url.replace('open.spotify.com/', 'open.spotify.com/embed/')

def embed_youtube(url):
    if not url:
        return ''
    m = re.search(r'(?:v=|youtu\.be/|embed/)([\w-]{11})', url)
    if m:
        return f'https://www.youtube.com/embed/{m.group(1)}'
    return ''

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

# ---------- Template da página de álbum (com BASE) ----------
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
    sp_embed = embed_spotify(a.get('spotify', ''))
    if sp_embed:
        embeds_html += f'\n        <iframe src="{esc(sp_embed)}" height="152" loading="lazy" title="Ouvir no Spotify"></iframe>'
    yt_embed = embed_youtube(a.get('youtube', ''))
    if yt_embed:
        embeds_html += f'\n        <iframe src="{esc(yt_embed)}" style="aspect-ratio:16/9" loading="lazy" allowfullscreen title="Vídeo do álbum"></iframe>'

    plats = []
    if a.get('spotify'): plats.append(('Spotify', a['spotify']))
    if a.get('youtube'): plats.append(('YouTube', a['youtube']))
    if a.get('apple'): plats.append(('Apple Music', a['apple']))
    if a.get('deezer'): plats.append(('Deezer', a['deezer']))
    plats_html = ''.join(
        f'<a class="plat-link" href="{esc(u)}" target="_blank" rel="noopener">{esc(n)}</a>'
        for n, u in plats)

    en_html = ''
    if a.get('texto_en'):
        en_html = f'<p class="album-descricao-en">{esc(a["texto_en"])}</p>'

        prev_html = (f'<a class="album-nav-link" href="{caminho("/albuns/" + prev["slug"] + ".html")}">← {esc(prev["titulo"])}</a>'
                 if prev else '<span></span>')
    next_html = (f'<a class="album-nav-link" href="{caminho("/albuns/" + next_["slug"] + ".html")}">{esc(next_["titulo"])} →</a>'
                 if next_ else '<span></span>')

    faixas_txt = f'{a.get("faixas")} faixas · ' if a.get('faixas') else ''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(a['titulo'])} — {esc(a['artista'])} | Por do Som</title>
<meta name="description" content="{esc((a['texto_pt'] or a['titulo'])[:155])}">
<meta property="og:title" content="{esc(a['titulo'])}">
<meta property="og:description" content="{esc((a['texto_pt'] or '')[:110])}">
<meta property="og:type" content="music.album">
<link rel="icon" type="image/jpeg" href="{caminho('/pordosom-profile.jpg')}">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{caminho('/css/style.css')}">
<script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=2)}
</script>
</head>
<body class="page-interna">

<header class="header" id="header">
    <a href="{caminho('/')}" class="logo">
        <span class="logo-mark"><img src="{caminho('/pordosom-profile.jpg')}" alt="Por do Som"></span>
        <span class="logo-text">PÔR DO SOM</span>
    </a>
    <nav class="nav" id="nav">
        <a href="{caminho('/gravadora.html')}" class="nav-link">Gravadora</a>
        <a href="{caminho('/projetos.html')}" class="nav-link">Projetos</a>
        <a href="{caminho('/audiovisual.html')}" class="nav-link">Audiovisual</a>
        <a href="{caminho('/blog.html')}" class="nav-link">Notícias</a>
        <a href="{caminho('/manifesto.html')}" class="nav-link">Manifesto</a>
        <a href="{caminho('/quem-somos.html')}" class="nav-link">Quem Somos</a>
        <a href="{caminho('/contato.html')}" class="nav-link nav-cta">Fale com o Selo</a>
    </nav>
    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>
</header>

<main class="album-page">
    <div class="container">
        <div class="album-hero">
            <div class="album-capa-grande">
                <img src="{caminho(a.get('capa', ''))}" alt="Capa do álbum {esc(a['titulo'])}"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 600 600%22%3E%3Crect fill=%22%231a0e0e%22 width=%22600%22 height=%22600%22/%3E%3Ccircle cx=%22300%22 cy=%22260%22 r=%22100%22 fill=%22%23a83030%22 opacity=%220.75%22/%3E%3C/svg%3E'">
            </div>
            <div>
                <span class="album-kicker">Álbum · {esc(a.get('ano', ''))} · {esc(generos_str)}</span>
                <h1 class="album-titulo-grande">{esc(a['titulo'])}</h1>
                <div class="album-artista-grande">{esc(a['artista'])}</div>
                <div class="album-meta-info">{faixas_txt}Por do Som</div>

                <p class="album-descricao">{esc(a['texto_pt'])}</p>
                {en_html}

                <div class="album-embeds">{embeds_html}
                </div>
                <div class="album-plataformas">{plats_html}</div>
            </div>
        </div>

        <div class="album-navegacao">
            {prev_html}
            <a class="album-nav-link" href="{caminho('/gravadora.html')}">Voltar ao catálogo</a>
            {next_html}
        </div>
    </div>
</main>

<footer class="footer">
    <div class="container">
        <span class="footer-logo">PÔR DO SOM</span>
        <p class="footer-tagline">Selo Independente · Brasilidades</p>
        <p class="footer-text">© {datetime.now().year} Por do Som</p>
    </div>
</footer>

<script>
const menuBtn = document.getElementById('mobileMenuBtn');
const nav = document.getElementById('nav');
menuBtn.addEventListener('click', () => nav.classList.toggle('active'));
</script>
</body>
</html>'''

# ---------- Gera as páginas ----------
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

# ---------- Gera o data/catalogo.json (com BASE para o JS) ----------
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
urls = [f'{DOMINIO}/{p}' for p in paginas_estaticas] + \
       [f'{DOMINIO}/albuns/{s}.html' for s in geradas]
hoje = datetime.now().strftime('%Y-%m-%d')
sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for u in urls:
    sitemap += f'  <url><loc>{u}</loc><lastmod>{hoje}</lastmod></url>\n'
sitemap += '</urlset>\n'
with open(OUT_SITEMAP, 'w', encoding='utf-8') as f:
    f.write(sitemap)

# ---------- Relatório ----------
print(f'✔ {len(geradas)} páginas de álbum geradas (BASE = {BASE or "(raiz)"})')
for s in geradas:
    print(f'   albuns/{s}.html')
print(f'✔ data/catalogo.json regenerado (com base: {BASE})')
print(f'✔ sitemap.xml com {len(urls)} URLs → {DOMINIO}')
if not geradas:
    print('⚠ NENHUM .md encontrado em content/albuns/ — crie os arquivos primeiro!')
