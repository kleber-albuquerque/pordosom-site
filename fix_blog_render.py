path = "render.py"
src = open(path, encoding="utf-8").read()

# 1. Ler posts no inicio (depois da leitura dos albuns)
old1 = "albuns.sort(key=lambda a: (str(a.get('ano', '')), a['titulo']), reverse=True)"
new1 = old1 + '''

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
posts.sort(key=lambda p: str(p.get('date', '')), reverse=True)'''
if old1 in src and 'PASTA_POSTS' not in src:
    src = src.replace(old1, new1, 1)

# 2. Gerar blog.html (antes do relatorio final)
old2 = "print('✔ ' + str(len(geradas)) + ' páginas de álbum geradas"
new2 = '''# ---------- Gera o blog.html ----------
if posts:
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
    corpo_posts = '\\n\\n'.join(
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
    blog_html = BLOG_TEMPLATE.replace('<!-- POSTS LISTA -->', '\\n'.join(itens)).replace('<!-- POSTS CORPO -->', corpo_posts)
    with open(os.path.join(BASE_DIR, 'blog.html'), 'w', encoding='utf-8') as f:
        f.write(blog_html)
    print('✔ blog.html gerado com ' + str(len(posts)) + ' notícias')

''' + old2

if 'BLOG_TEMPLATE' not in src and old2 in src:
    # insere o template do blog antes da geracao
    template = '''
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
'''
    # substitui BASE pelo valor real no template gerado (por seguranca, via replace em runtime)
    src = src.replace('# ---------- Gera as páginas ----------',
                      template.replace('"""<!DOCTYPE', 'BLOG_TPL_RAW = """<!DOCTYPE').split('=')[0] + '= ' + '"""<!DOCTYPE' if False else template,
                      1)
    # simplificacao: aplica o replace de BASE na geracao
    src = src.replace("blog_html = BLOG_TEMPLATE.replace('<!-- POSTS LISTA -->'",
                      "blog_html = BLOG_TEMPLATE.replace('BASE', BASE).replace('<!-- POSTS LISTA -->'")
    src = src.replace(old2, new2, 1)

open(path, "w", encoding="utf-8").write(src)
print("render.py: blog gerado — valide com python3 render.py")
