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
      <a href="${BASE}/al
