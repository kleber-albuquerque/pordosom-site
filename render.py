#!/usr/bin/env python3
# ==========================================================
# POR DO SOM — render.py v5 (consolidado)
# A ÚNICA fonte: content/*.md → gera TUDO:
#   site.html (o site inteiro, seções por âncoras)
#   albuns/*.html (páginas individuais — deep-link/SEO)
#   posts/*.html (páginas de notícia)
#   data/catalogo.json + sitemap.xml
# Sem HTML à mão. Sem injeção regex. Uma técnica: geração.
# ==========================================================
import os, re, json, html
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA = {
    'albuns': os.path.join(BASE_DIR, 'content', 'albuns'),
    'posts': os.path.join(BASE_DIR, 'content', 'posts'),
    'projetos': os.path.join(BASE_DIR, 'content', 'projetos'),
    'audiovisual': os.path.join(BASE_DIR, 'content', 'audiovisual'),
    'config': os.path.join(BASE_DIR, 'content', 'config'),
}

BASE = '/pordosom-site'
DOMINIO = 'https://kleber-albuquerque.github.io' + BASE

GENEROS = {
    'samba-de-raiz': 'Samba de Raiz', 'instrumental': 'Instrumental',
    'mpb': 'MPB/Nova MPB', 'brasilidades': 'Brasilidades',
    'cultura-popular': 'Cultura Popular', 'afro-brasileira': 'Afro-brasileira',
    'infantil': 'Infantil',
}
GRUPOS_AV = {
    'sotaques': 'Série Sotaques do Brasil', 'malungo': 'Festival Malungo',
    'mestres': 'Festival Mestres dos Saberes', 'outros': 'Outros vídeos do canal',
}

# ---------- Parser ----------
def parse_md(caminho):
    with open(caminho, encoding='utf-8') as f:
        texto = f.read()
    meta, corpo = {}, texto
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', texto, re.DOTALL)
    if m:
        bloco, corpo = m.group(1), m.group(2)
        lista = None
        for linha in bloco.split('\n'):
            mi = re.match(r'^\s+-\s+(\S+)\s*$', linha)
            if mi and lista:
                if not isinstance(meta.get(lista), list):
                    meta[lista] = [meta[lista]] if lista in meta else []
                meta[lista].append(mi.group(1))
                continue
            mk = re.match(r'^(\w[\w_-]*):\s*(.*)$', linha)
            if mk:
                k, v = mk.group(1), mk.group(2).strip()
                lista = k
                ms = re.match(r'^"(.*)"$', v) or re.match(r"^'(.*)'$", v)
                if ms: meta[k] = ms.group(1)
                elif v == '': meta[k] = []
                elif re.match(r'^\d+$', v): meta[k] = int(v)
                elif v in ('true', 'false'): meta[k] = v == 'true'
                else: meta[k] = v
    return meta, corpo.strip()

def esc(t):
    return html.escape(str(t or ''))

def cfg_str(chave, default=''):
    v = SITE_CFG.get(chave, default)
    if isinstance(v, list): v = v[0] if v else ''
    return str(v) if v is not None else default

def slugify(t):
    t = re.sub(r'[^a-z0-9\s-]', '', str(t or '').lower())
    return re.sub(r'[\s-]+', '-', t.strip())

def yt_id(url):
    m = re.search(r'(?:v=|youtu\.be/|embed/)([\w-]{11})', str(url or ''))
    return m.group(1) if m else ''

def sp_embed(url):
    return str(url or '').replace('open.spotify.com/', 'open.spotify.com/embed/')

def md_html(texto):
    c = esc(texto)
    c = re.sub(r'^## (.+)$', r'<h2 style="font-size:1.25rem;text-transform:uppercase;letter-spacing:.5px;color:var(--text-primary);margin:2.2rem 0 1rem">\1</h2>', c, flags=re.M)
    c = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:var(--text-primary)">\1</strong>', c)
    c = re.sub(r'(?m)^\*(.+)\*$', r'<p style="font-style:italic;color:var(--text-muted)">\1</p>', c)
    c = re.sub(r'\[(.+?)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener" style="color:var(--brand-primary-light)">\1</a>', c)
    c = '<p>' + '\n<p>'.join(p for p in c.split('\n\n') if p.strip()) + '</p>'
    c = c.replace('<p><h2', '<h2').replace('</h2></p>', '</h2>')
    c = c.replace('<p><p style', '<p style').replace('</p></p>', '</p>')
    return c

# ---------- Leitura de TODOS os dados ----------
def _ler(pasta):
    itens = []
    if os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            if nome.endswith('.md'):
                meta, corpo = parse_md(os.path.join(pasta, nome))
                meta['corpo'] = corpo
                meta['slug'] = nome[:-3]
                itens.append(meta)
    return itens

albuns = _ler(PASTA['albuns'])
artistas = _ler(os.path.join(BASE_DIR, 'content', 'artistas'))
posts = _ler(PASTA['posts'])
projetos = _ler(PASTA['projetos'])
clips = _ler(PASTA['audiovisual'])
SITE_CFG = {}
cfg_path = os.path.join(PASTA['config'], 'site.md')
if os.path.exists(cfg_path):
    SITE_CFG, _ = parse_md(cfg_path)

# normalizacoes (a blindagem herdada)
for a in albuns:
    if isinstance(a.get('capa'), list): a['capa'] = a['capa'][0] if a['capa'] else ''
    if isinstance(a.get('generos'), str):
        a['generos'] = [x.strip() for x in a['generos'].replace('[','').replace(']','').split(',') if x.strip()]
    if not isinstance(a.get('generos'), list): a['generos'] = []
    a.setdefault('titulo', a['slug'].replace('-',' ').title())
    a.setdefault('artista', ''); a.setdefault('ano', ''); a.setdefault('destaque', False)

posts = [p for p in posts if str(p.get('rascunho')).lower() != 'true']
posts.sort(key=lambda p: str(p.get('date','')), reverse=True)

# ordenacao do catalogo: com ordem: primeiro; sem: ano desc
def _ordem(a):
    o = a.get('ordem')
    if isinstance(o, list): o = o[0] if o else None
    try: return (0, int(str(o).strip())) if o is not None and str(o).strip() else (1, 0)
    except: return (1, 0)
albuns.sort(key=lambda a: (_ordem(a)[0], _ordem(a)[1], str(a.get('ano',''))), reverse=False)
_com = [a for a in albuns if _ordem(a)[0] == 0]
_sem = [a for a in albuns if _ordem(a)[0] == 1]
_sem.sort(key=lambda a: (str(a.get('ano','')), a['titulo']), reverse=True)
albuns[:] = sorted(_com, key=_ordem) + _sem

