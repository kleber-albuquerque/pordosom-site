#!/usr/bin/env python3
# ==========================================================
# POR DO SOM — render.py v6 (matérias ricas + páginas de projeto)
# A ÚNICA fonte: content/*.md → gera TUDO:
#   site.html / index.html (site inteiro, seções por âncoras)
#   catalogo.html / audiovisual.html
#   albuns/*.html / posts/*.html / projetos/*.html (NOVO v6)
#   data/catalogo.json + sitemap.xml + robots.txt
# v6: md_html_v2 (figuras, embeds YT/Spotify, citações, H3),
#     páginas individuais de projeto, hero_scroll_texto
#     configurável, tempo de leitura nas notícias.
# ==========================================================
import os, re, json, html
from datetime import datetime
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA = {
    'albuns': os.path.join(BASE_DIR, 'content', 'albuns'),
    'posts': os.path.join(BASE_DIR, 'content', 'posts'),
    'projetos': os.path.join(BASE_DIR, 'content', 'projetos'),
    'audiovisual': os.path.join(BASE_DIR, 'content', 'audiovisual'),
    'config': os.path.join(BASE_DIR, 'content', 'config'),
    'playlists': os.path.join(BASE_DIR, 'content', 'playlists'),
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

# Paginação server-side de notícias (Lote 1b)
NOTICIAS_POR_PAGINA = 9

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
                if ms:
                    _val = ms.group(1)
                    if _val.startswith('b64:'):
                        try:
                            import base64 as _b64
                            _val = _b64.b64decode(_val[4:]).decode('utf-8')
                        except Exception:
                            pass
                    meta[k] = _val
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

def _grad_html(t):
    """Gradiente no trecho marcado com **...**; sem marcação: última palavra (ou tudo, se 1 palavra)."""
    t = str(t or '')
    m = re.search(r'\*\*(.+?)\*\*', t)
    if m:
        return esc(t[:m.start()]) + '<span class="gradient">' + esc(m.group(1)) + '</span>' + esc(t[m.end():])
    partes = t.rsplit(' ', 1)
    if len(partes) == 2:
        return esc(partes[0]) + ' <span class="gradient">' + esc(partes[1]) + '</span>'
    return '<span class="gradient">' + esc(t) + '</span>'

def slugify(t):
    t = re.sub(r'[^a-z0-9\s-]', '', str(t or '').lower())
    return re.sub(r'[\s-]+', '-', t.strip())

def yt_id(url):
    m = re.search(r'(?:v=|youtu\.be/|embed/)([\w-]{11})', str(url or ''))
    return m.group(1) if m else ''

def _sp_id(val):
    """Extrai o ID puro (22 chars) de qualquer formato de link Spotify."""
    m = re.search(r'([A-Za-z0-9]{22})', str(val or ''))
    return m.group(1) if m else str(val or '')

def sp_embed(url):
    u = str(url or '').strip()
    m = re.search(r'spotify\.com/(?:intl-\w+/)?(?:embed/)?(track|album|playlist|artist)/([A-Za-z0-9]{22})', u)
    if m:
        return 'https://open.spotify.com/embed/' + m.group(1) + '/' + m.group(2)
    return u.replace('open.spotify.com/', 'open.spotify.com/embed/')

# ---------- Markdown de matéria (v2) ----------
def inline(t):
    """Markdown inline: negrito, itálico, link — escape único."""
    c = esc(t)
    c = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:var(--text-primary)">\1</strong>', c)
    c = re.sub(r'\*(.+?)\*', r'<em>\1</em>', c)
    c = re.sub(r'\[(.+?)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener" style="color:var(--brand-primary-light)">\1</a>', c)
    return c

def md_html_v2(texto):
    """Figuras c/ legenda+crédito, embeds YT/Spotify, citações, H2/H3."""
    out = []
    for linha in str(texto or '').strip().split('\n'):
        t = linha.strip()
        if not t:
            continue
        m_img = re.match(r'^!\[(.*)\]\((.+?)\)\s*$', t)
        m_yt = re.match(r'^(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})', t)
        m_sp = re.match(r'^\{\{spotify:\s*(.+?)\}\}\s*$', t)
        m_gal = re.match(r'^\{\{galeria:\s*(.+?)\}\}\s*$', t)
        m_num = re.match(r'^\{\{numeros:\s*(.+?)\}\}\s*$', t)
        m_des = re.match(r'^\{\{destaque:\s*(.+?)\}\}\s*$', t)
        if m_img:
            legenda, url = m_img.group(1), m_img.group(2)
            cred = ''
            if ' / ' in legenda:
                partes = legenda.split(' / ')
                if partes[-1].lower().startswith('crédito:'):
                    cred, legenda = partes[-1], ' / '.join(partes[:-1])
            src = (BASE + url) if url.startswith('/') else url
            fig = ('<figure style="margin:2rem 0;text-align:center">'
                   '<img src="' + esc(src) + '" alt="' + esc(legenda) + '" style="max-width:100%;border-radius:4px;margin:0 auto;display:block" loading="lazy">')
            if legenda or cred:
                fig += ('<figcaption style="font-size:.8rem;color:var(--text-secondary);margin-top:.6rem;line-height:1.5">'
                        + esc(legenda)
                        + (' <span style="color:var(--text-muted)">· ' + esc(cred) + '</span>' if cred else '')
                        + '</figcaption>')
            out.append(fig + '</figure>')
        elif m_yt:
            out.append('<div style="margin:2rem 0"><iframe src="https://www.youtube.com/embed/' + m_yt.group(1) + '" style="aspect-ratio:16/9;width:100%;border:0;border-radius:4px" loading="lazy" allowfullscreen title="Vídeo"></iframe></div>')
        elif m_sp:
            out.append('<iframe src="' + esc(sp_embed(m_sp.group(1))) + '?utm_source=generator" style="width:100%;border:0;border-radius:12px;margin:2rem 0" height="152" loading="lazy" title="Ouvir no Spotify"></iframe>')
        elif m_des:
            out.append('<div style="margin:2.6rem auto;max-width:620px;text-align:center;font-size:1.3rem;font-weight:700;line-height:1.55;color:var(--text-primary);font-style:italic">“' + inline(m_des.group(1)) + '”</div>')
        elif m_num:
            cells = ''
            for x in [s.strip() for s in m_num.group(1).split('|') if s.strip()]:
                first = x.split(' ', 1)
                num = first[0]
                lab = first[1] if len(first) > 1 else ''
                cells += '<div style="text-align:center"><div style="font-size:1.7rem;font-weight:800;background:linear-gradient(135deg,var(--brand-primary-light),var(--brand-accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1">' + esc(num) + '</div><div style="font-size:.62rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted);margin-top:.3rem">' + esc(lab) + '</div></div>'
            out.append('<div style="display:flex;flex-wrap:wrap;gap:2.2rem;justify-content:center;margin:2.2rem 0;padding:1.6rem 1rem;border-top:1px solid var(--border-color-light);border-bottom:1px solid var(--border-color-light)">' + cells + '</div>')
        elif m_gal:
            caminhos = [c.strip() for c in m_gal.group(1).split('|') if c.strip()]
            imgs = ''
            for c in caminhos:
                src = (BASE + c) if c.startswith('/') else c
                imgs += '<img src="' + esc(src) + '" alt="" style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:4px" loading="lazy">'
            out.append('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.6rem;margin:2rem 0">' + imgs + '</div>')
        elif t.startswith('### '):
            out.append('<h3 style="font-size:1.05rem;text-transform:uppercase;letter-spacing:.5px;color:var(--brand-accent);margin:2rem 0 .8rem">' + inline(t[4:]) + '</h3>')
        elif t.startswith('## '):
            out.append('<h2 style="font-size:1.25rem;text-transform:uppercase;letter-spacing:.5px;color:var(--text-primary);margin:2.2rem 0 1rem">' + inline(t[3:]) + '</h2>')
        elif t.startswith('> '):
            out.append('<blockquote style="border-left:3px solid var(--brand-primary);padding:.6rem 0 .6rem 1.4rem;margin:1.8rem 0;font-style:italic;color:var(--text-secondary);line-height:1.8">' + inline(t[2:]) + '</blockquote>')
        else:
            out.append('<p style="margin:1rem 0;line-height:1.9">' + inline(t) + '</p>')
    return '\n'.join(out)

def calcular_tempo_leitura(texto):
    palavras = len(re.split(r'\s+', str(texto or '').strip()))
    return str(max(1, round(palavras / 200))) + ' min de leitura'

def md_html(texto):
    return md_html_v2(texto)

def _share(url):
    """Botões de compartilhamento (WhatsApp, Facebook, copiar link)."""
    u = quote(url, safe='')
    return ('<div style="display:flex;gap:.6rem;justify-content:center;align-items:center;margin:2.5rem 0 0;flex-wrap:wrap">'
            '<span style="font-size:.65rem;letter-spacing:2px;text-transform:uppercase;color:var(--text-muted)">Compartilhar:</span>'
            '<a class="plat-link" style="text-decoration:none" target="_blank" rel="noopener" href="https://wa.me/?text=' + u + '">WhatsApp</a>'
            '<a class="plat-link" style="text-decoration:none" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u=' + u + '">Facebook</a>'
            '<button class="plat-link" style="cursor:pointer;font-family:inherit" onclick="navigator.clipboard.writeText(\'' + url + '\');this.textContent=\'✓ Copiado!\'">Copiar link</button>'
            '</div>')

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
playlists = _ler(PASTA['playlists'])

SITE_CFG = {}
cfg_path = os.path.join(PASTA['config'], 'site.md')
if os.path.exists(cfg_path):
    SITE_CFG, _ = parse_md(cfg_path)

# normalizações (a blindagem herdada)
for a in albuns:
    if isinstance(a.get('capa'), list): a['capa'] = a['capa'][0] if a['capa'] else ''
    if isinstance(a.get('generos'), str):
        a['generos'] = [x.strip() for x in a['generos'].replace('[', '').replace(']', '').split(',') if x.strip()]
    if not isinstance(a.get('generos'), list): a['generos'] = []
    a.setdefault('titulo', a['slug'].replace('-', ' ').title())
    a.setdefault('artista', ''); a.setdefault('ano', ''); a.setdefault('destaque', False)

posts = [p for p in posts if str(p.get('rascunho')).lower() != 'true']
posts.sort(key=lambda p: str(p.get('date', '')), reverse=True)

# ordenação do catálogo: com ordem: primeiro; sem: ano desc
def _ordem(a):
    o = a.get('ordem')
    if isinstance(o, list): o = o[0] if o else None
    try: return (0, int(str(o).strip())) if o is not None and str(o).strip() else (1, 0)
    except: return (1, 0)

albuns.sort(key=lambda a: (_ordem(a)[0], _ordem(a)[1], str(a.get('ano', ''))), reverse=False)
_com = [a for a in albuns if _ordem(a)[0] == 0]
_sem = [a for a in albuns if _ordem(a)[0] == 1]
_sem.sort(key=lambda a: (str(a.get('ano', '')), a['titulo']), reverse=True)
albuns[:] = sorted(_com, key=_ordem) + _sem

def _pl_ordem(p):
    o = p.get('ordem')
    if isinstance(o, list): o = o[0] if o else None
    try: return int(str(o).strip()) if o is not None and str(o).strip() else 999
    except: return 999
playlists.sort(key=lambda p: (_pl_ordem(p), str(p.get('titulo', '')).lower()))

# ---------- Templates compartilhados ----------
ATUAL_EH_HOME = True

def _nav(ativo=None):
    ITENS = [('Home', BASE + '/site.html'), ('Gravadora', '#gravadora'),
             ('Projetos', '#projetos'), ('Editora & Direitos', '#editora'),
             ('Audiovisual', '#audiovisual'), ('Playlists', BASE + '/playlists.html'),
             ('Notícias', BASE + '/noticias.html'), ('Quem Somos', '#quemsomos'),
             ('Contato', '#contato')]
    linhas = []
    for nome, href in ITENS:
        if href.startswith('#') and not ATUAL_EH_HOME:
            href = BASE + '/site.html' + href
        st = ' style="color:var(--brand-primary-light)"' if nome == ativo else ''
        linhas.append('        <a href="' + href + '" class="nav-link"' + st + '>' + nome + '</a>')
    return ('<nav class="nav" id="nav">\n' + '\n'.join(linhas) + '\n</nav>')

def _footer():
    return ('<footer class="footer">\n<div class="container">\n'
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
            '            <a href="https://kaagenciacriativa.com.br/" target="_blank" rel="noopener" style="text-decoration:none;display:inline-flex;flex-direction:column;align-items:center;gap:.55rem;color:var(--text-muted, #999);transition:opacity 0.3s" onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.5\'">\n'
            '                <img src="' + BASE + '/img/ka-logo.png" alt="KA. Agência Criativa" style="width:32px;height:32px;border-radius:50%;object-fit:cover">\n'
            '                <div style="display:flex;flex-direction:column;align-items:flex-start;line-height:1.2">\n'
            '                    <span style="font-size:0.7rem;font-weight:700;color:var(--text-secondary, #ccc);letter-spacing:0.5px">KA. Agência Criativa.</span>\n'
            '                    <span style="font-size:0.6rem;font-style:italic;color:var(--text-muted, #888);letter-spacing:0.5px">Presença digital sem ruído</span>\n'
            '                </div>\n'
            '            </a>\n'
            '        </div>\n'
            '    </div>\n</footer>\n')

def _scripts():
    return ('<script>\n'
            'var canvas=document.getElementById("bg");if(!canvas){canvas=document.createElement("canvas");canvas.id="bg";canvas.style.cssText="position:fixed;inset:0;z-index:-1;pointer-events:none";document.body.insertBefore(canvas,document.body.firstChild);}\n'
            'var ctx=canvas.getContext("2d");var w,h,dpr=Math.min(window.devicePixelRatio||1,2);var pointer={x:0,y:0,active:false};var ripples=[];\n'
            'function resize(){w=window.innerWidth;h=window.innerHeight;canvas.width=w*dpr;canvas.height=h*dpr;canvas.style.width=w+"px";canvas.style.height=h+"px";ctx.setTransform(dpr,0,0,dpr,0,0)}window.addEventListener("resize",resize);resize();\n'
            'window.addEventListener("pointermove",function(e){pointer.x=e.clientX;pointer.y=e.clientY;pointer.active=true},{passive:true});\n'
            'window.addEventListener("pointerdown",function(e){ripples.push({x:e.clientX,y:e.clientY,r:4,a:0.30})},{passive:true});\n'
            'function frame(){var t=Date.now()*0.001;ctx.globalCompositeOperation="source-over";ctx.fillStyle="#0d0707";ctx.fillRect(0,0,w,h);ctx.globalCompositeOperation="lighter";\n'
            'var cx=w*0.5,cy=h*0.40;\n'
            'for(var i=0;i<3;i++){var ph=t*0.10+i*2.09;var rad=140+Math.sin(t*0.16+i*1.9)*60+i*90;var al=0.045-i*0.011;\n'
            'ctx.strokeStyle="rgba(200,69,69,"+al.toFixed(3)+")";ctx.lineWidth=1;\n'
            'ctx.beginPath();for(var a=0;a<=Math.PI*2+0.1;a+=0.10){var r=rad*(1+0.05*Math.sin(a*2+ph));var x=cx+Math.cos(a)*r;var y=cy+Math.sin(a)*r;if(a===0)ctx.moveTo(x);else ctx.lineTo(x,y)}ctx.closePath();ctx.stroke()}\n'
            'var sg=ctx.createRadialGradient(cx,cy,0,cx,cy,110);sg.addColorStop(0,"rgba(168,48,48,0.045)");sg.addColorStop(1,"rgba(168,48,48,0)");ctx.fillStyle=sg;ctx.beginPath();ctx.arc(cx,cy,110,0,Math.PI*2);ctx.fill();\n'
            'if(pointer.active){var pg=ctx.createRadialGradient(pointer.x,pointer.y,0,pointer.x,pointer.y,90);pg.addColorStop(0,"rgba(255,255,255,0.045)");pg.addColorStop(1,"rgba(255,255,255,0)");ctx.fillStyle=pg;ctx.beginPath();ctx.arc(pointer.x,pointer.y,90,0,Math.PI*2);ctx.fill()}\n'
            'for(var r=ripples.length-1;r>=0;r--){var rp=ripples[r];rp.r+=1.5;rp.a*=0.972;ctx.strokeStyle="rgba(232,160,74,"+rp.a.toFixed(3)+")";ctx.lineWidth=1;ctx.beginPath();ctx.arc(rp.x,rp.y,rp.r,0,Math.PI*2);ctx.stroke();if(rp.a<0.012)ripples.splice(r,1)}\n'
            'requestAnimationFrame(frame)}requestAnimationFrame(frame);\n'
            'const header=document.getElementById("header");const nav=document.getElementById("nav");\n'
            'const mobileMenuBtn=document.getElementById("mobileMenuBtn");\n'
            'window.addEventListener("scroll",()=>{if(window.scrollY>50)header.classList.add("scrolled");else header.classList.remove("scrolled")},{passive:true});\n'
            'mobileMenuBtn.addEventListener("click",()=>{nav.classList.toggle("active");mobileMenuBtn.textContent=nav.classList.contains("active")?"✕":"☰"});\n'
            'const fadeObserver=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("visible");fadeObserver.unobserve(e.target)}})},{threshold:0.1,rootMargin:"0px 0px -50px 0px"});\n'
            'document.querySelectorAll(".fade-in").forEach(el=>fadeObserver.observe(el));\n'
            '</script>\n')

def _doc(title, desc, body, img_og=None, url=None):
    final_title = SITE_CFG.get('seo_title', title + ' | Por do Som') if title == 'Por do Som | Selo Independente & Produtora Cultural' else (title + ' | Por do Som')
    final_desc = SITE_CFG.get('seo_description', desc) if desc == cfg_str('hero_texto', 'Selo dedicado às Brasilidades')[:155] else desc
    if img_og and img_og.startswith('<'):
        m = re.search(r'src="([^"]+)"', img_og)
        img_og = m.group(1) if m else None
    if img_og and img_og.startswith('/'):
        img_og = DOMINIO + BASE + img_og
    final_img = img_og if img_og else (SITE_CFG.get('seo_og_image') or (DOMINIO + BASE + '/pordosom-profile.jpg'))
    final_url = url if url else (DOMINIO + BASE + '/site.html')
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
            '<script src="https://unpkg.com/lucide@latest"></script>\n</head>\n<body>\n' + body +
            '\n<script type="application/ld+json">\n{"@context":"https://schema.org","@type":"MusicGroup","name":"Por do Som","genre":["Samba de Raiz","MPB","Brasilidades","Instrumental"],"url":"' + DOMINIO + BASE + '/site.html","description":"Selo independente e produtora cultural dedicado às brasilidades."}</script>\n'
            '</body>\n</html>\n')
