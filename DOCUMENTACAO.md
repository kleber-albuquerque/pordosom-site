KA STUDIO — DOCUMENTAÇÃO TÉCNICA COMPLETA
Projeto: Site Selo Pôr do Som (primeiro cliente — modelo replicável)
ARQUITETURA (o princípio fundamental)
content/*.md  (FONTE ÚNICA — toda a verdade do site)     │     ▼  python3 render.py (o ÚNICO autor do HTML)     │index.html (site inteiro, seções por âncoras)albuns/*.html (páginas individuais — SEO/deep-link)posts/*.html (notícias)data/catalogo.json (alimenta JS embutido)sitemap.xml     │     ▼  git push → GitHub Actions → Pages (~2 min)admin/index.html (painel) → GitHub API → escreve em content/*.md
REGRA DE OURO: nunca editar HTML à mão. Tudo nasce do content/.

ESTRUTURA DE ARQUIVOS (entrega ao cliente)
pordosom-site/├── index.html          ← o site inteiro (GERADO — não editar)├── albuns/*.html       ← 31 páginas de álbum (GERADAS)├── posts/*.html        ← páginas de notícias (GERADAS)├── css/style.css       ← estilos (1643 linhas, identidade do selo)├── data/catalogo.json ← dados para o JS (GERADO)├── images/uploads/     ← capas e imagens (via painel, comprimidas)├── img/                ← imagens institucionais (hero, projetos)├── content/            ← A FONTE (editável pelo painel ou direto)│   ├── albuns/*.md     ← 31 obras│   ├── posts/*.md      ← notícias│   ├── projetos/*.md   ← com status realizado/captação│   ├── audiovisual/*.md← 42 clips por grupo│   └── config/site.md  ← TODOS os textos institucionais├── render.py           ← o gerador (~600 linhas)├── sitemap.xml         ← GERADO└── admin/index.html    ← o painel do cliente└── .github/workflows/render.yml ← CI/CD
O RENDER.PY (o coração)
Lê TODO o content/ e gera TODO o HTML. Funcões principais:

parse_md(): frontmatter YAML + corpo
gera_site(): index.html com 11 seções por âncoras (hero, notícias,gravadora, artistas, projetos, audiovisual, playlists, manifesto,quem-somos, editora, contato) + JS embutido (vitrine, filtros, banner)
page_album(): página individual com Schema.org MusicAlbum (SEO)
gera_posts(): páginas de notícia com markdown→HTML
gera_json(): catalogo.json (nasce normalizado: capa string, generos array)
gera_sitemap()
⚠️ REGRA DA BASE (migração para domínio próprio):BASE = '/pordosom-site' no render.py → trocar por '' quando o domíniopróprio apontar. É o ÚNICO lugar (o JS embutido herda do JSON).

O PAINEL (admin/index.html)
Autenticação: token GitHub do cliente (fine-grained, escopo Contentsread/write no repo). Sem servidor, sem mensalidade.

Abas e o que editam:

Álbuns: CRUD completo + capas + destaque + posição + ordenação por coluna
Notícias: CRUD + imagens + rascunho + markdown com barra (B/I/H2/link)
Projetos: CRUD + status captação + relatório
Audiovisual: CRUD + preview YouTube ao colar link
Configurações: TODOS os textos do site (site.md) + logo + hero + playlists
Blindagens implementadas (herança da saga de bugs):

comprimirImagem(): Canvas API — imagens ≤500KB antes do upload
Normalização universal no parse (capa-lista→string, generos-string→array)
salvarAlbum: body explícito, sha só na edição (não na criação)
FORMATO DOS .md (a fonte)
Álbum (content/albuns/slug.md)
---titulo: "Nome"artista: "Nome"ano: 2024capa: "/images/uploads/arquivo.jpg"generos:  - mpbdestaque: true|falseordem: 1|""      ← número fixa no topo do catálogospotify: "url"youtube: "url"apple: "url"deezer: "url"texto_en: "versão inglês (opcional)"---Texto em português (corpo)
Notícia (content/posts/AAAA-MM-DD-slug.md)
title, date, resumo, rascunho (true/false), imagemcorpo com **negrito**, ## subtítulo, [link](url), *itálico*
Projeto (content/projetos/slug.md)
titulo, status (realizado|captacao), badge, ano, imagem, link,relatorio, tags (lista)
Clip (content/audiovisual/slug.md)
titulo, grupo (sotaques|malungo|mestres|outros), ano, artista, yt_id
Config (content/config/site.md) — 30+ campos
hero_slogan, hero_texto, grav_titulo, grav_descricao,artistas_titulo, projetos_titulo, audio_titulo, noticias_titulo,contato_titulo, manifesto_texto1-3, quemsomos_texto, editora_texto,portfolio_link, email_contato, whatsapp_contato,playlist1_nome/id, playlist2_nome/id, ...
SEGURANÇA
Token: localStorage do navegador do cliente, fine-grained GitHub
Sem segredos no repo (público = só conteúdo)
XSS: esc() em todo conteúdo no render; innerHTML do painel só comdados do próprio repo
LIÇÕES DE ARQUITETURA (para replicar em próximos clientes)
UMA fonte de verdade (content/) — HTML à mão diverge e quebra
Geração > injeção — regex em HTML é frágil por natureza
Normalizar dados na geração E no consumo (blindagem dupla)
Verificação de integridade antes de todo commit (tail + grep)
Cache-busting em JSON/CSS (?v=)
Commit logo após edição — pull antes de trabalhar
Arquivos grandes: blocos cat de ~30 linhas (terminal embaralha >40)
CHECKLIST DE REPLICAÇÃO (próximo cliente)
Fork da estrutura: content/ + render.py + admin/ + css/
Trocar: BASE, logo, cores (css :root --brand-*), GENEROS do cliente
Criar repo do cliente + Pages com Source: GitHub Actions
Token fine-grained do cliente (Contents read/write)
Render local → commit → primeiro deploy
Treinamento: painel + guia do token
FERRAMENTAS DO TOOLBOX (fora do repo do cliente)
../toolbox-ka/:

gerador_lote.py: lista "titulo|artista|ano|genero|link" → .md em massa
gerador_clips.py: idem para clips do YouTube
gera_posts.py: páginas individuais de notícia
baixador_capas.py: URLs→imagens otimizadas em images/uploads/
lote/: as listas de pesquisa (agentes IA)