# ---------- Templates compartilhados ----------
def _nav(ativo=None):
    ITENS = [('Home', BASE + '/site.html'), ('Gravadora', '#gravadora'),
             ('Projetos', '#projetos'), ('Editora & Direitos', '#editora'),
             ('Audiovisual', '#audiovisual'), ('Playlists', '#playlists'),
             ('Notícias/Blog', '#noticias'), ('Quem Somos', '#quemsomos'),
             ('Contato', '#contato')]
    # na home: ancoras; nas demais: links para site.html#ancora
    linhas = []
    for nome, href in ITENS:
        if href.startswith('#') and not ATUAL_EH_HOME:
            href = BASE + '/site.html' + href
        st = ' style="color:var(--brand-primary-light)"' if nome == ativo else ''
        linhas.append('        <a href="' + href + '" class="nav-link"' + st + '>' + nome + '</a>')
    return ('<nav class="nav" id="nav">\n' + '\n'.join(linhas) + '\n    </nav>')

ATUAL_EH_HOME = True  # controla o _nav por contexto

def _footer():
    return ('<footer class="footer">\n    <div class="container">\n'
            '        <span class="footer-logo">PÔR DO SOM</span>\n'
            '        <p class="footer-tagline">Selo Independente · Produtora Cultural · Brasilidades</p>\n'
            '        <div class="footer-social">\n'
            '            <a href="https://www.instagram.com/pordosomcultural" target="_blank" rel="noopener">Instagram</a>\n'
            '            <a href="https://www.youtube.com/user/pordosomcultural" target="_blank" rel="noopener">YouTube</a>\n'
            '            <a href="https://open.spotify.com/user/pordosom" target="_blank" rel="noopener">Spotify</a>\n'
            '            <a href="https://www.facebook.com/pordosomcultural" target="_blank" rel="noopener">Facebook</a>\n'
            '            <a href="https://tiktok.com/@pordosom" target="_blank" rel="noopener">TikTok</a>\n'
            '            <a href="https://linktr.ee/pordosom" target="_blank" rel="noopener">Linktree</a>\n'
            '        </div>\n'
            '        <p class="footer-text">© ' + str(datetime.now().year) + ' Por do Som Cultural · Todos os direitos reservados</p>\n'
            '        <div style="margin-top:2rem;padding-top:1.5rem;border-top:1px solid var(--border-color, #332020);text-align:center;opacity:0.5">\n'
            '            <a href="https://kaagenciacriativa.com.br/" target="_blank" rel="noopener" style="text-decoration:none;display:inline-flex;align-items:center;gap:0.5rem;color:var(--text-muted, #999);transition:opacity 0.3s" onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.5\'">\n'
            '                <div style="width:28px;height:28px;background:linear-gradient(135deg,#000 0%,#1a1a1a 100%);border-radius:50%;display:flex;align-items:center;justify-content:center;border:1px solid var(--brand-accent, #FFD700)">\n'
            '                    <span style="color:var(--brand-accent, #FFD700);font-weight:900;font-size:0.75rem;letter-spacing:1px">KA</span>\n'
            '                </div>\n'
            '                <div style="display:flex;flex-direction:column;align-items:flex-start;line-height:1.2">\n'
            '                    <span style="font-size:0.7rem;font-weight:700;color:var(--text-secondary, #ccc);letter-spacing:0.5px">KA. Agência Criativa.</span>\n'
            '                    <span style="font-size:0.6rem;font-style:italic;color:var(--text-muted, #888);letter-spacing:0.5px">Presença digital sem ruído</span>\n'
            '                </div>\n'
            '            </a>\n'
            '        </div>\n'
            '    </div>\n</footer>\n')

def _scripts():
    return ('<script>\n'
    'var canvas=document.getElementById("bg");var ctx=canvas.getContext("2d");var w,h,dpr=Math.min(window.devicePixelRatio||1,2);var pointer={x:0,y:0,active:false};var ripples=[];\n'
    'function resize(){w=window.innerWidth;h=window.innerHeight;canvas.width=w*dpr;canvas.height=h*dpr;canvas.style.width=w+"px";canvas.style.height=h+"px";ctx.setTransform(dpr,0,0,dpr,0,0)}window.addEventListener("resize",resize);resize();\n'
    'window.addEventListener("pointermove",function(e){pointer.x=e.clientX;pointer.y=e.clientY;pointer.active=true},{passive:true});\n'
    'window.addEventListener("pointerdown",function(e){ripples.push({x:e.clientX,y:e.clientY,r:4,a:0.30})},{passive:true});\n'
    'function frame(){var t=Date.now()*0.001;ctx.globalCompositeOperation="source-over";ctx.fillStyle="#0d0707";ctx.fillRect(0,0,w,h);ctx.globalCompositeOperation="lighter";\n'
    'var cx=w*0.5,cy=h*0.40;\n'
    'for(var i=0;i<3;i++){var ph=t*0.10+i*2.09;var rad=140+Math.sin(t*0.16+i*1.9)*60+i*90;var al=0.045-i*0.011;\n'
    'ctx.strokeStyle="rgba(200,69,69,"+al.toFixed(3)+")";ctx.lineWidth=1;\n'
    'ctx.beginPath();for(var a=0;a<=Math.PI*2+0.1;a+=0.10){var r=rad*(1+0.05*Math.sin(a*2+ph));var x=cx+Math.cos(a)*r;var y=cy+Math.sin(a)*r;if(a===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.closePath();ctx.stroke()}\n'
    'var sg=ctx.createRadialGradient(cx,cy,0,cx,cy,110);sg.addColorStop(0,"rgba(168,48,48,0.045)");sg.addColorStop(1,"rgba(168,48,48,0)");ctx.fillStyle=sg;ctx.beginPath();ctx.arc(cx,cy,110,0,Math.PI*2);ctx.fill();\n'
    'if(pointer.active){var pg=ctx.createRadialGradient(pointer.x,pointer.y,0,pointer.x,pointer.y,90);pg.addColorStop(0,"rgba(255,255,255,0.045)");pg.addColorStop(1,"rgba(255,255,255,0)");ctx.fillStyle=pg;ctx.beginPath();ctx.arc(pointer.x,pointer.y,90,0,Math.PI*2);ctx.fill()}\n'
    'for(var r=ripples.length-1;r>=0;r--){var rp=ripples[r];rp.r+=1.5;rp.a*=0.972;ctx.strokeStyle="rgba(232,160,74,"+rp.a.toFixed(3)+")";ctx.lineWidth=1;ctx.beginPath();ctx.arc(rp.x,rp.y,rp.r,0,Math.PI*2);ctx.stroke();if(rp.a<0.012)ripples.splice(r,1)}\n'
    'requestAnimationFrame(frame)}requestAnimationFrame(frame);\n'
            'const header=document.getElementById("header");const nav=document.getElementById("nav");'
            'const mobileMenuBtn=document.getElementById("mobileMenuBtn");\n'
            'window.addEventListener("scroll",()=>{if(window.scrollY>50)header.classList.add("scrolled");else header.classList.remove("scrolled")},{passive:true});\n'
            'mobileMenuBtn.addEventListener("click",()=>{nav.classList.toggle("active");mobileMenuBtn.textContent=nav.classList.contains("active")?"✕":"☰"});\n'
            'const fadeObserver=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("visible");fadeObserver.unobserve(e.target)}})},{threshold:0.1,rootMargin:"0px 0px -50px 0px"});\n'
            'document.querySelectorAll(".fade-in").forEach(el=>fadeObserver.observe(el));\n'
            '</script>\n')