# ---------- Página de álbum ----------
def page_album(a, prev, next_):
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    generos_str = ' · '.join(GENEROS.get(g, g) for g in a['generos'])
    schema = {"@context": "https://schema.org", "@type": "MusicAlbum",
              "name": a['titulo'], "byArtist": {"@type": "MusicGroup", "name": a['artista']},
              "genre": generos_str, "datePublished": str(a.get('ano', '')),
              "publisher": {"@type": "Organization", "name": "Por do Som"}}
    if a.get('produtor'): schema["producer"] = {"@type": "Person", "name": str(a['produtor'])}
    if a.get('engenheiro'): schema["recordedBy"] = {"@type": "Person", "name": str(a['engenheiro'])}
    if a.get('estudio'): schema["recordedAt"] = {"@type": "Place", "name": str(a['estudio'])}
    if a.get('ano_gravacao'): schema["dateCreated"] = str(a['ano_gravacao'])
    if a.get('gravadora'): schema["productionCompany"] = {"@type": "Organization", "name": str(a['gravadora'])}
    if a.get('isrc'): schema["isrcCode"] = str(a['isrc'])

    embeds = ''
    if a.get('spotify'):
        embeds += '\n<iframe class="album-iframe-spotify" src="' + esc(sp_embed(a['spotify'])) + '" height="380" loading="lazy" title="Ouvir no Spotify"></iframe>'
    yid = yt_id(a.get('youtube', ''))
    if yid:
        embeds += '\n<iframe src="https://www.youtube.com/embed/' + yid + '" style="aspect-ratio:16/9" loading="lazy" allowfullscreen title="Vídeo"></iframe>'
    plats = ''.join('<a class="plat-link" href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(n) + '</a>'
                    for n, u in [('Spotify', a.get('spotify', '')), ('YouTube', a.get('youtube', '')),
                                 ('Apple', a.get('apple', '')), ('Deezer', a.get('deezer', ''))] if u)

    _ficha_items = [
        ('Produtor musical', a.get('produtor')),
        ('Engenheiro de som', a.get('engenheiro')),
        ('Estúdio', a.get('estudio')),
        ('Ano de gravação', a.get('ano_gravacao')),
        ('Músicos participantes', a.get('musicos')),
        ('ISRC', a.get('isrc')),
        ('Gravadora', a.get('gravadora')),
        ('Distribuidora', a.get('distribuidora')),
    ]
    _ficha_linhas = ''
    for _lbl, _val in _ficha_items:
        if _val:
            if isinstance(_val, list):
                _val = ' · '.join(str(x) for x in _val)
            _ficha_linhas += ('<div class="album-ficha-linha">'
                              '<div class="album-ficha-label">' + esc(_lbl) + '</div>'
                              '<div class="album-ficha-valor">' + esc(_val) + '</div>'
                              '</div>')
    ficha_html = ''
    if _ficha_linhas:
        ficha_html = ('<aside class="album-ficha">'
                      '<div class="album-ficha-titulo">Ficha técnica</div>'
                      + _ficha_linhas +
                      '</aside>')

    prev_h = ('<a class="album-nav-link" href="' + BASE + '/albuns/' + prev['slug'] + '.html">&#8592; ' + esc(prev['titulo']) + '</a>') if prev else '<span></span>'
    next_h = ('<a class="album-nav-link" href="' + BASE + '/albuns/' + next_['slug'] + '.html">' + esc(next_['titulo']) + ' &#8594;</a>') if next_ else '<span></span>'
    capa = str(a.get('capa', '') or '')
    capa_src = (BASE + capa) if capa.startswith('/') else capa
    conteudo_cls = 'album-conteudo' if ficha_html else 'album-conteudo album-conteudo-sem-ficha'
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav() +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<main class="album-page">\n<div class="container">\n<div class="album-hero">\n'
            '            <div class="album-capa-grande">\n'
            '                <img src="' + esc(capa_src) + '" alt="Capa" loading="lazy" onerror="this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 600 600%22%3E%3Crect fill=%22%231a0e0e%22 width=%22600%22 height=%22600%22/%3E%3C/svg%3E\'">\n'
            '            </div>\n<div>\n'
            '                <span class="album-kicker">Álbum · ' + esc(a.get('ano', '')) + ' · ' + esc(generos_str) + '</span>\n'
            '                <h1 class="album-titulo-grande">' + esc(a['titulo']) + '</h1>\n'
            '                <div class="album-artista-grande">' + esc(a['artista']) + '</div>\n'
            '                <div class="album-descricao">' + md_html_v2(a.get('corpo', '')) + '</div>\n'
            + ('<p class="album-descricao-en">' + esc(a.get('texto_en', '')) + '</p>' if a.get('texto_en') else '')
            + '            </div>\n</div>\n'
            + '<div class="' + conteudo_cls + '">\n'
            + (ficha_html if ficha_html else '')
            + '            <div class="album-player">\n'
            + '                <div class="album-embeds">' + embeds + '\n</div>\n'
            + '                <div class="album-plataformas">' + plats + '</div>\n'
            + '            </div>\n'
            + '</div>\n'
            + '        <div class="album-navegacao">\n' + prev_h + '\n'
            + '            <a class="album-nav-link" href="' + BASE + '/index.html">← Voltar para Home</a>\n'
            + '            ' + next_h + '\n</div>\n</div>\n</main>\n' + _footer() + _scripts())
    d = _doc(a['titulo'] + ' — ' + a['artista'], (a.get('corpo') or a['titulo'])[:155], body, img_og=capa)
    return d.replace('</head>', '<script type="application/ld+json">\n' + json.dumps(schema, ensure_ascii=False) + '\n</script>\n</head>')


