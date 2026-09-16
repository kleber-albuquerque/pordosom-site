KA STUDIO — DOCUMENTAÇÃO TÉCNICA COMPLETA v2.0
Projeto: Site Selo Pôr do Som (primeiro cliente — modelo replicável)
Atualizado em: [DATA] — pós-arquitetura v5 consolidada

ARQUITETURA (o princípio fundamental)
content/*.md  (FONTE ÚNICA — toda a verdade do site)     │     ▼  python3 render.py v5 (o ÚNICO autor do HTML)     │index.html (home curta: hero + teasers com "ver tudo")catalogo.html (catálogo completo + artistas)audiovisual.html (42 vídeos + playlists)albuns/*.html (31 páginas individuais — SEO/deep-link)posts/*.html (notícias)data/catalogo.json (albuns + posts + artistas)sitemap.xml     │     ▼  git push → GitHub Actions → Pages (~2 min)admin/index.html (painel) → GitHub API → escreve em content/*.md
REGRA DE OURO: nunca editar HTML à mão. Tudo nasce do content/.Editar HTML à mão quebra a sincronização com o site.md — causa raizde todos os bugs da fase v1-v4.

ESTRUTURA DE ARQUIVOS (entrega ao cliente)
pordosom-site/├── index.html          ← HOME CURTA (gerada — não editar)├── catalogo.html      ← catálogo completo + artistas (GERADA)├── audiovisual.html   ← 42 vídeos + playlists (GERADA)├── albuns/*.html      ← 31 páginas de álbum (GERADAS)├── posts/*.html       ← páginas de notícias (GERADAS)├── css/style.css      ← identidade visual (terracota + efeito)├── data/catalogo.json ← dados para o JS (GERADO)├── images/uploads/    ← capas e imagens (via painel, comprimidas)├── img/               ← imagens institucionais├── content/           ← A FONTE (editável pelo painel)│   ├── albuns/*.md     ← 31 obras│   ├── posts/*.md      ← notícias│   ├── projetos/*.md   ← 3 projetos (realizado/captação)│   ├── audiovisual/*.md← 42 clips por grupo│   ├── artistas/*.md   ← 10 artistas do selo│   └── config/site.md  ← TODOS os textos institucionais├── render.py          ← o gerador v5 (~650 linhas)├── sitemap.xml        ← GERADO├── admin/index.html   ← o painel do cliente├── DOCUMENTACAO.md    ← este arquivo└── .github/workflows/render.yml ← CI/CD
O RENDER.PY v5 (o coração)
Lê TODO o content/ e gera TODO o HTML. Funções principais:

parse_md(): frontmatter YAML + corpo
gera_site(): index.html — HOME CURTA com:
Hero (slogan+texto do site.md)
Banner da última notícia (JS lê catalogo.json)
Vitrine de 6 capas + botão "Ver catálogo completo"
3 projetos (cards) + 4 vídeos + playlists
Manifesto, Quem Somos, Editora, Contato (do site.md)
JS embutido: efeito visual + banner + menu mobile
gera_catalogo(): catálogo completo com filtros + SEÇÃO ARTISTAS
gera_audiovisual(): 42 vídeos por grupo + playlists
page_album(): página individual com Schema.org MusicAlbum
gera_posts(): páginas de notícia (markdown→HTML)
gera_json(): catalogo.json (albuns + posts + ARTISTAS)
gera_sitemap()
⚠️ REGRA DA BASE (domínio próprio):BASE = '/pordosom-site' no render.py → trocar por '' quando odomínio próprio apontar. ÚNICO lugar (o JS herda do JSON).

EFEITO VISUAL — ASSINATURA KA (assinatura de marca)
Todas as páginas têm o mesmo fundo:

Canvas com 3 ondas circulares discretas e fluidas (terracota)
Glow central sutil + glow que segue o mouse
Ondas âmbar no clique (ripples)
Grain cinematográfico por cima
Herança: mesmo efeito do assistente.html (KA Vox)
Implementado no _scripts() do render.py — é herança, não arquivo externo.

O PAINEL (admin/index.html)
Autenticação: token GitHub fine-grained (Contents read/write do repo).Sem servidor, sem mensalidade.

ABAS (todas funcionais):
Álbuns: CRUD + capas + destaque + posição + ordenação por coluna
Notícias: CRUD + imagens + rascunho + markdown (B/I/H2/link)
Projetos: CRUD + status captação + relatório
Audiovisual: CRUD + preview do YouTube ao colar link
Configurações: 10 seções espelhando o site (ver abaixo)
CONFIGURAÇÕES — espelho exato do site:
Item do painel	Controla	Onde aparece
1 · Hero	slogan + texto	Home topo
2 · Gravadora	título + descrição	Home + catalogo.html
3 · Artistas	título + descrição	catalogo.html (abaixo do catálogo)
4 · Projetos	título + descrição	Home
5 · Audiovisual	título + descrição	Home + audiovisual.html
6 · Playlists	título + 2 IDs	Home + audiovisual.html
7 · Manifesto	3 parágrafos	Home
8 · Quem Somos	currículo + portfolio	Home
9 · Editora	texto	Home
10 · Contato	título + email + WhatsApp	Home
Logo do selo + imagem do hero (upload com compressão)
BLINDAGENS (herança da saga):
comprimirImagem(): Canvas API (≤500KB antes do upload)
Normalização universal no parse (capa-lista→string etc.)
salvarAlbum: body explícito, sha só na edição
Cache-busting no fetch do JSON (?v=Date.now())
FORMATO DOS .md (a fonte)
Álbum (content/albuns/slug.md)
---titulo, artista, ano, capa, generos (lista),destaque (bool), ordem (número fixa no topo),spotify, youtube, apple, deezer, texto_en---Texto PT (corpo)
Notícia (content/posts/AAAA-MM-DD-slug.md)
title, date, resumo, rascunho, imagemcorpo: **negrito**, ## subtítulo, [link](url), *itálico*
Projeto (content/projetos/slug.md)
titulo, status (realizado|captacao), badge, ano,imagem, link, relatorio, tags (lista)
Clip (content/audiovisual/slug.md)
titulo, grupo (sotaques|malungo|mestres|outros), ano, artista, yt_id
Artista (content/artistas/slug.md) — NOVO
nome, role, img(corpo: descrição — uso futuro)
Config (content/config/site.md) — os 25+ campos das 10 seções
SEGURANÇA
Token: localStorage do cliente, fine-grained GitHub
Zero segredos no repo (público = só conteúdo)
XSS: esc() em todo conteúdo no render
NAVEGAÇÃO (o modelo one-page + aprofundamento)
HOME (scroll rápido):hero → notícia → vitrine(6) → projetos(3) → vídeos(4)→ playlists → manifesto → quem somos → editora → contatoAPROFUNDAMENTO (botões "ver tudo"):catalogo.html (catálogo+filtros+artistas)audiovisual.html (42 vídeos+playlists)albuns/*.html (deep-link, SEO)posts/*.html (notícias)Menu da home: âncoras para as seções do próprio scroll.
LIÇÕES DE ARQUITETURA (para replicar)
UMA fonte de verdade (content/) — HTML à mão diverge
Geração > injeção — regex em HTML é frágil por natureza
Campos do painel = campos do render (mesmas chaves, sempre)
Normalizar dados na geração E no consumo
Verificação de integridade antes de todo commit (tail + grep)
Cache-busting em JSON (?v=)
Commit logo após edição — pull antes de trabalhar
Arquivos grandes: kwrite method ou blocos cat ~30 linhas(terminal embaralha pastes >40 linhas)
Replace por função INTEIRA (estrutural) > replace de trecho (frágil)
CHECKLIST DE REPLICAÇÃO (próximo cliente)
Copiar template (~/KA_PROJETOS/ka-studio-template/)
Trocar: BASE, logo, cores (css :root), GENEROS
Criar repo do cliente + Pages (Source: GitHub Actions)
Token fine-grained do cliente
Render local → commit → primeiro deploy
Treinamento: painel + guia do token
FERRAMENTAS DO TOOLBOX (~/KA_PROJETOS/toolbox-ka/)
gerador_lote.py: lista → .md de álbuns em massa
gerador_clips.py: idem para clips
gera_posts.py: páginas individuais de notícia
baixador_capas.py: URLs → imagens otimizadas
lote/: listas de pesquisa (agentes IA)
ESTADO DO PROJETO (nesta data)
Site: 100% funcional, home curta + páginas de aprofundamento
Painel: 5 abas completas, configurações espelhando o site
Conteúdo: 31 álbuns, 42 vídeos, 3 projetos, 10 artistas,1 notícia, textos institucionais todos editáveis
Deploy: GitHub Actions (render.py → Pages)
Mensalidade do cliente: R$ 0 (promessa cumprida)
PENDÊNCIAS DE ENTREGA (com o cliente)
Transferir repo (ou colaborador + trocar REPO no admin)
Domínio próprio (pordosom.com.br → Pages + BASE='')
Treinamento (1h + guia do token)
2ª parcela (R$ 2.750) na aprovação
Depoimento + case no portfólio KA

O PAINEL v6 (admin/index.html)
Autenticação: token GitHub fine-grained (Contents read/write do repo). Sem servidor, sem mensalidade.
ABAS (todas funcionais):
Álbuns: CRUD + capas + destaque + posição + ordenação por coluna
Notícias: CRUD + imagens + rascunho + toolbar de matéria rica (NOVO v6)
Projetos: CRUD + status captação + relatório + toolbar de matéria rica (NOVO v6)
Audiovisual: CRUD + preview do YouTube ao colar link
Configurações: 10 seções espelhando o site + campo hero_scroll_texto (NOVO v6)
TOOLBAR DE MATÉRIA RICA (NOVO v6):
Nos editores de Notícia e Projeto, botões que inserem markdown v2:
B / I: negrito / itálico
H2 / H3: subtítulos
🔗: link
🖼️: imagem com legenda + crédito → ![legenda / Crédito: Fulano](url)
▶: vídeo do YouTube (URL sozinha numa linha)
🎵: embed Spotify → {{spotify: url}}
❝: citação em bloco → > texto
Funções helper: mdImagem(), mdYoutube(), mdSpotify(), mdCitacao(), mdH3() — inserem o snippet na posição do cursor.
CONFIGURAÇÕES — espelho exato do site:
Item do painel
Controla
Onde aparece
1 · Hero
slogan + texto + hero_scroll_texto (NOVO v6)
Home topo
2 · Gravadora
título + descrição
Home + catalogo.html
3 · Artistas
título + descrição
catalogo.html (abaixo do catálogo)
4 · Projetos
título + descrição
Home
5 · Audiovisual
título + descrição
Home + audiovisual.html
6 · Playlists
título + 2 IDs
Home + audiovisual.html
7 · Manifesto
3 parágrafos
Home
8 · Quem Somos
currículo + portfolio
Home
9 · Editora
texto
Home
10 · Contato
título + email + WhatsApp
Home
Logo do selo + imagem do hero (upload com compressão)
RODAPÉ DO PAINEL:
Logo da KA Agência Criativa (linha 1729) — presença digital sem ruído. Herança de marca.
BLINDAGENS (herança da saga v1-v6)
comprimirImagem(): Canvas API (≤500KB antes do upload)
Normalização universal no parse (capa-lista→string etc.)
salvarAlbum: body explícito, sha só na edição
Cache-busting no fetch do JSON (?v=Date.now())
NOVO v6: global ATUAL_EH_HOME nas funções page_album, gera_posts, gera_projetos, gera_catalogo, gera_audiovisual — faz o menu das subpáginas usar site.html#ancora em vez de #ancora cru
FORMATO DOS .md (a fonte)

---
titulo, artista, ano, capa, generos (lista),
destaque (bool), ordem (número fixa no topo),
spotify, youtube, apple, deezer, texto_en
---
Texto PT (corpo) — NOVO v6: suporta md_html_v2 (figuras, embeds, citações)

Notícia (content/posts/AAAA-MM-DD-slug.md)
yaml
title, date, resumo, rascunho, imagem
corpo: **negrito**, ## subtítulo, [link](url), *itálico*
NOVO v6: suporta md_html_v2 (figuras com legenda+crédito, embeds YT/Spotify, citações, H3, tempo de leitura automático)
Projeto (content/projetos/slug.md)

(corpo: descrição — uso futuro)
Config (content/config/site.md) — os 25+ campos das 10 seções
NOVO v6: campo hero_scroll_texto (se vazio, remove "Role para descobrir")
SEGURANÇA
Token: localStorage do cliente, fine-grained GitHub
Zero segredos no repo (público = só conteúdo)
XSS: esc() em todo conteúdo no render
NAVEGAÇÃO (o modelo one-page + aprofundamento)
HOME (scroll rápido):
hero → notícia → vitrine(6) → projetos(1) → vídeos(4) → playlists → manifesto → quem somos → editora → contato
APROFUNDAMENTO (botões "ver tudo"):
catalogo.html (catálogo+filtros+artistas)
audiovisual.html (42 vídeos+playlists)
albuns/*.html (deep-link, SEO)
posts/*.html (notícias)
projetos.html + projetos/*.html (NOVO v6: matérias completas)
Menu da home: âncoras para as seções do próprio scroll.
Menu das subpáginas: site.html#ancora (graças ao global ATUAL_EH_HOME).
LIÇÕES DE ARQUITETURA (para replicar)
UMA fonte de verdade (content/) — HTML à mão diverge
Geração > injeção — regex em HTML é frágil por natureza
Campos do painel = campos do render (mesmas chaves, sempre)
Normalizar dados na geração E no consumo
Verificação de integridade antes de todo commit (tail + grep)
Cache-busting em JSON (?v=)
Commit logo após edição — pull antes de trabalhar
Arquivos grandes: kwrite method ou blocos cat ~30 linhas (terminal embaralha pastes >40 linhas)
Replace por função INTEIRA (estrutural) > replace de trecho (frágil)
NOVO v6: Branches para features — nunca commitar direto na main sem testar em branch primeiro
NOVO v6: force push em branch de feature é seguro (não afeta produção), mas perde commits remotos não-merged
NOVO v6: global em Python é necessário para modificar variáveis de escopo global dentro de funções (o bug do menu nas subpáginas)
NOVO v6: Ctrl+F não busca texto quebrado em múltiplas linhas — use grep de pedaços únicos ou override com !important no CSS
LIÇÕES ESPECÍFICAS DA V6 (matérias ricas + páginas de projeto)
Branch protege produção: o cliente edita conteúdo na main via painel enquanto você desenvolve features em feat/* — zero risco de quebrar o site no ar
Force push com cuidado: substitui o histórico remoto da branch. Se o remoto tem commits que você não tem localmente, eles se perdem (aconteceu com o CSS do hero no Commit 1 — tivemos que reaplicar)
Merge via Pull Request: mais seguro que merge local. O GitHub mostra o diff, permite review, e o botão Revert desfaz tudo em 1 clique se algo quebrar
Toolbar de matéria > HTML livre: o cliente escreve markdown simples (clica nos botões), o render converte em HTML formatado. Padroniza o visual e evita quebras de layout
Páginas individuais de projeto: deep-link para editais, parcerias, mídia. Cada projeto vira uma "matéria" completa com badge, foto, corpo rico, botões de link/relatório
Tempo de leitura automático: calcular_tempo_leitura() baseado em 200 palavras/min — aparece no kicker das notícias, melhora UX
Figuras com legenda+crédito: ![legenda / Crédito: Fulano](url) → <figure> semântico. Profissionaliza o conteúdo
Embeds automáticos: URL do YouTube sozinha numa linha → iframe responsivo. {{spotify: url}} → embed Spotify. Zero fricção para o cliente
Hero configurável: campo hero_scroll_texto no painel — se vazio, remove a frase; se preenchido, mostra. Flexibilidade sem mexer no código
CHECKLIST DE REPLICAÇÃO (próximo cliente)
Copiar template (~/KA_PROJETOS/ka-studio-template/)
Trocar: BASE, logo, cores (css :root), GENEROS
Criar repo do cliente + Pages (Source: GitHub Actions)
Token fine-grained do cliente
Render local → commit → primeiro deploy
Treinamento: painel + guia do token
NOVO v6: explicar a toolbar de matéria rica (🖼️ ▶ 🎵 ❝ H3) e o campo hero_scroll_texto
NOVO v6: mostrar como criar uma matéria completa (Notícia ou Projeto) com imagens, vídeos, citações
FERRAMENTAS DO TOOLBOX (~/KA_PROJETOS/toolbox-ka/)
gerador_lote.py: lista → .md de álbuns em massa
gerador_clips.py: idem para clips
gera_posts.py: páginas individuais de notícia
baixador_capas.py: URLs → imagens otimizadas
lote/: listas de pesquisa (agentes IA)
ESTADO DO PROJETO (nesta data: 17/09/2026)
Site: 100% funcional, home curta + páginas de aprofundamento + páginas de projeto com matérias completas (NOVO v6)
Painel: 5 abas completas, configurações espelhando o site + toolbar de matéria rica (NOVO v6) + campo hero_scroll_texto (NOVO v6)
Conteúdo: 28 álbuns, 42 vídeos, 3 projetos, 10 artistas, 1 notícia, textos institucionais todos editáveis
Deploy: GitHub Actions (render.py → Pages)
Mensalidade do cliente: R$ 0 (promessa cumprida)
MUDANÇAS DA V5 → V6 (changelog)
render.py
✅ md_html() → md_html_v2(): suporte a figuras com legenda+crédito, embeds YT/Spotify, citações, H3
✅ calcular_tempo_leitura(): 200 palavras/min, aparece no kicker das notícias
✅ page_projeto(): página individual de projeto com matéria completa
✅ gera_projetos(): agora gera projetos.html + projetos/*.html
✅ gera_json(): inclui projetos no catalogo.json
✅ gera_sitemap(): URLs de projetos
✅ Hero: hero_scroll_texto configurável (se vazio, remove a frase)
✅ global ATUAL_EH_HOME em 5 funções (fix do menu nas subpáginas)
✅ CSS: slogan do hero com clamp ajustado (3.5vw desktop, 2.5rem mobile)
Painel (admin/index.html)
✅ Campo hero_scroll_texto na seção 1 do Hero
✅ Toolbar de matéria rica nos editores de Notícia e Projeto (🖼️ ▶ 🎵 ❝ H3)
✅ Funções helper: mdImagem(), mdYoutube(), mdSpotify(), mdCitacao(), mdH3()
CSS (css/style.css)
✅ .hero-title: clamp(2.5rem, 3.5vw, 3.9rem) — slogan equilibrado no desktop, mobile intacto
Sitemap
✅ URLs de projetos adicionadas (de 30 para 33 URLs)
PENDÊNCIAS DE ENTREGA (com o cliente)
Transferir repo (ou colaborador + trocar REPO no admin)
Domínio próprio (pordosom.com.br → Pages + BASE='')
Treinamento (1h + guia do token)
2ª parcela (R$ 2.750) na aprovação
Depoimento + case no portfólio KA
NOVAS OPORTUNIDADES (pós-v6):
Upload de imagens de corpo no painel (além da capa) — melhoria de UX
Prêmios do portfolio na aba Quem Somos/Manifesto — conteúdo de ouro pra autoridade
Tradução automática de descrições de álbum (EN) — SEO internacional