def _doc(title, desc, body, img_og=None):
    # SEO: Define título, descrição e imagem (fallback para o configurado no painel)
    final_title = SITE_CFG.get('seo_title', title + ' | Por do Som') if title == 'Por do Som | Selo Independente & Produtora Cultural' else (title + ' | Por do Som')
    final_desc = SITE_CFG.get('seo_description', desc) if desc == cfg_str('hero_texto', 'Selo dedicado às Brasilidades')[:155] else desc
    final_img = img_og if img_og else (SITE_CFG.get('seo_og_image') or (DOMINIO + BASE + '/pordosom-profile.jpg'))
    final_url = DOMINIO + BASE + '/site.html'
    keywords = SITE_CFG.get('seo_keywords', '')

    return ('<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            '<title>' + esc(final_title) + '</title>\n'
            '<meta name="description" content="' + esc(final_desc) + '">\n'
            '<meta name="keywords" content="' + esc(keywords) + '">\n'
            '<meta name="robots" content="index, follow">\n'
            '<link rel="canonical" href="' + esc(final_url) + '">\n'
            '<meta property="og:type" content="website">\n'
            '<meta property="og:title" content="' + esc(final_title) + '">\n'
            '<meta property="og:description" content="' + esc(final_desc) + '">\n'
            '<meta property="og:image" content="' + esc(final_img) + '">\n'
            '<meta property="og:url" content="' + esc(final_url) + '">\n'
            '<meta property="og:locale" content="pt_BR">\n'
            '<meta property="og:site_name" content="Por do Som">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<meta name="twitter:title" content="' + esc(final_title) + '">\n'
            '<meta name="twitter:description" content="' + esc(final_desc) + '">\n'
            '<meta name="twitter:image" content="' + esc(final_img) + '">\n'
            '<link rel="icon" type="image/jpeg" href="' + BASE + '/pordosom-profile.jpg">\n'
            '<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">\n'
            '<link rel="stylesheet" href="' + BASE + '/css/style.css">\n'
            '</head>\n<body>\n' + body +
            '\n<script type="application/ld+json">\n{"@context":"https://schema.org","@type":"MusicGroup","name":"Por do Som","genre":["Samba de Raiz","MPB","Brasilidades","Instrumental"],"url":"' + DOMINIO + BASE + '/site.html","description":"Selo independente e produtora cultural dedicado às brasilidades."}</script>\n' +
            '</body>\n</html>\n')

# ---------- Página de álbum ----------
def page_album(a, prev, next_):
    ATUAL_EH_HOME = False
    generos_str = ' · '.join(GENEROS.get(g, g) for g in a['generos'])
    schema = {"@context": "https://schema.org", "@type": "MusicAlbum",
              "name": a['titulo'], "byArtist": {"@type": "MusicGroup", "name": a['artista']},
              "genre": generos_str, "datePublished": str(a.get('ano','')),
              "publisher": {"@type": "Organization", "name": "Por do Som"}}
    embeds = ''
    if a.get('spotify'):
        embeds += '\n        <iframe src="' + esc(sp_embed(a['spotify'])) + '" height="152" loading="lazy" title="Ouvir no Spotify"></iframe>'
    yid = yt_id(a.get('youtube',''))
    if yid:
        embeds += '\n        <iframe src="https://www.youtube.com/embed/' + yid + '" style="aspect-ratio:16/9" loading="lazy" allowfullscreen title="Vídeo"></iframe>'
    plats = ''.join('<a class="plat-link" href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(n) + '</a>'
                    for n, u in [('Spotify', a.get('spotify','')), ('YouTube', a.get('youtube','')),
                                  ('Apple', a.get('apple','')), ('Deezer', a.get('deezer',''))] if u)
    prev_h = ('<a class="album-nav-link" href="' + BASE + '/albuns/' + prev['slug'] + '.html">&#8592; ' + esc(prev['titulo']) + '</a>') if prev else '<span></span>'
    next_h = ('<a class="album-nav-link" href="' + BASE + '/albuns/' + next_['slug'] + '.html">' + esc(next_['titulo']) + ' &#8594;</a>') if next_ else '<span></span>'
    body = ('<header class="header" id="header">\n    <a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav() +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<main class="album-page">\n    <div class="container">\n        <div class="album-hero">\n'
            '            <div class="album-capa-grande">\n'
            '                <img src="' + esc(str(a.get('capa',''))) + '" alt="Capa" loading="lazy" '
            'onerror="this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 600 600%22%3E%3Crect fill=%22%231a0e0e%22 width=%22600%22 height=%22600%22/%3E%3C/svg%3E\'">\n'
            '            </div>\n            <div>\n'
            '                <span class="album-kicker">Álbum · ' + esc(a.get('ano','')) + ' · ' + esc(generos_str) + '</span>\n'
            '                <h1 class="album-titulo-grande">' + esc(a['titulo']) + '</h1>\n'
            '                <div class="album-artista-grande">' + esc(a['artista']) + '</div>\n'
            '                <p class="album-descricao">' + esc(a.get('corpo','')) + '</p>\n'
            + ('<p class="album-descricao-en">' + esc(a.get('texto_en','')) + '</p>' if a.get('texto_en') else '') +
            '                <div class="album-embeds">' + embeds + '\n                </div>\n'
            '                <div class="album-plataformas">' + plats + '</div>\n'
            '            </div>\n        </div>\n'
            '        <div class="album-navegacao">\n            ' + prev_h + '\n'
            '            <a class="album-nav-link" href="' + BASE + '/site.html#gravadora">Voltar ao catálogo</a>\n'
            '            ' + next_h + '\n        </div>\n    </div>\n</main>\n\n' + _footer() + _scripts())
    d = _doc(a['titulo'] + ' — ' + a['artista'], (a.get('corpo') or a['titulo'])[:155], body, img_og=str(a.get('capa','')))
    return d.replace('</head>', '<script type="application/ld+json">\n' + json.dumps(schema, ensure_ascii=False) + '\n</script>\n</head>')

# ---------- site.html (o site inteiro, seções por âncoras) ----------
def _sec(id_, subtitulo, titulo_cfg, desc_cfg=None, conteudo='', alt=False):
    titulo = cfg_str(titulo_cfg)
    partes = titulo.rsplit(' ', 1)
    titulo_html = (esc(partes[0]) + ' <span class="gradient">' + esc(partes[1]) + '</span>') if len(partes) == 2 else esc(titulo)
    desc = ''
    if desc_cfg and cfg_str(desc_cfg):
        desc = '\n            <p class="section-description">' + esc(cfg_str(desc_cfg)) + '</p>'
    cls = 'teaser teaser-alt' if alt else 'teaser'
    return ('<section class="' + cls + '" id="' + id_ + '">\n    <div class="container">\n'
            '        <div class="teaser-head">\n'
            '            <span class="section-subtitle">' + esc(subtitulo) + '</span>\n'
            '            <h2 class="section-title">' + titulo_html + '</h2>' + desc + '\n'
            '        </div>\n' + conteudo + '\n    </div>\n</section>\n')