# ---------- site.html (o site inteiro, seções por âncoras) ----------
def _sec(id_, subtitulo, titulo_cfg, desc_cfg=None, conteudo='', alt=False):
    titulo_html = _grad_html(cfg_str(titulo_cfg))
    desc = ''
    if desc_cfg and cfg_str(desc_cfg):
        desc = '\n<p class="section-description">' + esc(cfg_str(desc_cfg)) + '</p>'
    cls = 'teaser teaser-alt' if alt else 'teaser'
    return ('<section class="' + cls + '" id="' + id_ + '">\n<div class="container">\n'
            '        <div class="teaser-head">\n'
            '            <span class="section-subtitle">' + esc(subtitulo) + '</span>\n'
            '            <h2 class="section-title">' + titulo_html + '</h2>' + desc + '\n'
            '        </div>\n' + conteudo + '\n</div>\n</section>\n')

def _card_noticia(p):
    """Card de notícia (vertical, para grades)."""
    partes = str(p.get('date', '')).split('-')
    data = '/'.join(reversed(partes)) if len(partes) == 3 else ''
    im = p.get('imagem', '')
    if isinstance(im, list): im = im[0] if im else ''
    img = (BASE + im) if str(im).startswith('/') else (im or BASE + '/pordosom-profile.jpg')
    slug = slugify(p.get('title', 'post'))
    return (
        '<a href="' + BASE + '/posts/' + slug + '.html" class="card-noticia fade-in">'
        '<div class="card-noticia-img">'
        '<img src="' + esc(img) + '" alt="' + esc(p.get('title', '')) + '" loading="lazy">'
        '</div>'
        '<div class="card-noticia-info">'
        '<div class="card-noticia-meta">' + data + ' · ' + calcular_tempo_leitura(p.get('corpo', '')) + '</div>'
        '<h3 class="card-noticia-titulo">' + esc(p.get('title', '')) + '</h3>'
        '<p class="card-noticia-resumo">' + esc(str(p.get('resumo', ''))[:140]) + '…</p>'
        '<span class="card-noticia-link">Ler notícia →</span>'
        '</div>'
        '</a>'
    )

def _card_projeto(p):
    """Card de projeto (vertical, para grades)."""
    st = str(p.get('status', 'realizado'))
    st_cls = 'realizado' if st != 'captacao' else 'captacao'
    st_lbl = '✓ Realizado' if st != 'captacao' else '★ Em captação'
    img = str(p.get('imagem', '') or '')
    img_src = (BASE + img) if img.startswith('/') else (img or BASE + '/pordosom-profile.jpg')
    slug = p.get('slug', slugify(p.get('titulo', 'projeto')))
    corpo_txt = str(p.get('corpo', '') or '')
    return (
        '<div class="project-card fade-in">'
        '<div class="project-card-visual">'
        '<img class="project-card-img" src="' + esc(img_src) + '" alt="' + esc(p['titulo']) + '" loading="lazy">'
        '<span class="project-badge ' + st_cls + '">' + st_lbl + '</span>'
        '</div>'
        '<div class="project-body">'
        '<h3 class="project-title">' + esc(p['titulo']) + '</h3>'
        '<p class="project-desc">' + esc(corpo_txt[:160]) + ('…' if len(corpo_txt) > 160 else '') + '</p>'
        '<a href="' + BASE + '/projetos/' + slug + '.html" class="project-link">Ver projeto →</a>'
        '</div>'
        '</div>'
    )

