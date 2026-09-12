// ==========================================================
// POR DO SOM — catalogo.js v2 (consolidado e blindado)
// Vitrine · Gravadora (filtros+ordenação) · Audiovisual ·
// Artistas · Contato — com NORMALIZAÇÃO UNICA dos dados
// ==========================================================
(async function(){
  // ⚠️ REGRA DA BASE — mesma do render.py
  // GitHub Pages de projeto: '/pordosom-site' | Domínio próprio: ''
  const BASE = '/pordosom-site';

  // ---------- Carrega o catálogo ----------
  let CAT;
  try {
    const res = await fetch(BASE + '/data/catalogo.json');
    CAT = await res.json();
  } catch(e){ console.error('Falha ao carregar catálogo:', e); return; }

  // ==========================================================
  // NORMALIZAÇÃO ÚNICA — todo dado deformado morre AQUI.
  // Daqui pra frente: capa é string, generos é array. Sempre.
  // ==========================================================
  if (CAT.albuns) CAT.albuns.forEach(a => {
    // capa: array -> primeiro item; qualquer coisa -> string
    if (Array.isArray(a.capa)) a.capa = a.capa[0] || '';
    if (typeof a.capa !== 'string') a.capa = String(a.capa || '');
    // generos: string -> array limpo; qualquer coisa não-array -> []
    if (typeof a.generos === 'string') {
      a.generos = a.generos.replace(/[\[\]]/g, '').split(',')
        .map(s => s.trim()).filter(Boolean);
    }
    if (!Array.isArray(a.generos)) a.generos = [];
    // ano/ordem: garantem string comparável
    if (Array.isArray(a.ano)) a.ano = a.ano[0] || '';
    if (Array.isArray(a.ordem)) a.ordem = a.ordem[0] || '';
    if (typeof a.ano !== 'string' && typeof a.ano !== 'number') a.ano = '';
    if (typeof a.ordem !== 'string' && typeof a.ordem !== 'number') a.ordem = '';
    // titulo/artista nunca undefined (quebra template)
    if (!a.titulo) a.titulo = '';
    if (!a.artista) a.artista = '';
  });
  if (!CAT.generos) CAT.generos = [];
  if (!CAT.albuns) CAT.albuns = [];

  // ---------- Capa com BASE (helper único) ----------
  const capaSrc = c => (c && c.startsWith('/')) ? BASE + c : (c || '');
  const fallback = () =>
    'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 300 300%22%3E%3Crect fill=%22%231a0e0e%22 width=%22300%22 height=%22300%22/%3E%3Ccircle cx=%22150%22 cy=%22130%22 r=%2255%22 fill=%22%23a83030%22 opacity=%220.7%22/%3E%3C/svg%3E';

  // ---------- Ordenação: com ordem: primeiro; sem: ano desc ----------
  CAT.albuns.sort((x, y) => {
    const ox = parseInt(x.ordem) || 0, oy = parseInt(y.ordem) || 0;
    if (ox && oy) return ox - oy;
    if (ox) return -1;
    if (oy) return 1;
    return String(y.ano || '').localeCompare(String(x.ano || ''));
  });

  /* ==========================================================
     VITRINE DA HOME
     ========================================================== */
  const vitrine = document.getElementById('vitrine');
  if (vitrine) {
    const destaques = CAT.albuns.filter(a => a.destaque).slice(0, 6);
    vitrine.innerHTML = destaques.map(a => `
      <a href="${BASE}/albuns/${a.slug}.html" title="${a.titulo} — ${a.artista}">
        <img src="${capaSrc(a.capa)}" alt="Capa: ${a.titulo}" loading="lazy" onerror="this.src='${fallback()}'">
        <span class="vitrine-titulo">${a.titulo}</span>
      </a>`).join('');
  }

  /* ==========================================================
     GRAVADORA — filtros + grid
     ========================================================== */
  const filtrosEl = document.getElementById('filtros');
  const grid = document.getElementById('catalogo-grid');
  if (filtrosEl && grid) {
    const contagem = { todos: CAT.albuns.length };
    CAT.generos.forEach(g => {
      contagem[g.id] = CAT.albuns.filter(a => a.generos.includes(g.id)).length;
    });
    filtrosEl.innerHTML =
      `<button class="filtro ativo" data-g="todos">Todos <span class="count">${contagem.todos}</span></button>` +
      CAT.generos.filter(g => contagem[g.id] > 0).map(g =>
        `<button class="filtro" data-g="${g.id}">${g.nome} <span class="count">${contagem[g.id]}</span></button>`
      ).join('');

    const nomeG = id => (CAT.generos.find(g => g.id === id) || {}).nome || id;

    function renderGrid(g){
      const lista = (g === 'todos')
        ? CAT.albuns
        : CAT.albuns.filter(a => a.generos.includes(g));
      grid.innerHTML = lista.map(a => `
        <a class="album-card" href="${BASE}/albuns/${a.slug}.html">
          <div class="album-capa">
            <img src="${capaSrc(a.capa)}" alt="Capa: ${a.titulo}" loading="lazy" onerror="this.src='${fallback()}'">
          </div>
          <div class="album-info">
            <div class="album-titulo">${a.titulo}</div>
            <div class="album-artista">${a.artista}${a.ano ? ' · ' + a.ano : ''}</div>
            <div class="album-tags">${a.generos.map(g => `<span class="album-tag">${nomeG(g)}</span>`).join('')}</div>
          </div>
        </a>`).join('') ||
        '<p style="grid-column:1/-1;text-align:center;color:var(--text-muted)">Nenhum álbum neste gênero ainda.</p>';
    }
    function ativar(g, url=true){
      filtrosEl.querySelectorAll('.filtro').forEach(b => b.classList.toggle('ativo', b.dataset.g === g));
      renderGrid(g);
      if (url) history.replaceState(null, '', g === 'todos' ? '?' : '?g=' + g);
    }
    filtrosEl.addEventListener('click', e => {
      const b = e.target.closest('.filtro'); if (b) ativar(b.dataset.g);
    });
    const gURL = new URLSearchParams(location.search).get('g');
    ativar(gURL && contagem[gURL] !== undefined ? gURL : 'todos', false);
  }

  /* ==========================================================
     AUDIOVISUAL — playlists
     ========================================================== */
  const pls = document.getElementById('playlists-grid');
  if (pls && Array.isArray(CAT.playlists)) {
    pls.innerHTML = CAT.playlists.map(p => `
      <iframe src="${p.embed}" height="380" loading="lazy"
              title="Playlist: ${p.nome || ''}"></iframe>`).join('');
  }

  /* ==========================================================
     QUEM SOMOS — artistas
     ========================================================== */
  const artGrid = document.getElementById('artistas-grid');
  if (artGrid && Array.isArray(CAT.artistas)) {
    artGrid.innerHTML = CAT.artistas.map(a => {
      const inicial = (a.nome || '?').trim()[0].toUpperCase();
      return `
      <div class="artist-card fade-in">
        <div class="artist-card-img" style="background-image: url('${a.img || ''}')"></div>
        <div class="artist-card-overlay"></div>
        <div class="artist-card-content">
          <div class="artist-initial">${inicial}</div>
          <div class="artist-name">${a.nome}</div>
          <div class="artist-role">${a.role || ''}</div>
        </div>
      </div>`;
    }).join('');
    const obs = new IntersectionObserver(es => {
      es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
    }, { threshold: 0.1 });
    artGrid.querySelectorAll('.fade-in').forEach(el => obs.observe(el));
  }

  /* ==========================================================
     CONTATO — redes sociais
     ========================================================== */
  const socialGrid = document.getElementById('social-grid-dinamico');
  if (socialGrid && CAT.contato) {
    const icones = {
      instagram: '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>',
      youtube: '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"></path><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"></polygon>',
      spotify: '<path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"></path>'
    };
    const redes = [
      ['instagram', 'Instagram', CAT.contato.instagram_handle || '@pordosomcultural'],
      ['youtube', 'YouTube', '/pordosomcultural'],
      ['spotify', 'Spotify', '/pordosom'],
    ];
    socialGrid.innerHTML = redes.map(([k, label, handle]) => `
      <a href="${CAT.contato[k] || '#'}" target="_blank" rel="noopener" class="social-card">
        <div class="social-card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">${icones[k]}</svg>
        </div>
        <div class="social-card-text">
          <div class="social-card-label">${label}</div>
          <div class="social-card-handle">${handle}</div>
        </div>
      </a>`).join('');
  }


  /* ---------- BANNER DA NOTICIA EM DESTAQUE (logo apos o hero) ---------- */
  const bannerEl = document.getElementById('banner-noticia');
  if (bannerEl && Array.isArray(CAT.posts) && CAT.posts.length) {
    const p = CAT.posts[0];
    const partes = String(p.date || '').split('-');
    const data = partes.length === 3 ? partes.reverse().join('/') : '';
    const temImg = p.imagem && p.imagem.startsWith('/');
    const imgTag = temImg ? '<img src="' + BASE + p.imagem + '" alt="" style="width:200px;height:200px;object-fit:cover;border-radius:4px;flex-shrink:0" loading="lazy">' : '';
    bannerEl.innerHTML =
      '<a href="' + BASE + '/blog.html" style="display:flex;gap:1.8rem;max-width:860px;margin:0 auto;padding:' + (temImg ? '1.6rem' : '2.2rem') + ';background:linear-gradient(135deg,var(--bg-card),var(--bg-darker));border:1px solid var(--border-color);border-left:4px solid var(--brand-primary);border-radius:6px;text-decoration:none;align-items:center;box-shadow:0 12px 40px rgba(0,0,0,.35);transition:transform .3s,border-color .3s" onmouseover="this.style.transform=\'translateY(-3px)\';this.style.borderColor=\'var(--brand-primary-light)\'" onmouseout="this.style.transform=\'\';this.style.borderColor=\'var(--border-color)\'">'
      + imgTag
      + '<div style="flex:1">'
      + '<div style="font-size:.62rem;letter-spacing:2.5px;text-transform:uppercase;color:var(--brand-accent);margin-bottom:.7rem">📰 Última notícia · ' + data + '</div>'
      + '<h3 style="font-size:clamp(1.15rem,3vw,1.6rem);font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--text-primary);line-height:1.25;margin-bottom:.8rem">' + (p.title || '') + '</h3>'
      + '<p style="font-size:.9rem;color:var(--text-secondary);line-height:1.7">' + (p.resumo || '') + '</p>'
      + '<span style="display:inline-block;margin-top:1.1rem;font-size:.68rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--brand-primary-light)">Ler a notícia completa →</span>'
      + '</div></a>';
  }

})();