def gera_site():
    ATUAL_EH_HOME = True

    # --- HERO ---
    slog = cfg_str('hero_slogan', 'Onde a música nasce')
    sp = slog.rsplit(' ', 1)
    slog_html = esc(sp[0]) + (' <span class="gradient">' + esc(sp[1]) + '</span>' if len(sp) > 1 else '')
    hero = ('<section class="hero">\n    <div class="hero-bg"></div>\n    <div class="hero-bg-overlay"></div>\n'
            '    <div class="hero-noise"></div>\n    <div class="hero-content">\n'
'        <p class="hero-subtitle">Selo Pôr do Som</p>\n'
            '        <h1 class="hero-title">' + slog_html + '</h1>\n'
            '        <p class="hero-description">' + esc(cfg_str('hero_texto')) + '</p>\n'
            '    </div>\n    <div class="hero-scroll">\n        <span>Role para descobrir</span>\n'
            '        <div class="hero-scroll-line"></div>\n    </div>\n</section>\n')

    # --- NOTICIAS (banner da ultima) ---
    banner_js = ('<div class="container"><div id="banner-noticia"></div></div>')
    sec_noticias = ('<section class="teaser" id="noticias" style="padding-top:2rem;padding-bottom:2rem">\n'
                    + banner_js + '\n</section>\n')

    # --- GRAVADORA (catalogo + filtros + artistas) ---
    vitrine_js = '<div class="vitrine-grid" id="vitrine"></div>\n        <div style="text-align:center"><a href="#gravadora" class="teaser-link" style="display:none"></a></div>'
    vitrine_js = '<div class="vitrine-grid" id="vitrine"></div>\n        <div style="text-align:center;margin-top:2.5rem"><a href="' + BASE + '/catalogo.html" class="btn btn-outline" style="text-decoration:none">Ver catálogo completo (' + str(len(albuns)) + ' obras) →</a></div>'
    sec_grav = ('<section class="teaser" id="gravadora">\n    <div class="container">\n'
                '        <div class="teaser-head">\n'
                '            <span class="section-subtitle">Gravadora</span>\n'
                '            <h2 class="section-title">' + esc(cfg_str('grav_titulo')) + '</h2>\n'
                '            <p class="section-description">' + esc(cfg_str('grav_descricao')) + '</p>\n'
                '        </div>\n        ' + vitrine_js + '\n    </div>\n</section>\n')


    # --- PROJETOS ---
    cards_p = []
    for p in projetos[:1]:  # Limitado a 1 na home
        img = p.get('imagem') or ''
        if isinstance(img, list): img = img[0] if img else ''
        st_cls = 'status-realizado' if str(p.get('status')) != 'captacao' else 'status-captacao'
        st_lbl = '✓ Realizado' if str(p.get('status')) != 'captacao' else '★ Em captação'
        link = p.get('link') or '#'
        cards_p.append(
            '<div class="projeto-card"><div class="galeria">'
            '<img src="' + BASE + (img or '/pordosom-profile.jpg') + '" alt="' + esc(p['titulo']) + '" loading="lazy" onerror="this.style.display=\'none\'"></div>'
            '<div class="projeto-corpo"><span class="projeto-badge ' + st_cls + '">' + st_lbl + '</span>'
            '<h3>' + esc(p['titulo']) + '</h3>'
            '<p style="font-size:.9rem;line-height:1.8;color:var(--text-secondary)">' + esc(p.get('corpo','')) + '</p>'
            '<a href="' + esc(link) + '" target="_blank" rel="noopener" class="teaser-link" style="margin-top:14px">Ver projeto →</a>'
            '</div></div>')
    sec_proj = _sec('projetos', 'Projetos & Festivais', 'projetos_titulo', 'projetos_descricao',
                    '\n'.join(cards_p) + ('\n        <div style="text-align:center;margin-top:2.5rem"><a href="' + BASE + '/projetos.html" class="btn btn-outline" style="text-decoration:none">Ver todos os projetos (' + str(len(projetos)) + ') →</a></div>' if len(projetos) > 1 else ''), alt=True)

    # --- AUDIOVISUAL (clips por grupo) ---
    _clips_home = clips[:4]
    vids_home = '\n'.join('            <iframe src="https://www.youtube.com/embed/' + str(c.get('yt_id','')) +
                         '" loading="lazy" allowfullscreen title="' + esc(c.get('titulo','')) + '"></iframe>' for c in _clips_home)
    btn_av = ('\n        <div style="text-align:center;margin-top:2.5rem"><a href="' + BASE + '/audiovisual.html" '
              'class="btn btn-outline" style="text-decoration:none">Ver todos os vídeos (' + str(len(clips)) + ') →</a></div>')
    sec_av = _sec('audiovisual', 'Audiovisual', 'audio_titulo', 'audio_descricao',
                  '<div class="teaser-videos">\n' + vids_home + '\n        </div>' + btn_av)

    # --- PLAYLISTS ---
    p1id = cfg_str('playlist1_id', '2lgoPMSE9e7lxEumGbBaGn')
    p2id = cfg_str('playlist2_id', '2cyXUj8Qhe3nZ0rbng87nR')
    playlists_html = ('<div class="teaser-playlists">\n'
                     '            <iframe src="https://open.spotify.com/embed/playlist/' + p1id + '" height="380" loading="lazy" title="Playlist 1"></iframe>\n'
                     '            <iframe src="https://open.spotify.com/embed/playlist/' + p2id + '" height="380" loading="lazy" title="Playlist 2"></iframe>\n'
                     '        </div>')
    sec_pl = _sec('playlists', 'Playlists', 'home_playlists_titulo', None, playlists_html, alt=True)

    # --- MANIFESTO ---
    manifesto_ps = '\n            '.join('<p class="manifesto-text">' + esc(cfg_str('manifesto_texto' + str(i))) + '</p>' for i in (1,2,3) if cfg_str('manifesto_texto' + str(i)))
    stats = [('31','Obras no catálogo'),('10+','Artistas'),('3','Festivais próprios'),('42','Vídeos produzidos')]
    stats_html = '\n'.join('<div class="stat-item fade-in"><div class="stat-num">' + n + '</div><div class="stat-label">' + l + '</div></div>' for n,l in stats)
    sec_manif = ('<section class="teaser" id="manifesto">\n    <div class="container">\n'
                 '        <div class="manifesto-content">\n'
                 '            <span class="section-subtitle">Manifesto</span>\n'
                 '            <h2 class="section-title">Som que <span class="gradient">pulsa Brasil</span></h2>\n'
                 '            ' + manifesto_ps + '\n'
                 '            <p class="manifesto-signature">— Por do Som Cultural</p>\n'
                 '            <div class="manifesto-stats" style="margin-top:3rem">\n' + stats_html + '\n            </div>\n'
                 '        </div>\n    </div>\n</section>\n')

    # --- QUEM SOMOS ---
    portfolio = cfg_str('portfolio_link')
    port_html = ('<div style="margin-top:3rem" class="fade-in"><a href="' + esc(portfolio) + '" target="_blank" rel="noopener" '
                  'class="btn btn-outline" style="text-decoration:none">Currículo completo &amp; Portfolio ↗</a></div>') if portfolio else ''
    sec_qs = ('<section class="teaser teaser-alt" id="quemsomos">\n    <div class="container">\n'
              '        <div class="manifesto-content">\n'
              '            <span class="section-subtitle">Quem Somos</span>\n'
              '            <h2 class="section-title">Mais de 20 anos <span class="gradient">cantando o Brasil</span></h2>\n'
              '            <p class="manifesto-text">' + esc(cfg_str('quemsomos_texto')) + '</p>\n'
              + port_html + '\n        </div>\n    </div>\n</section>\n')

    # --- EDITORA ---
    sec_ed = ('<section class="teaser" id="editora">\n    <div class="container">\n'
              '        <div class="manifesto-content">\n'
              '            <span class="section-subtitle">Editora &amp; Direitos</span>\n'
              '            <h2 class="section-title">Administração de <span class="gradient">obras musicais</span></h2>\n'
              '            <p class="manifesto-text">' + esc(cfg_str('editora_texto')) + '</p>\n'
              '            <p class="manifesto-signature">Consultoria: <a href="#contato" style="color:var(--brand-primary-light);text-decoration:none;text-transform:none;letter-spacing:normal">fale com o selo</a></p>\n'
              '        </div>\n    </div>\n</section>\n')

    # --- CONTATO ---
    email = cfg_str('email_contato', 'contato@pordosom.com.br')
    wa = cfg_str('whatsapp_contato')
    wa_html = ('<a href="https://wa.me/' + esc(wa) + '" class="social-card" style="text-decoration:none">'
               '<div class="social-card-icon">📱</div>'
               '<div class="social-card-text"><div class="social-card-label">WhatsApp</div>'
               '<div class="social-card-handle">' + esc(wa) + '</div></div></a>') if wa else ''
    sec_cont = ('<section class="teaser teaser-alt" id="contato">\n    <div class="container">\n'
                '        <div class="teaser-head">\n'
                '            <span class="section-subtitle">Contato</span>\n'
                '            <h2 class="section-title">' + esc(cfg_str('contato_titulo', 'Vamos fazer música juntos?')) + '</h2>\n'
                '            <p class="section-description">' + esc(cfg_str('contato_descricao')) + '</p>\n'
                '            <div class="teaser-contato" style="margin-top:1.5rem">\n'
                '                <a href="mailto:' + esc(email) + '" class="social-card" style="text-decoration:none">\n'
                '                    <div class="social-card-icon">✉</div>\n'
                '                    <div class="social-card-text"><div class="social-card-label">E-mail</div>\n'
                '                    <div class="social-card-handle">' + esc(email) + '</div></div></a>\n'
                '                <a href="https://www.instagram.com/pordosomcultural" target="_blank" rel="noopener" class="social-card" style="text-decoration:none">\n'
                '                    <div class="social-card-icon">📷</div>\n'
                '                    <div class="social-card-text"><div class="social-card-label">Instagram</div>\n'
                '                    <div class="social-card-handle">@pordosomcultural</div></div></a>\n'
                + wa_html + '\n            </div>\n        </div>\n    </div>\n</section>\n')

    # --- O JS da vitrine/filtros/banner EMBUTIDO ---
    js_site = ('<script>\n(async function(){\n'
               '  const BASE = "' + BASE + '";\n'
               '  let CAT;\n'
               '  try { const r = await fetch(BASE + "/data/catalogo.json?v=" + Date.now()); CAT = await r.json(); } catch(e){ return; }\n'
               '  if (CAT.albuns) CAT.albuns.forEach(a => {\n'
               '    if (Array.isArray(a.capa)) a.capa = a.capa[0] || "";\n'
               '    if (typeof a.capa !== "string") a.capa = String(a.capa || "");\n'
               '    if (typeof a.generos === "string") a.generos = a.generos.replace(/[\\[\\]]/g,"").split(",").map(s=>s.trim()).filter(Boolean);\n'
               '    if (!Array.isArray(a.generos)) a.generos = [];\n'
               '  });\n'
               '  if (!CAT.albuns) CAT.albuns = []; if (!CAT.generos) CAT.generos = [];\n'
               '  const capaSrc = c => (c && c.startsWith("/")) ? BASE + c : (c || "");\n'
               '  const fallback = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 300 300%22%3E%3Crect fill=%22%231a0e0e%22 width=%22300%22 height=%22300%22/%3E%3Ccircle cx=%22150%22 cy=%22130%22 r=%2255%22 fill=%22%23a83030%22 opacity=%220.7%22/%3E%3C/svg%3E";\n'
               '  CAT.albuns.sort((x,y)=>{const ox=parseInt(x.ordem)||0,oy=parseInt(y.ordem)||0;'
               'if(ox&&oy)return ox-oy;if(ox)return -1;if(oy)return 1;'
               'return String(y.ano||"").localeCompare(String(x.ano||""))});\n'
               '  const vitrine = document.getElementById("vitrine");\n'
               '  if (vitrine) { vitrine.innerHTML = CAT.albuns.filter(a=>a.destaque).slice(0,6).map(a =>\n'
               '    `<a href="${BASE}/albuns/${a.slug}.html"><img src="${capaSrc(a.capa)}" alt="Capa: ${a.title||a.titulo||""}" loading="lazy" onerror="this.src=\'${fallback}\'"><span class="vitrine-titulo">${a.titulo||""}</span></a>`).join(""); }\n'
               '  const filtrosEl = document.getElementById("filtros");\n'
               '  const grid = document.getElementById("catalogo-grid");\n'
               '  if (filtrosEl && grid) {\n'
               '    const contagem = { todos: CAT.albuns.length };\n'
               '    CAT.generos.forEach(g => { contagem[g.id] = CAT.albuns.filter(a=>a.generos.includes(g.id)).length });\n'
               '    filtrosEl.innerHTML = `<button class="filtro ativo" data-g="todos">Todos <span class="count">${contagem.todos}</span></button>` +\n'
               '      CAT.generos.filter(g=>contagem[g.id]>0).map(g=>`<button class="filtro" data-g="${g.id}">${g.nome} <span class="count">${contagem[g.id]}</span></button>`).join("");\n'
               '    const nomeG = id => (CAT.generos.find(g=>g.id===id)||{}).nome || id;\n'
               '    function renderGrid(g){\n'
               '      const lista = g==="todos" ? CAT.albuns : CAT.albuns.filter(a=>a.generos.includes(g));\n'
               '      grid.innerHTML = lista.map(a => `<a class="album-card" href="${BASE}/albuns/${a.slug}.html">\n'
               '        <div class="album-capa"><img src="${capaSrc(a.capa)}" alt="" loading="lazy" onerror="this.src=\'${fallback}\'"></div>\n'
               '        <div class="album-info"><div class="album-titulo">${a.titulo}</div>\n'
               '        <div class="album-artista">${a.artista}${a.ano?" · "+a.ano:""}</div>\n'
               '        <div class="album-tags">${a.generos.map(g=>`<span class="album-tag">${nomeG(g)}</span>`).join("")}</div></div></a>`).join("") || \'<p style="grid-column:1/-1;text-align:center;color:var(--text-muted)">Nenhum álbum neste gênero.</p>\';\n'
               '    }\n'
               '    filtrosEl.addEventListener("click", e => { const b = e.target.closest(".filtro"); if (b) {\n'
               '      filtrosEl.querySelectorAll(".filtro").forEach(x=>x.classList.toggle("ativo", x===b)); renderGrid(b.dataset.g); } });\n'
               '    renderGrid("todos");\n'
               '  }\n'
               '  const artGrid = document.getElementById("artistas-grid");\n'
               '  if (artGrid && Array.isArray(CAT.artistas)) { artGrid.innerHTML = CAT.artistas.map(a =>\n'
               '    `<div class="artist-card fade-in"><div class="artist-card-img" style="background-image:url(\'${a.img||""}\')"></div>\n'
               '    <div class="artist-card-overlay"></div><div class="artist-card-content">\n'
               '    <div class="artist-initial">${(a.nome||"?").trim()[0].toUpperCase()}</div>\n'
               '    <div class="artist-name">${a.nome||""}</div><div class="artist-role">${a.role||""}</div></div></div>`).join(""); }\n'
               '  const bannerEl = document.getElementById("banner-noticia");\n'
               '  if (bannerEl && Array.isArray(CAT.posts) && CAT.posts.length) {\n'
               '    const p = CAT.posts[0]; const partes = String(p.date||"").split("-");\n'
               '    const data = partes.length===3 ? partes.reverse().join("/") : "";\n'
               '    const imgSrc = p.imagem ? (p.imagem.startsWith("/") ? BASE + p.imagem : p.imagem) : "";\n'
               '    bannerEl.innerHTML = `<a href="${BASE}/posts/${p.slug}.html" style="display:flex;gap:1.5rem;max-width:860px;margin:0 auto;padding:1.5rem;background:linear-gradient(135deg,var(--bg-card),var(--bg-darker));border:1px solid var(--border-color);border-left:4px solid var(--brand-primary);border-radius:8px;text-decoration:none;align-items:center;box-shadow:0 12px 40px rgba(0,0,0,.35);transition:transform .3s"\n'
               '      onmouseover="this.style.transform=\'translateY(-3px)\'" onmouseout="this.style.transform=\'\'">\n'
               '      ${imgSrc ? `<img src="${imgSrc}" alt="${p.title}" style="width:120px;height:120px;object-fit:cover;border-radius:6px;flex-shrink:0" loading="lazy">` : \'<div style="width:120px;height:120px;background:var(--bg-darker);border-radius:6px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:2rem">📰</div>\'}\n'
               '      <div style="flex:1;min-width:0">\n'
               '      <div style="font-size:.65rem;letter-spacing:2px;text-transform:uppercase;color:var(--brand-accent);margin-bottom:.5rem">📰 Última notícia · ${data}</div>\n'
               '      <h3 style="font-size:clamp(1.1rem,3vw,1.5rem);font-weight:800;text-transform:uppercase;color:var(--text-primary);line-height:1.3;margin-bottom:.6rem">${p.title||"Sem título"}</h3>\n'
               '      <p style="font-size:.9rem;color:var(--text-secondary);line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">${p.resumo||""}</p>\n'
               '      <span style="display:inline-block;margin-top:1rem;font-size:.7rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--brand-primary-light)">Ler a notícia completa →</span>\n'
               '      </div></a>`;\n'
               '  }\n'
               '})();\n</script>\n')

    body = ('<header class="header" id="header">\n    <a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav() +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n\n'
            + hero + sec_noticias + sec_grav + sec_proj + sec_ed + sec_av + sec_pl
            + sec_manif + sec_qs + sec_cont + '\n' + _footer() + _scripts() + js_site)

    _conteudo = _doc('Por do Som | Selo Independente & Produtora Cultural',
                     cfg_str('hero_texto', 'Selo dedicado às Brasilidades')[:155], body)
    for _alvo in ('site.html', 'index.html'):
        with open(os.path.join(BASE_DIR, _alvo), 'w', encoding='utf-8') as f:
            f.write(_conteudo)
    print('✔ site.html + index.html gerados (seções: hero, notícias, gravadora, artistas, projetos, audiovisual, playlists, manifesto, quem-somos, editora, contato)')