def embed_playlist_url(plataforma, embed_id):
    """Normaliza qualquer formato (ID puro ou URL) para uma URL de embed."""
    p = str(plataforma or 'spotify').lower().strip()
    e = str(embed_id or '').strip()
    if not e:
        return ''
    if p == 'spotify':
        m = re.search(r'(?:playlist|album|track|artist)/([A-Za-z0-9]{22})', e)
        if m:
            return 'https://open.spotify.com/embed/playlist/' + m.group(1)
        if re.match(r'^[A-Za-z0-9]{22}$', e):
            return 'https://open.spotify.com/embed/playlist/' + e
        return e
    if p == 'youtube':
        m = re.search(r'list=([A-Za-z0-9_-]+)', e)
        if m:
            return 'https://www.youtube.com/embed/videoseries?list=' + m.group(1)
        m = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', e)
        if m:
            return 'https://www.youtube.com/embed/' + m.group(1)
        if e.startswith('PL') or e.startswith('UU') or e.startswith('OL'):
            return 'https://www.youtube.com/embed/videoseries?list=' + e
        return 'https://www.youtube.com/embed/' + e
    if p == 'deezer':
        m = re.search(r'(?:playlist|album|track)/(\d+)', e)
        if m:
            return 'https://widget.deezer.com/widget/dark/playlist/' + m.group(1)
        if re.match(r'^\d+$', e):
            return 'https://widget.deezer.com/widget/dark/playlist/' + e
        return e
    return e


def _card_playlist(p):
    """Card de playlist (vertical, para grades)."""
    capa = str(p.get('capa', '') or '')
    capa_src = (BASE + capa) if capa.startswith('/') else (capa or BASE + '/pordosom-profile.jpg')
    slug = p.get('slug', slugify(p.get('titulo', 'playlist')))
    desc = str(p.get('descricao_curta', '') or '')
    plat = str(p.get('plataforma', 'spotify') or 'spotify').lower().strip()
    return (
        '<a href="' + BASE + '/playlists/' + slug + '.html" class="card-playlist fade-in">'
        '<div class="card-playlist-img">'
        '<img src="' + esc(capa_src) + '" alt="' + esc(p.get('titulo', '')) + '" loading="lazy">'
        '<span class="card-playlist-plat">' + esc(plat) + '</span>'
        '</div>'
        '<div class="card-playlist-info">'
        '<h3 class="card-playlist-titulo">' + esc(p.get('titulo', '')) + '</h3>'
        '<p class="card-playlist-resumo">' + esc(desc[:140]) + ('…' if len(desc) > 140 else '') + '</p>'
        '<span class="card-playlist-link">Ouvir →</span>'
        '</div>'
        '</a>'
    )


def gera_site():
    ATUAL_EH_HOME = True
    # --- HERO ---
    slog_html = _grad_html(cfg_str('hero_slogan', 'Onde a música nasce'))
    hi = str(SITE_CFG.get('hero_imagem', '') or '').strip()
    hero = ('<section class="hero" style="' + ('background-image: url(' + hi + '); background-size: cover; background-position: center;' if hi else '') + '">\n<div class="hero-bg"></div>\n<div class="hero-bg-overlay"></div>\n'
            '    <div class="hero-noise"></div>\n<div class="hero-content">\n'
            '        <p class="hero-subtitle">Selo Pôr do Som</p>\n'
            '        <h1 class="hero-title">' + slog_html + '</h1>\n'
            '        <p class="hero-description">' + esc(cfg_str('hero_texto')) + '</p>\n'
            '    </div>\n<div class="hero-scroll">\n        <span>' + esc(cfg_str('hero_scroll_texto', '')) + '</span>\n'
            '        <div class="hero-scroll-line"></div>\n    </div>\n</section>\n')
    # --- NOTÍCIAS (grade com N mais recentes; N vem do painel) ---
    try:
        _qtd_home = int(str(cfg_str('noticias_home_qtd', '3')).strip() or '3')
    except (ValueError, TypeError):
        _qtd_home = 3
    _qtd_home = max(1, min(_qtd_home, 12))
    posts_home = posts[:_qtd_home]
    cards_noticias = ''.join(_card_noticia(p) for p in posts_home) if posts_home else '<p style="text-align:center;color:var(--text-muted)">Nenhuma notícia publicada ainda.</p>'
    sec_noticias = ('<section class="teaser" id="noticias">\n<div class="container">\n'
                    '        <div class="teaser-head">\n'
                    '            <span class="section-subtitle">Notícias</span>\n'
                    '            <h2 class="section-title">Do <span class="gradient">selo</span></h2>\n'
                    '        </div>\n'
                    '        <div class="grade-noticias">' + cards_noticias + '</div>\n'
                    '        <div style="text-align:center;margin-top:2.5rem">\n'
                    '            <a class="btn btn-outline" style="text-decoration:none" href="' + BASE + '/noticias.html">Ver todas as notícias →</a>\n'
                    '        </div>\n</div>\n</section>\n')
    # --- GRAVADORA (catalogo + filtros + artistas) ---
    vitrine_js = '<div class="vitrine-grid" id="vitrine"></div>\n<div style="text-align:center;margin-top:2.5rem"><a href="' + BASE + '/catalogo.html" class="btn btn-outline" style="text-decoration:none">Ver catálogo completo (' + str(len(albuns)) + ' obras) →</a></div>'
    sec_grav = ('<section class="teaser" id="gravadora">\n<div class="container">\n'
                '        <div class="teaser-head">\n'
                '            <span class="section-subtitle">Gravadora</span>\n'
                '            <h2 class="section-title">' + _grad_html(cfg_str('grav_titulo')) + '</h2>\n'
                '            <p class="section-description">' + esc(cfg_str('grav_descricao')) + '</p>\n'
                '        </div>\n' + vitrine_js + '\n</div>\n</section>\n')
    # --- PROJETOS (grade com todos) ---
    cards_p = [_card_projeto(p) for p in projetos]
    conteudo_proj = '<div class="grade-projetos">' + ''.join(cards_p) + '</div>'
    if len(projetos) > 6:
        conteudo_proj += ('<div style="text-align:center;margin-top:2.5rem">'
                          '<a href="' + BASE + '/projetos.html" class="btn btn-outline" style="text-decoration:none">'
                          'Ver todos os projetos →</a></div>')
    sec_proj = _sec('projetos', 'Projetos & Festivais', 'projetos_titulo', 'projetos_descricao',
                    conteudo_proj, alt=True)
    # --- AUDIOVISUAL (clips por grupo) ---
    _clips_home = clips[:4]
    vids_home = '\n'.join('            <iframe src="https://www.youtube.com/embed/' + str(c.get('yt_id', '')) +
                          '" loading="lazy" allowfullscreen title="' + esc(c.get('titulo', '')) + '"></iframe>' for c in _clips_home)
    btn_av = ('\n<div style="text-align:center;margin-top:2.5rem"><a href="' + BASE + '/audiovisual.html" '
              'class="btn btn-outline" style="text-decoration:none">Ver todos os vídeos (' + str(len(clips)) + ') →</a></div>')
    sec_av = _sec('audiovisual', 'Audiovisual', 'audio_titulo', 'audio_descricao',
                  '<div class="teaser-videos">\n' + vids_home + '\n</div>' + btn_av)
    # --- PLAYLISTS (teaser) ---
    playlists_destaque = [p for p in playlists if p.get('destaque')][:3]
    if not playlists_destaque:
        playlists_destaque = playlists[:3]
    if playlists_destaque:
        cards_pl = ''.join(_card_playlist(p) for p in playlists_destaque)
        btn_pl = ('<div style="text-align:center;margin-top:2.5rem">'
                  '<a href="' + BASE + '/playlists.html" class="btn btn-outline" style="text-decoration:none">'
                  'Ver todas as playlists (' + str(len(playlists)) + ') →</a></div>')
        playlists_html = '<div class="grade-playlists">' + cards_pl + '</div>' + btn_pl
    else:
        playlists_html = '<p style="text-align:center;color:var(--text-muted)">Nenhuma playlist cadastrada ainda.</p>'
    sec_pl = _sec('playlists', 'Playlists', 'home_playlists_titulo', None, playlists_html, alt=True)
    # --- QUEM SOMOS (com stats migrados do manifesto + link pro Sérgio) ---
    stats = [('31', 'Obras no catálogo'), ('10+', 'Artistas'), ('3', 'Festivais próprios'), ('42', 'Vídeos produzidos')]
    stats_html = '\n'.join('<div class="stat-item fade-in"><div class="stat-num">' + n + '</div><div class="stat-label">' + l + '</div></div>' for n, l in stats)
    portfolio = cfg_str('portfolio_link')
    port_html = ('<div style="margin-top:2rem" class="fade-in"><a href="' + esc(portfolio) + '" target="_blank" rel="noopener" '
                 'class="btn btn-outline" style="text-decoration:none">Currículo completo &amp; Portfolio ↗</a></div>') if portfolio else ''
    _sergio_nome = cfg_str('sergio_nome', 'Sérgio Mendonça')
    sergio_link = ('<div style="margin-top:2rem" class="fade-in"><a href="' + BASE + '/sergio-mendonca.html" '
                   'class="btn btn-outline" style="text-decoration:none">Conheça a trajetória de ' + esc(_sergio_nome) + ' →</a></div>')
    sec_qs = ('<section class="teaser teaser-alt" id="quemsomos">\n<div class="container">\n'
              '        <div class="manifesto-content">\n'
              '            <span class="section-subtitle">Quem Somos</span>\n'
              '            <h2 class="section-title">Mais de 20 anos <span class="gradient">cantando o Brasil</span></h2>\n'
              '            <div class="quemsomos-texto">' + md_html_v2(cfg_str('quemsomos_texto')) + '</div>\n'
              '            <div class="manifesto-stats" style="margin-top:3rem">\n' + stats_html + '\n</div>\n'
              + port_html + sergio_link + '\n        </div>\n</div>\n</section>\n')
    # --- RECONHECIMENTO (prêmios do portfolio) ---
    premios = [cfg_str('premio' + str(i)) for i in range(1, 7)]
    premios = [p for p in premios if p]
    sec_premios = ''
    if premios and cfg_str('premios_titulo'):
        cards_pr = []
        for p in premios:
            m = re.match(r'^(\d{4}(?:/\d{4})?)\s*[·\-–]\s*(.+)$', p)
            if m:
                cards_pr.append('<div class="fade-in" style="background:var(--bg-card);border:1px solid var(--border-color-light);border-radius:2px;padding:1.4rem"><div style="font-size:.7rem;font-weight:800;letter-spacing:2px;color:var(--brand-accent);margin-bottom:.6rem">' + esc(m.group(1)) + '</div><div style="font-size:.85rem;line-height:1.6;color:var(--text-secondary)">' + esc(m.group(2)) + '</div></div>')
            else:
                cards_pr.append('<div class="fade-in" style="grid-column:1/-1;background:var(--bg-card);border:1px solid var(--border-color-light);border-radius:2px;padding:1.4rem"><div style="font-size:.7rem;font-weight:800;letter-spacing:2px;color:var(--brand-accent);margin-bottom:.6rem">TRAJETÓRIA</div><div style="font-size:.85rem;line-height:1.7;color:var(--text-secondary)">' + esc(p) + '</div></div>')
        sec_premios = _sec('premios', 'Reconhecimento', 'premios_titulo', 'premios_descricao', '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem">' + ''.join(cards_pr) + '</div>')
    # --- EDITORA ---
    sec_ed = ('<section class="teaser" id="editora">\n<div class="container">\n'
              '        <div class="manifesto-content">\n'
              '            <span class="section-subtitle">Editora &amp; Direitos</span>\n'
              '            <h2 class="section-title">Administração de <span class="gradient">obras musicais</span></h2>\n'
              '            <p class="manifesto-text">' + esc(cfg_str('editora_texto')) + '</p>\n'
              '            <p class="manifesto-signature">Consultoria: <a href="#contato" style="color:var(--brand-primary-light);text-decoration:none;text-transform:none;letter-spacing:normal">fale com o selo</a></p>\n'
              '        </div>\n</div>\n</section>\n')
    # --- CONTATO ---
    email = cfg_str('email_contato', 'contato@pordosom.com.br')
    wa = cfg_str('whatsapp_contato')
    wa_html = ('<a href="https://wa.me/' + esc(wa) + '" class="social-card" style="text-decoration:none">'
               '<div class="social-card-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.65 15.02L2 22l5.13-1.32A10 10 0 1 0 12 2Zm0 1.8a8.2 8.2 0 1 1-4.02 15.35l-.29-.17-3.03.78.81-2.96-.19-.3A8.2 8.2 0 0 1 12 3.8Zm-3.1 4.02c-.17 0-.45.06-.68.31-.23.25-.9.88-.9 2.14s.92 2.48 1.05 2.65c.13.17 1.8 2.86 4.44 3.9 2.2.86 2.65.69 3.14.64.49-.05 1.57-.64 1.79-1.26.22-.62.22-1.15.16-1.26-.06-.11-.23-.17-.48-.29l-1.96-.98c-.26-.1-.45-.15-.64.1-.19.25-.73.9-.9 1.09-.16.19-.33.21-.58.09-.25-.13-1.07-.4-2.03-1.26-.75-.67-1.26-1.5-1.41-1.75-.15-.25-.02-.39.11-.51.11-.11.25-.29.38-.44.13-.15.17-.25.25-.42.08-.17.04-.32-.02-.45-.06-.13-.57-1.43-.79-1.95-.2-.49-.41-.42-.57-.43l-.36-.01Z"/></svg></div>'
               '<div class="social-card-text"><div class="social-card-label">WhatsApp</div>'
               '<div class="social-card-handle">' + esc(wa) + '</div></div></a>') if wa else ''
    sec_cont = ('<section class="teaser teaser-alt" id="contato">\n<div class="container">\n'
                '        <div class="teaser-head">\n'
                '            <span class="section-subtitle">Contato</span>\n'
                '            <h2 class="section-title">' + _grad_html(cfg_str('contato_titulo', 'Vamos fazer música juntos?')) + '</h2>\n'
                '            <p class="section-description">' + esc(cfg_str('contato_descricao')) + '</p>\n'
                '            <div class="teaser-contato" style="margin-top:1.5rem">\n'
                '                <a href="mailto:' + esc(email) + '" class="social-card" style="text-decoration:none">\n'
                '                    <div class="social-card-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="4.5" width="19" height="15" rx="3"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/></svg></div>\n'
                '                    <div class="social-card-text"><div class="social-card-label">E-mail</div>\n'
                '                    <div class="social-card-handle">' + esc(email) + '</div></div></a>\n'
                '                <a href="https://www.instagram.com/pordosomcultural" target="_blank" rel="noopener" class="social-card" style="text-decoration:none">\n'
                '                    <div class="social-card-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17.3 6.7h.01"/></svg></div>\n'
                '                    <div class="social-card-text"><div class="social-card-label">Instagram</div>\n'
                '                    <div class="social-card-handle">@pordosomcultural</div></div></a>\n'
                + wa_html + '\n</div>\n</div>\n</div>\n</section>\n')
    # --- O JS da vitrine/filtros/banner EMBUTIDO ---
    js_site = ('<script>\n'
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
               '  CAT.albuns.sort((x,y)=>{const ox=parseInt(x.ordem)||0,oy=parseInt(y.ordem)||0;if(ox&&oy)return ox-oy;if(ox)return -1;if(oy)return 1;return String(y.ano||"").localeCompare(String(x.ano||""))});\n'
               '  const vitrine = document.getElementById("vitrine");\n'
               '  if (vitrine) { vitrine.innerHTML = CAT.albuns.filter(a=>a.destaque).slice(0,6).map(a =>\n'
               '    `<a href="${BASE}/albuns/${a.slug}.html"><img src="${capaSrc(a.capa)}" alt="Capa: ${a.title||a.titulo||""}" loading="lazy" onerror="this.src=\'${fallback}\'"><span class="vitrine-titulo">${a.titulo||""}</span></a>`).join(""); }\n'
               '  const filtrosEl = document.getElementById("filtros");\n'
               '  const grid = document.getElementById("catalogo-grid");\n'
               '  if (filtrosEl && grid) {\n'
               '    const contagem = { todos: CAT.albuns.length };\n'
               '    CAT.generos.forEach(g => { contagem[g.id] = CAT.albuns.filter(a=>a.generos.includes(g.id)).length });\n'
               '    filtrosEl.innerHTML = `<button class="filtro ativo" data-g="todos">Todos <span class="count">${contagem.todos}</span></button>` +\n'
               '      CAT.generos.map(g=>`<button class="filtro" data-g="${g.id}">${g.nome} <span class="count">${contagem[g.id]||0}</span></button>`).join("");\n'
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
               '})();\n'
               '</script>\n')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav() +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            + hero + sec_noticias + sec_grav + sec_proj + sec_ed + sec_av + sec_pl
            + sec_qs + sec_premios + sec_cont + '\n' + _footer() + _scripts() + js_site)
    _conteudo = _doc('Por do Som | Selo Independente & Produtora Cultural',
                     cfg_str('hero_texto', 'Selo dedicado às Brasilidades')[:155], body)
    for _alvo in ('site.html', 'index.html'):
        with open(os.path.join(BASE_DIR, _alvo), 'w', encoding='utf-8') as f:
            f.write(_conteudo)
    print('✔ site.html + index.html gerados (seções: hero, notícias, gravadora, artistas, projetos, audiovisual, playlists, manifesto, quem-somos, editora, contato)')