# ---------- Páginas de notícia ----------
def gera_posts():
    ATUAL_EH_HOME = False
    os.makedirs(os.path.join(BASE_DIR, 'posts'), exist_ok=True)
    n = 0
    for p in posts:
        partes = str(p.get('date','')).split('-')
        data = '/'.join(reversed(partes)) if len(partes) == 3 else ''
        img = ''
        if p.get('imagem'):
            im = p['imagem']
            if isinstance(im, list): im = im[0] if im else ''
            img = '<img src="' + BASE + im + '" alt="" style="width:100%;max-width:760px;border-radius:4px;margin:0 auto 2rem;display:block" loading="lazy">'
        body = ('<header class="header" id="header">\n    <a href="' + BASE + '/site.html" class="logo">\n'
                '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
                '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav() +
                '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
                '<main class="album-page">\n    <div class="container">\n'
                '        <div style="max-width:760px;margin:0 auto">\n'
                '            <span class="album-kicker">Notícia · ' + data + '</span>\n'
                '            <h1 class="album-titulo-grande" style="font-size:clamp(1.6rem,4vw,2.4rem)">' + esc(p.get('title','')) + '</h1>\n'
                '            <div class="album-meta-info">' + esc(p.get('resumo','')) + '</div>\n'
                '        </div>\n' + img + '\n'
                '        <div style="max-width:680px;margin:0 auto;font-size:.98rem;line-height:2;color:var(--text-secondary)">\n'
                + md_html(p.get('corpo','')) + '\n        </div>\n'
                '        <div class="album-navegacao">\n            <span></span>\n'
                '            <a class="album-nav-link" href="' + BASE + '/site.html#noticias">Todas as notícias</a>\n            <span></span>\n'
                '        </div>\n    </div>\n</main>\n\n' + _footer() + _scripts())
        with open(os.path.join(BASE_DIR, 'posts', slugify(p.get('title','post')) + '.html'), 'w', encoding='utf-8') as f:
            f.write(_doc(p.get('title',''), str(p.get('resumo',''))[:155], body, img_og=img))
        n += 1
    print('✔ ' + str(n) + ' páginas de notícia geradas')