def gera_noticias():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    total = len(posts)
    total_pag = max(1, (total + NOTICIAS_POR_PAGINA - 1) // NOTICIAS_POR_PAGINA) if total else 1
    for pagina in range(1, total_pag + 1):
        ini = (pagina - 1) * NOTICIAS_POR_PAGINA
        fim = ini + NOTICIAS_POR_PAGINA
        posts_pag = posts[ini:fim]
        cards = ''.join(_card_noticia(p) for p in posts_pag)
        lista_html = ('<div class="grade-noticias">' + cards + '</div>') if cards else '<p style="text-align:center;color:var(--text-muted)">Nenhuma notícia publicada ainda.</p>'
        nav_pag = ''
        if total_pag > 1:
            itens = []
            if pagina > 1:
                prev_url = 'noticias.html' if pagina == 2 else 'noticias-' + str(pagina - 1) + '.html'
                itens.append('<a class="pag-link" href="' + BASE + '/' + prev_url + '">← Anterior</a>')
            else:
                itens.append('<span class="pag-link pag-disabled">← Anterior</span>')
            for n in range(1, total_pag + 1):
                url_n = 'noticias.html' if n == 1 else 'noticias-' + str(n) + '.html'
                cls = 'pag-num pag-ativo' if n == pagina else 'pag-num'
                itens.append('<a class="' + cls + '" href="' + BASE + '/' + url_n + '">' + str(n) + '</a>')
            if pagina < total_pag:
                itens.append('<a class="pag-link" href="' + BASE + '/noticias-' + str(pagina + 1) + '.html">Próxima →</a>')
            else:
                itens.append('<span class="pag-link pag-disabled">Próxima →</span>')
            nav_pag = '<nav class="paginacao">' + ''.join(itens) + '</nav>'
        if pagina == 1:
            sub = 'Notícias do selo'
            titulo_pag = 'Notícias — Por do Som'
            url_pag = DOMINIO + BASE + '/noticias.html'
        else:
            sub = 'Notícias do selo · Página ' + str(pagina) + ' de ' + str(total_pag)
            titulo_pag = 'Notícias — Página ' + str(pagina) + ' — Por do Som'
            url_pag = DOMINIO + BASE + '/noticias-' + str(pagina) + '.html'
        body = ('<header class="header" id="header">\n<a href="' + BASE + '/index.html" class="logo">\n'
            '<span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '<span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Notícias') +
            '<button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n<div class="container">\n'
            '<span class="section-subtitle">' + sub + '</span>\n'
            '<h1 class="section-title">Lançamentos, projetos e novidades</h1>\n'
            '<p class="section-description">Tudo o que a Por do Som está fazendo agora — em matérias completas.</p>\n'
            '</div>\n</header>\n'
            '<section style="padding:3rem 0">\n<div class="container">\n' + lista_html + '\n' + nav_pag + '\n</div>\n</section>\n' + _footer() + _scripts())
        nome_arq = 'noticias.html' if pagina == 1 else 'noticias-' + str(pagina) + '.html'
        with open(os.path.join(BASE_DIR, nome_arq), 'w', encoding='utf-8') as f:
            f.write(_doc(titulo_pag, 'Lançamentos, projetos e novidades do selo Por do Som.', body, url=url_pag))
    print('✔ ' + str(total_pag) + ' página(s) de notícias geradas (' + str(total) + ' notícias)')


# ---------- Páginas de notícia ----------
def gera_posts():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    os.makedirs(os.path.join(BASE_DIR, 'posts'), exist_ok=True)
    n = 0
    for _i, p in enumerate(posts):
        partes = str(p.get('date', '')).split('-')
        data = '/'.join(reversed(partes)) if len(partes) == 3 else ''
        img = ''
        if p.get('imagem'):
            im = p['imagem']
            if isinstance(im, list): im = im[0] if im else ''
            img = '<img src="' + BASE + im + '" alt="" style="width:100%;max-width:760px;border-radius:4px;margin:0 auto 2rem;display:block" loading="lazy">'
        prev_p = posts[_i - 1] if _i > 0 else None
        next_p = posts[_i + 1] if _i < len(posts) - 1 else None
        prev_h = ('<a class="album-nav-link" href="' + BASE + '/posts/' + slugify(prev_p.get('title','post')) + '.html">&#8592; ' + esc(prev_p.get('title',''))[:40] + '</a>') if prev_p else '<span></span>'
        next_h = ('<a class="album-nav-link" href="' + BASE + '/posts/' + slugify(next_p.get('title','post')) + '.html">' + esc(next_p.get('title',''))[:40] + ' &#8594;</a>') if next_p else '<span></span>'
        share_html = _share(DOMINIO + BASE + '/posts/' + slugify(p.get('title','post')) + '.html')
        outros = [q for q in posts if q is not p][:3]
        rel_html = ''
        if outros:
            cards_rel = ''
            for q in outros:
                qim = q.get('imagem', '')
                if isinstance(qim, list): qim = qim[0] if qim else ''
                qsrc = (BASE + qim) if str(qim).startswith('/') else (qim or BASE + '/pordosom-profile.jpg')
                cards_rel += '<a href="' + BASE + '/posts/' + slugify(q.get('title', 'post')) + '.html" style="text-decoration:none;background:var(--bg-card);border:1px solid var(--border-color-light);border-radius:2px;overflow:hidden;display:block"><img src="' + esc(qsrc) + '" alt="" style="width:100%;height:110px;object-fit:cover" loading="lazy"><div style="padding:.8rem .9rem;font-size:.8rem;font-weight:700;color:var(--text-primary);line-height:1.4">' + esc(q.get('title', '')) + '</div></a>'
            rel_html = '<div style="margin:3rem 0 0"><div style="font-size:.68rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--brand-accent);margin-bottom:1rem">Leia também</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem">' + cards_rel + '</div></div>'
        assinatura = '<div style="margin:2.5rem 0 0;padding:1.4rem;background:var(--bg-card);border:1px solid var(--border-color-light);border-radius:2px;display:flex;gap:1rem;align-items:center"><img src="' + BASE + '/pordosom-profile.jpg" alt="" style="width:52px;height:52px;border-radius:50%;object-fit:cover;flex-shrink:0"><div style="font-size:.8rem;line-height:1.6;color:var(--text-secondary)"><strong style="color:var(--text-primary)">Sobre a Por do Som</strong><br>Selo independente, produtora cultural e gravadora dedicada às brasilidades desde 2001. <a href="' + BASE + '/site.html#quemsomos" style="color:var(--brand-primary-light)">Conheça nossa história →</a></div></div>'
        body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
                '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
                '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav() +
                '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
                '<main class="album-page">\n<div class="container">\n'
                '        <div style="max-width:760px;margin:0 auto">\n'
                '            <span class="album-kicker">Notícia · ' + data + ' · ' + calcular_tempo_leitura(p.get('corpo', '')) + '</span>\n'
                '            <h1 class="album-titulo-grande" style="font-size:clamp(1.6rem,4vw,2.4rem)">' + esc(p.get('title', '')) + '</h1>\n'                '            <div style="font-size:.78rem;color:var(--text-muted);margin:.5rem 0 1.4rem;letter-spacing:.4px">Por <strong style="color:var(--text-secondary)">' + esc(cfg_str('autor_padrao', 'Redação Por do Som')) + '</strong></div>\n'
                '            <div class="album-meta-info">' + esc(p.get('resumo', '')) + '</div>\n'
                '        </div>\n' + img + '\n'
                '        <div style="max-width:680px;margin:0 auto;font-size:.98rem;line-height:2;color:var(--text-secondary)">\n'
                + md_html(p.get('corpo', '')) + rel_html + assinatura + '\n</div>\n'
                '        <div class="album-navegacao">\n' + prev_h + '\n'
                '            <a class="album-nav-link" href="' + BASE + '/noticias.html">Todas as notícias</a>\n' + next_h + '\n'
                '        </div>\n' + share_html + '\n</div>\n</main>\n' + _footer() + _scripts())
        with open(os.path.join(BASE_DIR, 'posts', slugify(p.get('title', 'post')) + '.html'), 'w', encoding='utf-8') as f:
            d = _doc(p.get('title', ''), str(p.get('resumo', ''))[:155], body, img_og=img)
            schema_post = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p.get('title',''), "datePublished": str(p.get('date','')), "description": str(p.get('resumo',''))[:155], "publisher": {"@type": "Organization", "name": "Por do Som"}}
            d = d.replace('</head>', '<script type="application/ld+json">\n' + json.dumps(schema_post, ensure_ascii=False) + '\n</script>\n</head>')
            f.write(d)
        n += 1
    print('✔ ' + str(n) + ' páginas de notícia geradas')
    # ---------- catalogo.json ----------
# ---------- Página individual de playlist ----------
def page_playlist(p, prev, next_):
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    capa = str(p.get('capa', '') or '')
    capa_src = (BASE + capa) if capa.startswith('/') else capa
    embed_url = embed_playlist_url(p.get('plataforma', 'spotify'), p.get('embed_id', ''))
    embed_html = ''
    if embed_url:
        embed_html = ('<div class="playlist-embed"><iframe src="' + esc(embed_url) +
                      '" loading="lazy" allowfullscreen title="' + esc(p.get('titulo', '')) +
                      '" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe></div>')
    plat = str(p.get('plataforma', 'spotify') or 'spotify').lower().strip()
    prev_h = ('<a class="album-nav-link" href="' + BASE + '/playlists/' + prev['slug'] + '.html">&#8592; ' + esc(prev.get('titulo','')) + '</a>') if prev else '<span></span>'
    next_h = ('<a class="album-nav-link" href="' + BASE + '/playlists/' + next_['slug'] + '.html">' + esc(next_.get('titulo','')) + ' &#8594;</a>') if next_ else '<span></span>'
    texto_html = md_html_v2(p.get('corpo', '')) if p.get('corpo') else ''
    share_html = _share(DOMINIO + BASE + '/playlists/' + p['slug'] + '.html')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Playlists') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<main class="album-page">\n<div class="container">\n'
            '        <div class="playlist-hero">\n'
            + (('<div class="playlist-capa-grande"><img src="' + esc(capa_src) + '" alt="' + esc(p.get('titulo','')) + '" loading="lazy"></div>') if capa_src else '')
            + '<div>\n'
            '                <span class="album-kicker">Playlist · ' + esc(plat) + '</span>\n'
            '                <h1 class="album-titulo-grande">' + esc(p.get('titulo','')) + '</h1>\n'
            + (('<div class="album-descricao">' + esc(p.get('descricao_curta','')) + '</div>') if p.get('descricao_curta') else '')
            + embed_html
            + '</div>\n</div>\n'
            + (('<div class="playlist-texto">' + texto_html + '</div>') if texto_html else '')
            + '<div class="album-navegacao">\n' + prev_h + '\n'
            '            <a class="album-nav-link" href="' + BASE + '/playlists.html">Todas as playlists</a>\n'
            '            ' + next_h + '\n</div>\n' + share_html + '\n</div>\n</main>\n' + _footer() + _scripts())
    return _doc('Playlist: ' + p.get('titulo',''), str(p.get('descricao_curta',''))[:155], body, img_og=(capa_src or None))


def gera_playlists():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    cards = ''.join(_card_playlist(p) for p in playlists) if playlists else '<p style="text-align:center;color:var(--text-muted)">Nenhuma playlist cadastrada ainda.</p>'
    lista_html = '<div class="grade-playlists">' + cards + '</div>'
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
        '<span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
        '<span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Playlists') +
        '<button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
        '<header class="page-header">\n<div class="container">\n'
        '<span class="section-subtitle">Curadoria do selo</span>\n'
        '<h1 class="section-title">' + _grad_html(cfg_str('home_playlists_titulo', 'Playlists')) + '</h1>\n'
        '<p class="section-description">Seleções musicais que traduzem a alma da Por do Som — ouça no Spotify, YouTube ou Deezer.</p>\n'
        '</div>\n</header>\n'
        '<section style="padding:3rem 0">\n<div class="container">\n' + lista_html + '\n</div>\n</section>\n' + _footer() + _scripts())
    with open(os.path.join(BASE_DIR, 'playlists.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Playlists — Por do Som', 'Curadoria musical do selo Por do Som.', body))
    os.makedirs(os.path.join(BASE_DIR, 'playlists'), exist_ok=True)
    for _i, p in enumerate(playlists):
        slug = p.get('slug', slugify(p.get('titulo', 'playlist')))
        with open(os.path.join(BASE_DIR, 'playlists', slug + '.html'), 'w', encoding='utf-8') as f:
            f.write(page_playlist(p, playlists[_i - 1] if _i > 0 else None, playlists[_i + 1] if _i < len(playlists) - 1 else None))
    print('✔ playlists.html + ' + str(len(playlists)) + ' páginas de playlist geradas')