# ---------- catalogo.json ----------
def gera_json():
    def _n(a):
        capa = a.get('capa','')
        if isinstance(capa, list): capa = capa[0] if capa else ''
        g = a.get('generos', [])
        if isinstance(g, str): g = [x.strip() for x in g.replace('[','').replace(']','').split(',') if x.strip()]
        ano = a.get('ano','')
        if isinstance(ano, list): ano = ano[0] if ano else ''
        ordem = a.get('ordem','')
        if isinstance(ordem, list): ordem = ordem[0] if ordem else ''
        return {'slug': a['slug'], 'titulo': str(a.get('titulo','')), 'artista': str(a.get('artista','')),
                'ano': str(ano), 'capa': str(capa or ''), 'generos': g,
                'destaque': bool(a.get('destaque')), 'ordem': str(ordem),
                'spotify': str(a.get('spotify','') or ''), 'youtube': str(a.get('youtube','') or '')}
    artistas_js = [{'nome': str(a.get('nome','')), 'role': str(a.get('role','')),
                   'img': str(a.get('img','') or '')} for a in artistas]
    posts_js = [{'title': str(p.get('title','')), 'resumo': str(p.get('resumo','')),
                 'date': str(p.get('date','')), 'imagem': str(p.get('imagem','') or ''),
                 'slug': slugify(p.get('title','post'))} for p in posts[:3]]
    cat = {'base': BASE,
           'generos': [{'id': k, 'nome': v} for k, v in GENEROS.items()],
           'albuns': [_n(a) for a in albuns],
           'posts': posts_js,
           'artistas': artistas_js}
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
    with open(os.path.join(BASE_DIR, 'data', 'catalogo.json'), 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print('OK catalogo.json (' + str(len(albuns)) + ' albuns, ' + str(len(posts_js)) + ' posts, ' + str(len(artistas_js)) + ' artistas)')
def gera_albuns():
    ATUAL_EH_HOME = False
    os.makedirs(os.path.join(BASE_DIR, 'albuns'), exist_ok=True)
    for i, a in enumerate(albuns):
        prev = albuns[i-1] if i > 0 else None
        nxt = albuns[i+1] if i < len(albuns)-1 else None
        with open(os.path.join(BASE_DIR, 'albuns', a['slug'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(page_album(a, prev, nxt))
    print('✔ ' + str(len(albuns)) + ' páginas de álbum geradas')

# ---------- sitemap ----------

# ---------- Página de projetos completos ----------
def gera_projetos():
    ATUAL_EH_HOME = False
    cards = []
    for p in projetos:
        img = p.get('imagem') or ''
        if isinstance(img, list): img = img[0] if img else ''
        st_cls = 'status-realizado' if str(p.get('status')) != 'captacao' else 'status-captacao'
        st_lbl = '✓ Realizado' if str(p.get('status')) != 'captacao' else '★ Em captação'
        link = p.get('link') or '#'
        cards.append(
            '<div class="projeto-card"><div class="galeria">'
            '<img src="' + BASE + (img or '/pordosom-profile.jpg') + '" alt="' + esc(p['titulo']) + '" loading="lazy" onerror="this.style.display=\'none\'"></div>'
            '<div class="projeto-corpo"><span class="projeto-badge ' + st_cls + '">' + st_lbl + '</span>'
            '<h3>' + esc(p['titulo']) + '</h3>'
            '<p style="font-size:.9rem;line-height:1.8;color:var(--text-secondary)">' + esc(p.get('corpo','')) + '</p>'
            '<a href="' + esc(link) + '" target="_blank" rel="noopener" class="teaser-link" style="margin-top:14px">Ver projeto →</a>'
            '</div></div>')
    
    body = ('<header class="header" id="header">\n    <a href="' + BASE + '/index.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav('Projetos') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n    <div class="container">\n'
            '        <span class="section-subtitle">Projetos & Festivais</span>\n'
            '        <h1 class="section-title">' + esc(cfg_str('projetos_titulo')) + '</h1>\n'
            '        <p class="section-description">' + esc(cfg_str('projetos_descricao')) + '</p>\n'
            '    </div>\n</header>\n'
            '<section style="padding:3rem 0">\n    <div class="container">\n'
            + '\n'.join(cards) + '\n    </div>\n</section>\n\n' + _footer() + _scripts())
    
    with open(os.path.join(BASE_DIR, 'projetos.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Projetos & Festivais', cfg_str('projetos_descricao')[:155], body))
    print('✔ projetos.html gerada (' + str(len(projetos)) + ' projetos)')

def gera_robots():
    txt = "User-agent: *\nAllow: /\nSitemap: " + DOMINIO + BASE + "/sitemap.xml\n"
    with open(os.path.join(BASE_DIR, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print('✔ robots.txt gerado')


def gera_sitemap():
    urls = [DOMINIO + '/site.html'] + [DOMINIO + '/albuns/' + a['slug'] + '.html' for a in albuns] + \
           [DOMINIO + '/posts/' + slugify(p.get('title','')) + '.html' for p in posts]
    hoje = datetime.now().strftime('%Y-%m-%d')
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += '  <url><loc>' + u + '</loc><lastmod>' + hoje + '</lastmod></url>\n'
    sm += '</urlset>\n'
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sm)
    print('✔ sitemap.xml (' + str(len(urls)) + ' URLs)')



# ---------- JS para paginas de dados (catalogo, etc.) ----------
def _js_dados():
    """JS reutilizavel: filtros do catalogo + grade de artistas."""
    return ('<script>\n'
    '(async function(){\n'
    '  const BASE = "' + BASE + '";\n'
    '  let CAT;\n'
    '  try { const r = await fetch(BASE + "/data/catalogo.json?v=" + Date.now()); CAT = await r.json(); } catch(e){ return; }\n'
    '  if (CAT.albuns) CAT.albuns.forEach(a => {\n'
    '    if (Array.isArray(a.capa)) a.capa = a.capa[0] || "";\n'
    '    if (typeof a.capa !== "string") a.capa = String(a.capa || "");\n'
    '    if (typeof a.generos === "string") a.generos = a.generos.replace(/[\\[\\]]/g,"").split(",").map(s=>s.trim()).filter(Boolean);\n'
    '    if (!Array.isArray(a.generos)) a.generos = [];\n'
    '  });\n'
    '  if (!CAT.albuns) CAT.albuns = []; if (!CAT.generos) CAT.generos = [];\n'
    '  const capaSrc = c => (c && c.startsWith("/")) ? BASE + c : (c || "");\n'
    '  const fallback = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 300 300%22%3E%3Crect fill=%22%231a0e0e%22 width=%22300%22 height=%22300%22/%3E%3Ccircle cx=%22150%22 cy=%22130%22 r=%2255%22 fill=%22%23a83030%22 opacity=%220.7%22/%3E%3C/svg%3E";\n'
    '  CAT.albuns.sort((x,y)=>{const ox=parseInt(x.ordem)||0,oy=parseInt(y.ordem)||0;'
    'if(ox&&oy)return ox-oy;if(ox)return -1;if(oy)return 1;'
    'return String(y.ano||"").localeCompare(String(x.ano||""))});\n'
    '  const filtrosEl = document.getElementById("filtros");\n'
    '  const grid = document.getElementById("catalogo-grid");\n'
    '  if (filtrosEl && grid) {\n'
    '    const contagem = { todos: CAT.albuns.length };\n'
    '    CAT.generos.forEach(g => { contagem[g.id] = CAT.albuns.filter(a=>a.generos.includes(g.id)).length });\n'
    '    filtrosEl.innerHTML = `<button class="filtro ativo" data-g="todos">Todos <span class="count">${contagem.todos}</span></button>` +\n'
    '      CAT.generos.filter(g=>contagem[g.id]>0).map(g=>`<button class="filtro" data-g="${g.id}">${g.nome} <span class="count">${contagem[g.id]}</span></button>`).join("");\n'
    '    const nomeG = id => (CAT.generos.find(g=>g.id===id)||{}).nome || id;\n'
    '    function renderGrid(g){\n'
    '      const lista = g==="todos" ? CAT.albuns : CAT.albuns.filter(a=>a.generos.includes(g));\n'
    '      grid.innerHTML = lista.map(a => `<a class="album-card" href="${BASE}/albuns/${a.slug}.html">\n'
    '        <div class="album-capa"><img src="${capaSrc(a.capa)}" alt="" loading="lazy" onerror="this.src=\'${fallback}\'"></div>\n'
    '        <div class="album-info"><div class="album-titulo">${a.titulo}</div>\n'
    '        <div class="album-artista">${a.artista}${a.ano?" · "+a.ano:""}</div>\n'
    '        <div class="album-tags">${a.generos.map(g=>`<span class="album-tag">${nomeG(g)}</span>`).join("")}</div></div></a>`).join("") || \'<p style="grid-column:1/-1;text-align:center;color:var(--text-muted)">Nenhum álbum neste gênero.</p>\';\n'
    '    }\n'
    '    filtrosEl.addEventListener("click", e => { const b = e.target.closest(".filtro"); if (b) {\n'
    '      filtrosEl.querySelectorAll(".filtro").forEach(x=>x.classList.toggle("ativo", x===b)); renderGrid(b.dataset.g); } });\n'
    '    renderGrid("todos");\n'
    '  }\n'
    '  const artGrid = document.getElementById("artistas-grid");\n'
    '  if (artGrid && Array.isArray(CAT.artistas)) { artGrid.innerHTML = CAT.artistas.map(a =>\n'
    '    `<div class="artist-card fade-in"><div class="artist-card-img" style="background-image:url(\'${a.img||""}\')"></div>\n'
    '    <div class="artist-card-overlay"></div><div class="artist-card-content">\n'
    '    <div class="artist-initial">${(a.nome||"?").trim()[0].toUpperCase()}</div>\n'
    '    <div class="artist-name">${a.nome||""}</div><div class="artist-role">${a.role||""}</div></div></div>`).join(""); }\n'
    '})();\n'
    '</script>\n')


# ---------- Página do catálogo completo (aprofundamento) ----------
def gera_catalogo():
    ATUAL_EH_HOME = False
    filtros_js = ('<div class="filtros" id="filtros"></div>\n        <div class="catalogo-grid" id="catalogo-grid"></div>')
    body = ('<header class="header" id="header">\n    <a href="' + BASE + '/index.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav('Gravadora') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n    <div class="container">\n'
            '        <span class="section-subtitle">Gravadora</span>\n'
            '        <h1 class="section-title">' + esc(cfg_str('grav_titulo')) + '</h1>\n'
            '        <p class="section-description">' + esc(cfg_str('grav_descricao')) + '</p>\n'
            '    </div>\n</header>\n'
            '<section style="padding-top:2rem">\n    <div class="container">\n        ' + filtros_js + '\n'
            '    </div>\n</section>\n'
            '<section class="teaser teaser-alt" style="padding-top:2rem">\n    <div class="container">\n'
            '        <div class="teaser-head">\n'
            '            <span class="section-subtitle">Gravadora</span>\n'
            '            <h2 class="section-title">' + esc(cfg_str('artistas_titulo')) + '</h2>\n'
            '            <p class="section-description">' + esc(cfg_str('artistas_descricao')) + '</p>\n'
            '        </div>\n        <div class="artistas-grid" id="artistas-grid"></div>\n'
            '    </div>\n</section>\n\n' + _footer() + _scripts() + _js_dados())
    with open(os.path.join(BASE_DIR, 'catalogo.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Gravadora — Catálogo & Artistas', cfg_str('grav_descricao')[:155], body))
    print('✔ catalogo.html gerada (catálogo completo + artistas)')

# ---------- Página audiovisual completa (aprofundamento) ----------
def gera_audiovisual():
    ATUAL_EH_HOME = False
    grupos_html = []
    for gid, gname in GRUPOS_AV.items():
        do_g = [c for c in clips if str(c.get('grupo')) == gid]
        if not do_g: continue
        vids = '\n'.join('            <iframe src="https://www.youtube.com/embed/' + str(c.get('yt_id','')) +
                         '" loading="lazy" allowfullscreen title="' + esc(c.get('titulo','')) + '"></iframe>' for c in do_g)
        grupos_html.append('<h2 class="section-title" style="font-size:1.3rem;margin-top:3rem">' + esc(gname) + '</h2>\n'
                          '<div class="teaser-videos">\n' + vids + '\n        </div>')
    p1id = cfg_str('playlist1_id', '2lgoPMSE9e7lxEumGbBaGn')
    p2id = cfg_str('playlist2_id', '2cyXUj8Qhe3nZ0rbng87nR')
    playlists = ('<section class="teaser teaser-alt">\n    <div class="container">\n'
                 '        <div class="teaser-head">\n'
                 '            <span class="section-subtitle">Playlists</span>\n'
                 '            <h2 class="section-title">' + esc(cfg_str('playlists_titulo', 'Curadoria do selo')) + '</h2>\n'
                 '        </div>\n        <div class="teaser-playlists">\n'
                 '            <iframe src="https://open.spotify.com/embed/playlist/' + p1id + '" height="380" loading="lazy" title="Playlist 1"></iframe>\n'
                 '            <iframe src="https://open.spotify.com/embed/playlist/' + p2id + '" height="380" loading="lazy" title="Playlist 2"></iframe>\n'
                 '        </div>\n    </div>\n</section>\n')
    body = ('<header class="header" id="header">\n    <a href="' + BASE + '/index.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n    </a>\n' + _nav('Audiovisual') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n    <div class="container">\n'
            '        <span class="section-subtitle">Audiovisual</span>\n'
            '        <h1 class="section-title">' + esc(cfg_str('audio_titulo')) + '</h1>\n'
            '        <p class="section-description">' + esc(cfg_str('audio_descricao')) + '</p>\n'
            '    </div>\n</header>\n'
            '<section style="padding-top:2rem">\n    <div class="container">\n'
            + '\n'.join(grupos_html) + '\n    </div>\n</section>\n\n' + playlists + '\n' + _footer() + _scripts())
    with open(os.path.join(BASE_DIR, 'audiovisual.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Audiovisual & Playlists', cfg_str('audio_descricao')[:155], body))
    print('✔ audiovisual.html gerada (' + str(len(clips)) + ' vídeos em ' + str(len(grupos_html)) + ' grupos)')

# ---------- MAIN ----------
if __name__ == '__main__':
    gera_site()
    gera_catalogo()
    gera_audiovisual()
    gera_projetos()
    gera_albuns()
    gera_posts()
    gera_json()
    gera_robots()
    gera_sitemap()
    print('\n🎉 RENDER v5 COMPLETO — uma fonte (content/), um autor (render.py)')