# ---------- Página Sérgio Mendonça (fundador) ----------
def gera_sergio():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    nome = cfg_str('sergio_nome', 'Sérgio Mendonça')
    role = cfg_str('sergio_role', 'Fundador e Diretor Artístico')
    bio = cfg_str('sergio_bio_curta')
    curriculo = cfg_str('sergio_curriculo')
    foto = cfg_str('sergio_foto')
    foto_src = (BASE + foto) if foto.startswith('/') else foto
    foto_html = ('<div class="sergio-foto"><img src="' + esc(foto_src) + '" alt="' + esc(nome) + '" loading="lazy"></div>') if foto_src else ''
    curriculo_html = md_html_v2(curriculo) if curriculo else '<p style="color:var(--text-muted);text-align:center;font-style:italic">Currículo em breve.</p>'
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/site.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Quem Somos') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<main class="album-page">\n<div class="container">\n'
            '        <div class="sergio-hero">\n' + foto_html + '<div>\n'
            '            <span class="album-kicker">' + esc(role) + '</span>\n'
            '            <h1 class="album-titulo-grande">' + esc(nome) + '</h1>\n'
            + (('<div class="album-descricao" style="font-style:italic">' + esc(bio) + '</div>') if bio else '') +
            '        </div>\n</div>\n'
            '        <div class="sergio-curriculo">' + curriculo_html + '</div>\n'
            '        <div class="album-navegacao">\n'
            '            <a class="album-nav-link" href="' + BASE + '/site.html#quemsomos">← Voltar para Quem Somos</a>\n'
            '            <a class="album-nav-link" href="' + BASE + '/site.html#contato">Fale com o selo →</a>\n'
            '        </div>\n'
            '</div>\n</main>\n' + _footer() + _scripts())
    with open(os.path.join(BASE_DIR, 'sergio-mendonca.html'), 'w', encoding='utf-8') as f:
        f.write(_doc(nome + ' — ' + role, (bio[:155] if bio else 'Trajetória do fundador do selo Por do Som.'), body, img_og=(foto_src or None)))
    print('✔ sergio-mendonca.html gerada')


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
                 'slug': slugify(p.get('title','post'))} for p in posts]
    projetos_js = [{'slug': p['slug'], 'titulo': str(p.get('titulo','')), 'status': str(p.get('status','')),
                    'ano': str(p.get('ano','')), 'badge': str(p.get('badge',''))} for p in projetos]
    playlists_js = [{'slug': p.get('slug', slugify(p.get('titulo','playlist'))), 'titulo': str(p.get('titulo','')),
                     'plataforma': str(p.get('plataforma','spotify') or 'spotify'),
                     'embed_id': str(p.get('embed_id','') or ''), 'capa': str(p.get('capa','') or ''),
                     'descricao_curta': str(p.get('descricao_curta','') or ''),
                     'destaque': bool(p.get('destaque'))} for p in playlists]
    cat = {'base': BASE,
           'generos': [{'id': k, 'nome': v} for k, v in GENEROS.items()],
           'albuns': [_n(a) for a in albuns],
           'posts': posts_js,
           'projetos': projetos_js,
           'playlists': playlists_js,
           'artistas': artistas_js}
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
    with open(os.path.join(BASE_DIR, 'data', 'catalogo.json'), 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print('OK catalogo.json (' + str(len(albuns)) + ' albuns, ' + str(len(posts_js)) + ' posts, ' + str(len(artistas_js)) + ' artistas, ' + str(len(projetos_js)) + ' projetos, ' + str(len(playlists_js)) + ' playlists)')

def gera_albuns():
    os.makedirs(os.path.join(BASE_DIR, 'albuns'), exist_ok=True)
    for i, a in enumerate(albuns):
        prev = albuns[i-1] if i > 0 else None
        nxt = albuns[i+1] if i < len(albuns)-1 else None
        with open(os.path.join(BASE_DIR, 'albuns', a['slug'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(page_album(a, prev, nxt))
    print('✔ ' + str(len(albuns)) + ' páginas de álbum geradas')

# ---------- Página individual de projeto (matéria completa) ----------
def page_projeto(p, prev=None, next_=None):
    """Página individual do projeto — matéria completa (corpo rico)."""
    st = str(p.get('status','realizado'))
    st_cls = 'realizado' if st != 'captacao' else 'captacao'
    st_lbl = '✓ Realizado' if st != 'captacao' else '★ Em captação'
    img = str(p.get('imagem','') or '')
    img_src = (BASE + img) if img.startswith('/') else img
    link = str(p.get('link','') or '')
    rel = str(p.get('relatorio','') or '')
    ano = str(p.get('ano','') or '')
    badge = str(p.get('badge','') or '')
    tags = p.get('tags', [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    tags_html = ''.join('<span class="project-tag" style="margin-right:.4rem">' + esc(t) + '</span>' for t in tags)
    botoes = ''
    if link and link != '#':
        botoes += '<a class="btn btn-primary" style="text-decoration:none" href="' + esc(link) + '" target="_blank" rel="noopener">Ver online →</a>'
    if rel:
        botoes += '<a class="btn btn-outline" style="text-decoration:none" href="' + esc(rel) + '" target="_blank" rel="noopener">📄 Relatório</a>'
    meta_linha = ' · '.join(x for x in [badge, ano] if x)
    cab = ('<div style="max-width:760px;margin:0 auto">'
        '<span class="projeto-badge ' + st_cls + '" style="display:inline-block;margin-bottom:1rem">' + st_lbl + '</span>'
        + (('<span class="album-kicker" style="margin-left:1rem">' + esc(meta_linha) + '</span>') if meta_linha else '')
        + '<h1 class="album-titulo-grande" style="font-size:clamp(1.6rem,4vw,2.4rem)">' + esc(p.get('titulo','')) + '</h1>'
        + (('<div class="album-meta-info">' + tags_html + '</div>') if tags_html else '')
        + '</div>')
    fig = (('<figure style="margin:2rem auto;max-width:900px"><img src="' + esc(img_src) + '" alt="' + esc(p.get('titulo','')) + '" style="width:100%;border-radius:4px" loading="lazy"></figure>') if img_src else '')
    rod = (('<div style="margin-top:2.5rem;display:flex;flex-wrap:wrap;gap:.6rem">' + botoes + '</div>') if botoes else '')
    prev_h = ('<a class="album-nav-link" href="' + BASE + '/projetos/' + prev['slug'] + '.html">&#8592; ' + esc(prev.get('titulo',''))[:40] + '</a>') if prev else '<span></span>'
    next_h = ('<a class="album-nav-link" href="' + BASE + '/projetos/' + next_['slug'] + '.html">' + esc(next_.get('titulo',''))[:40] + ' &#8594;</a>') if next_ else '<span></span>'
    share_html = _share(DOMINIO + BASE + '/projetos/' + p['slug'] + '.html')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/index.html" class="logo">\n'
        '<span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
        '<span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Projetos') +
        '<button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
        '<main class="album-page">\n<div class="container">\n'
        + cab + fig +
        '<div style="max-width:760px;margin:0 auto;font-size:.98rem;line-height:1.9;color:var(--text-secondary)">'
        + md_html_v2(p.get('corpo','')) + rod + share_html +
        '<div class="album-navegacao">\n' + prev_h + '\n'
        '<a class="album-nav-link" href="' + BASE + '/projetos.html">Todos os projetos</a>\n' + next_h + '\n</div>\n'
        '</div>\n</div>\n</main>\n' + _footer() + _scripts())
    return _doc(p.get('titulo','Projeto'), str(p.get('corpo',''))[:155], body, img_og=(img_src or None))

# ---------- Página de projetos (lista) + páginas individuais ----------
def gera_projetos():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    realizados = [p for p in projetos if str(p.get('status', 'realizado')) != 'captacao']
    captacao = [p for p in projetos if str(p.get('status', 'realizado')) == 'captacao']
    html_realizados = '<div class="grade-projetos">' + ''.join(_card_projeto(p) for p in realizados) + '</div>'
    html_captacao = ''
    if captacao:
        html_captacao = ('<h2 class="section-title" style="font-size:1.2rem;margin:3rem 0 1.5rem;text-align:left">'
                         '★ Em captação — disponíveis para leis de incentivo</h2>\n'
                         '<div class="grade-projetos">' + ''.join(_card_projeto(p) for p in captacao) + '</div>')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/index.html" class="logo">\n'
        '<span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
        '<span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Projetos') +
        '<button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
        '<header class="page-header">\n<div class="container">\n'
        '<span class="section-subtitle">Projetos & Festivais</span>\n'
        '<h1 class="section-title">' + _grad_html(cfg_str('projetos_titulo')) + '</h1>\n'
        '<p class="section-description">' + esc(cfg_str('projetos_descricao')) + '</p>\n'
        '</div>\n</header>\n'
        '<section style="padding:3rem 0">\n<div class="container">\n'
        + html_realizados + html_captacao + '\n</div>\n</section>\n' + _footer() + _scripts())
    with open(os.path.join(BASE_DIR, 'projetos.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Projetos & Festivais', cfg_str('projetos_descricao')[:155], body))
    os.makedirs(os.path.join(BASE_DIR, 'projetos'), exist_ok=True)
    for _i, p in enumerate(projetos):
        slug = p.get('slug', slugify(p.get('titulo', 'projeto')))
        with open(os.path.join(BASE_DIR, 'projetos', slug + '.html'), 'w', encoding='utf-8') as f:
            f.write(page_projeto(p, projetos[_i - 1] if _i > 0 else None, projetos[_i + 1] if _i < len(projetos) - 1 else None))
    print('✔ projetos.html + ' + str(len(projetos)) + ' páginas de projeto geradas')


def gera_robots():
    txt = "User-agent: *\nAllow: /\nSitemap: " + DOMINIO + BASE + "/sitemap.xml\n"
    with open(os.path.join(BASE_DIR, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print('✔ robots.txt gerado')

def gera_sitemap():
    total_pag = max(1, (len(posts) + NOTICIAS_POR_PAGINA - 1) // NOTICIAS_POR_PAGINA) if posts else 1
    urls_noticias = [DOMINIO + '/noticias.html'] + [DOMINIO + '/noticias-' + str(n) + '.html' for n in range(2, total_pag + 1)]
    urls = [DOMINIO + '/site.html'] + [DOMINIO + '/albuns/' + a['slug'] + '.html' for a in albuns] + \
           [DOMINIO + '/posts/' + slugify(p.get('title','')) + '.html' for p in posts] + \
           [DOMINIO + '/projetos/' + p['slug'] + '.html' for p in projetos] + \
           urls_noticias + \
           [DOMINIO + '/playlists.html'] + [DOMINIO + '/playlists/' + p.get('slug', slugify(p.get('titulo','playlist'))) + '.html' for p in playlists] + \
           [DOMINIO + '/sergio-mendonca.html']
    hoje = datetime.now().strftime('%Y-%m-%d')
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += '  <url><loc>' + u + '</loc><lastmod>' + hoje + '</lastmod></url>\n'
    sm += '</urlset>\n'
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sm)
    print('✔ sitemap.xml (' + str(len(urls)) + ' URLs)')


# ---------- JS para páginas de dados (catálogo, etc.) ----------
def _js_dados():
    """JS reutilizável: filtros do catálogo + grade de artistas."""
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
            '  CAT.albuns.sort((x,y)=>{const ox=parseInt(x.ordem)||0,oy=parseInt(y.ordem)||0;if(ox&&oy)return ox-oy;if(ox)return -1;if(oy)return 1;return String(y.ano||"").localeCompare(String(x.ano||""))});\n'
            '  const filtrosEl = document.getElementById("filtros");\n'
            '  const grid = document.getElementById("catalogo-grid");\n'
            '  if (filtrosEl && grid) {\n'
            '    const contagem = { todos: CAT.albuns.length };\n'
            '    CAT.generos.forEach(g => { contagem[g.id] = CAT.albuns.filter(a=>a.generos.includes(g.id)).length });\n'
            '    filtrosEl.innerHTML = `<button class="filtro ativo" data-g="todos">Todos <span class="count">${contagem.todos}</span></button>` +\n'
            '      CAT.generos.map(g=>`<button class="filtro" data-g="${g.id}">${g.nome} <span class="count">${contagem[g.id]||0}</span></button>`).join("");\n'
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

# ---------- Página do catálogo completo ----------
def gera_catalogo():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    filtros_js = ('<div class="filtros" id="filtros"></div>\n<div class="catalogo-grid" id="catalogo-grid"></div>')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/index.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Gravadora') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n<div class="container">\n'
            '        <span class="section-subtitle">Gravadora</span>\n'
            '        <h1 class="section-title">' + _grad_html(cfg_str('grav_titulo')) + '</h1>\n'
            '        <p class="section-description">' + esc(cfg_str('grav_descricao')) + '</p>\n'
            '    </div>\n</header>\n'
            '<section style="padding-top:2rem">\n<div class="container">\n' + filtros_js + '\n'
            '    </div>\n</section>\n'
            '<section class="teaser teaser-alt" style="padding-top:2rem">\n<div class="container">\n'
            '        <div class="teaser-head">\n'
            '            <span class="section-subtitle">Gravadora</span>\n'
            '            <h2 class="section-title">' + _grad_html(cfg_str('artistas_titulo')) + '</h2>\n'
            '            <p class="section-description">' + esc(cfg_str('artistas_descricao')) + '</p>\n'
            '        </div>\n<div class="artistas-grid" id="artistas-grid"></div>\n'
            '    </div>\n</section>\n' + _footer() + _scripts() + _js_dados())
    with open(os.path.join(BASE_DIR, 'catalogo.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Gravadora — Catálogo & Artistas', cfg_str('grav_descricao')[:155], body))
    print('✔ catalogo.html gerada (catálogo completo + artistas)')

# ---------- Página audiovisual completa ----------
def gera_audiovisual():
    global ATUAL_EH_HOME
    ATUAL_EH_HOME = False
    grupos_html = []
    for gid, gname in GRUPOS_AV.items():
        do_g = [c for c in clips if str(c.get('grupo')) == gid]
        if not do_g: continue
        vids = '\n'.join('            <iframe src="https://www.youtube.com/embed/' + str(c.get('yt_id','')) +
                         '" loading="lazy" allowfullscreen title="' + esc(c.get('titulo','')) + '"></iframe>' for c in do_g)
        grupos_html.append('<h2 class="section-title" style="font-size:1.3rem;margin-top:3rem">' + esc(gname) + '</h2>\n'
                           '<div class="teaser-videos">\n' + vids + '\n</div>')
    p1id = _sp_id(cfg_str('playlist1_id', '2lgoPMSE9e7lxEumGbBaGn'))
    p2id = _sp_id(cfg_str('playlist2_id', '2cyXUj8Qhe3nZ0rbng87nR'))
    playlists = ('<section class="teaser teaser-alt">\n<div class="container">\n'
                 '        <div class="teaser-head">\n'
                 '            <span class="section-subtitle">Playlists</span>\n'
                 '            <h2 class="section-title">' + _grad_html(cfg_str('playlists_titulo', 'Curadoria do selo')) + '</h2>\n'
                 '        </div>\n<div class="teaser-playlists">\n'
                 '            <iframe src="https://open.spotify.com/embed/playlist/' + p1id + '?utm_source=generator" height="380" style="width:100%;border-radius:12px;border:none" loading="lazy" title="Playlist 1"></iframe>\n'
                 '            <iframe src="https://open.spotify.com/embed/playlist/' + p2id + '?utm_source=generator" height="380" style="width:100%;border-radius:12px;border:none" loading="lazy" title="Playlist 2"></iframe>\n'
                 '        </div>\n</div>\n</section>\n')
    body = ('<header class="header" id="header">\n<a href="' + BASE + '/index.html" class="logo">\n'
            '        <span class="logo-mark"><img src="' + BASE + '/pordosom-profile.jpg" alt="Por do Som"></span>\n'
            '        <span class="logo-text">PÔR DO SOM</span>\n</a>\n' + _nav('Audiovisual') +
            '    <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>\n</header>\n'
            '<header class="page-header">\n<div class="container">\n'
            '        <span class="section-subtitle">Audiovisual</span>\n'
            '        <h1 class="section-title">' + _grad_html(cfg_str('audio_titulo')) + '</h1>\n'
            '        <p class="section-description">' + esc(cfg_str('audio_descricao')) + '</p>\n'
            '    </div>\n</header>\n'
            '<section style="padding-top:2rem">\n<div class="container">\n'
            + '\n'.join(grupos_html) + '\n</div>\n</section>\n' + playlists + '\n' + _footer() + _scripts())
    with open(os.path.join(BASE_DIR, 'audiovisual.html'), 'w', encoding='utf-8') as f:
        f.write(_doc('Audiovisual & Playlists', cfg_str('audio_descricao')[:155], body))
    print('✔ audiovisual.html gerada (' + str(len(clips)) + ' vídeos em ' + str(len(grupos_html)) + ' grupos)')

# ---------- MAIN ----------
if __name__ == '__main__':
    gera_site()
    gera_catalogo()
    gera_audiovisual()
    gera_projetos()
    gera_playlists()
    gera_sergio()
    gera_albuns()
    gera_noticias()
    gera_posts()
    gera_json()
    gera_robots()
    gera_sitemap()
    print('\n🎉 RENDER v6 COMPLETO — uma fonte (content/), um autor (render.py)')
