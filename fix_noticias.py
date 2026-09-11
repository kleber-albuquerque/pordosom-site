path = "admin/index.html"
src = open(path, encoding="utf-8").read()
n = 0

# ═══════════════════════════════════════════════
# 1. Sidebar: Notícias ativa (sai do emBreve)
# ═══════════════════════════════════════════════
old1 = '''<button class="side-item" data-pagina="noticias" onclick="emBreve('Notícias')"><span class="icone">📰</span> Notícias</button>'''
new1 = '''<button class="side-item" data-pagina="noticias"><span class="icone">📰</span> Notícias</button>'''
if old1 in src:
    src = src.replace(old1, new1); n += 1

# ═══════════════════════════════════════════════
# 2. Página Notícias (depois da página álbuns)
# ═══════════════════════════════════════════════
ancora_pag = '''    <!-- PÁGINA ÁLBUNS -->'''
pagina_noticias = '''    <!-- PÁGINA NOTÍCIAS -->
    <div id="pagina-noticias" class="hidden">
      <div class="toolbar">
        <div>
          <h1 class="page-title">Notícias</h1>
          <p class="page-sub" style="margin-bottom:0">Lançamentos, projetos e novidades do selo</p>
        </div>
        <button class="btn-novo" onclick='abrirNovaNoticia()'>＋ Nova Notícia</button>
      </div>
      <div class="loading" id="noticias-loading">Carregando notícias…</div>
      <div class="table-wrap hidden" id="noticias-table-wrap">
        <table>
          <thead>
            <tr><th>Data</th><th>Título</th><th>Resumo</th><th></th></tr>
          </thead>
          <tbody id="noticias-tbody"></tbody>
        </table>
      </div>
      <div class="vazio hidden" id="noticias-vazio">
        <span class="icone">📰</span>
        Nenhuma notícia publicada ainda.<br>
        <small>Clique em "＋ Nova Notícia" para o primeiro lançamento.</small>
      </div>
    </div>

    <!-- PÁGINA ÁLBUNS -->'''
if 'pagina-noticias' not in src and ancora_pag in src:
    src = src.replace(ancora_pag, pagina_noticias, 1); n += 1

# ═══════════════════════════════════════════════
# 3. Editor de notícia (overlay, depois do editor de álbum)
# ═══════════════════════════════════════════════
ancora_edit = '''  <!-- ===== EDITOR DE ÁLBUM (overlay) ===== -->'''
editor_noticia = '''  <!-- ===== EDITOR DE NOTÍCIA (overlay) ===== -->
  <div class="editor-overlay hidden" id="editor-noticia-overlay">
    <div class="editor-box">
      <div class="editor-header">
        <h2 id="editor-noticia-titulo">Nova Notícia</h2>
        <button class="editor-fechar" onclick="fecharEditorNoticia()">✕</button>
      </div>
      <div class="editor-grid">
        <div>
          <div class="capa-editor" id="noticia-img-preview" onclick="subirImagemNoticia()">
            <span class="capa-hint">🖼️<br>Clique para escolher<br>imagem de destaque<br>(opcional)</span>
          </div>
          <input type="file" id="noticia-img-input" accept="image/jpeg,image/png,image/webp" class="hidden" onchange="imagemNoticiaEscolhida(event)">
          <button class="btn-capa" onclick="subirImagemNoticia()">📷 Imagem de destaque</button>
          <p class="hint" style="font-size:.65rem;color:var(--text-muted);margin-top:.5rem;line-height:1.5">
            Aparece no topo da notícia<br>e nas redes sociais. Até 500KB.
          </p>
        </div>
        <div>
          <div class="f-grid">
            <div class="f-field full"><label>Título da notícia</label><input id="fn-titulo" type="text"></div>
            <div class="f-field"><label>Data de publicação</label><input id="fn-data" type="date"></div>
            <div class="f-field"><label>Status</label>
              <label class="f-toggle">
                <input type="checkbox" id="fn-rascunho">
                <span class="trilha"><span class="bolinha"></span></span>
                <span style="font-size:.75rem;color:var(--text-secondary)">Rascunho (não publica)</span>
              </label>
            </div>
            <div class="f-field full"><label>Resumo (aparece na lista do blog)</label><textarea id="fn-resumo" style="min-height:70px"></textarea></div>
            <div class="f-field full"><label>Conteúdo da notícia</label><textarea id="fn-corpo" style="min-height:200px"></textarea></div>
          </div>
        </div>
      </div>
      <div class="editor-rodape">
        <button class="btn-cancelar" onclick="fecharEditorNoticia()">Cancelar</button>
        <button class="btn-salvar" id="btn-salvar-noticia" onclick="salvarNoticia()">💾 Salvar Notícia</button>
      </div>
    </div>
  </div>

  <!-- ===== EDITOR DE ÁLBUM (overlay) ===== -->'''
if 'editor-noticia-overlay' not in src and ancora_edit in src:
    src = src.replace(ancora_edit, editor_noticia, 1); n += 1

# ═══════════════════════════════════════════════
# 4. Navegação: página notícias no toggle da sidebar
# ═══════════════════════════════════════════════
old4 = "['inicio', 'albuns'].forEach(p =>"
new4 = "['inicio', 'albuns', 'noticias'].forEach(p =>"
if old4 in src:
    src = src.replace(old4, new4); n += 1

# ═══════════════════════════════════════════════
# 5. O JS das notícias (antes do bloco PARTE 3)
# ═══════════════════════════════════════════════
ancora_js = "// ==========================================================\n// PARTE 3"
js_noticias = '''// ==========================================================
// PARTE 4 - NOTICIAS / BLOG
// ==========================================================
let NOTICIAS = [];
let noticiaAtual = null;
let imagemNoticiaNova = null;

async function carregarNoticias() {
  const loading = document.getElementById('noticias-loading');
  const wrap = document.getElementById('noticias-table-wrap');
  const vazio = document.getElementById('noticias-vazio');
  try {
    const lista = await gh('/repos/' + REPO + '/contents/content/posts');
    const mds = Array.isArray(lista) ? lista.filter(f => f.name.endsWith('.md')) : [];

    NOTICIAS = [];
    for (const f of mds) {
      const blob = await gh('/repos/' + REPO + '/contents/content/posts/' + f.name);
      const textoUtf8 = decodeURIComponent(escape(atob(blob.content.replace(/\\n/g, ''))));
      const { meta, corpo } = parseMd(textoUtf8);
      meta.corpo = corpo;
      meta._arquivo = f.name;
      meta._sha = blob.sha;
      if (typeof meta.generos === 'string') meta.generos = [];
      NOTICIAS.push(meta);
    }
    NOTICIAS.sort((a, b) => String(b.date || b._arquivo).localeCompare(String(a.date || a._arquivo)));

    const st = document.getElementById('stat-noticias');
    if (st) st.textContent = NOTICIAS.filter(x => !x.rascunho).length;

    const tbody = document.getElementById('noticias-tbody');
    tbody.innerHTML = NOTICIAS.map(x => {
      const data = (x.date || '').split('-').reverse().join('/');
      return '<tr>'
        + '<td style="white-space:nowrap">' + data + '</td>'
        + '<td><div class="titulo-cell">' + (x.title || x._arquivo) + '</div>'
        + (x.rascunho ? '<span class="tag-genero" style="color:var(--brand-accent)">rascunho</span>' : '') + '</td>'
        + '<td style="color:var(--text-muted);font-size:.75rem;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (x.resumo || '—') + '</td>'
        + '<td><button class="side-item" style="padding:.4rem .7rem" title="Editar" onclick="abrirEditorNoticia(NOTICIAS[' + NOTICIAS.indexOf(x) + '])">✏️</button>'
        + ' <button class="side-item" style="padding:.4rem .7rem" title="Excluir" onclick="excluirNoticia(NOTICIAS[' + NOTICIAS.indexOf(x) + '])">🗑️</button></td>'
        + '</tr>';
    }).join('');

    loading.classList.add('hidden');
    if (NOTICIAS.length) wrap.classList.remove('hidden'); else vazio.classList.remove('hidden');
  } catch (e) {
    // pasta inexistente = nenhuma notícia ainda (normal no começo)
    if (String(e.message).includes('404')) {
      loading.classList.add('hidden');
      vazio.classList.remove('hidden');
      const st = document.getElementById('stat-noticias');
      if (st) st.textContent = '0';
    } else {
      loading.textContent = 'Erro: ' + e.message;
      loading.style.color = '#f0b0b0';
    }
  }
}

function abrirNovaNoticia() {
  noticiaAtual = { _arquivo: '', _sha: null, title: '', date: new Date().toISOString().slice(0, 10),
                   resumo: '', rascunho: false, imagem: '', corpo: '' };
  imagemNoticiaNova = null;
  preencherEditorNoticia();
  document.getElementById('editor-noticia-titulo').textContent = 'Nova Notícia';
  document.getElementById('editor-noticia-overlay').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function abrirEditorNoticia(x) {
  noticiaAtual = x;
  imagemNoticiaNova = null;
  preencherEditorNoticia();
  document.getElementById('editor-noticia-titulo').textContent = 'Editar: ' + (x.title || 'notícia');
  document.getElementById('editor-noticia-overlay').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function preencherEditorNoticia() {
  document.getElementById('fn-titulo').value = noticiaAtual.title || '';
  document.getElementById('fn-data').value = noticiaAtual.date || '';
  document.getElementById('fn-resumo').value = noticiaAtual.resumo || '';
  document.getElementById('fn-corpo').value = noticiaAtual.corpo || '';
  document.getElementById('fn-rascunho').checked = !!noticiaAtual.rascunho;
  const prev = document.getElementById('noticia-img-preview');
  if (noticiaAtual.imagem && noticiaAtual.imagem.startsWith('/images')) {
    prev.innerHTML = '<img src="' + noticiaAtual.imagem + '" alt="">';
  } else {
    prev.innerHTML = '<span class="capa-hint">🖼️<br>Clique para escolher<br>imagem de destaque<br>(opcional)</span>';
  }
}

function fecharEditorNoticia() {
  document.getElementById('editor-noticia-overlay').classList.add('hidden');
  document.body.style.overflow = '';
  noticiaAtual = null; imagemNoticiaNova = null;
}

function subirImagemNoticia() { document.getElementById('noticia-img-input').click(); }
function imagemNoticiaEscolhida(e) {
  const arquivo = e.target.files[0];
  if (!arquivo) return;
  if (arquivo.size > 500 * 1024) {
    toast('Imagem grande (' + Math.round(arquivo.size/1024) + 'KB). Comprima em tinypng.com.');
    e.target.value = ''; return;
  }
  const leitor = new FileReader();
  leitor.onload = ev => {
    imagemNoticiaNova = ev.target.result.split(',')[1];
    document.getElementById('noticia-img-preview').innerHTML = '<img src="' + ev.target.result + '" alt="">';
    toast('Imagem pronta — enviada ao salvar');
  };
  leitor.readAsDataURL(arquivo);
}

function montarMdNoticia() {
  const val = id => (document.getElementById(id).value || '').trim();
  const q = s => '"' + (s || '').replace(/"/g, '\\\\"') + '"';
  return '---\\n'
    + 'title: ' + q(val('fn-titulo')) + '\\n'
    + 'date: ' + val('fn-data') + '\\n'
    + 'resumo: ' + q(val('fn-resumo')) + '\\n'
    + 'rascunho: ' + document.getElementById('fn-rascunho').checked + '\\n'
    + 'imagem: ' + q(noticiaAtual.imagem || '') + '\\n'
    + '---\\n\\n'
    + val('fn-corpo') + '\\n';
}

async function salvarNoticia() {
  if (!noticiaAtual) return;
  const btn = document.getElementById('btn-salvar-noticia');
  if (!document.getElementById('fn-titulo').value.trim()) {
    toast('O título é obrigatório'); return;
  }
  btn.disabled = true; btn.textContent = 'Salvando…';
  try {
    if (imagemNoticiaNova) {
      const baseNome = noticiaAtual._arquivo
        ? noticiaAtual._arquivo.replace('.md', '')
        : new Date().toISOString().slice(0,10) + '-' + slugify(document.getElementById('fn-titulo').value);
      const nomeImg = 'images/uploads/' + baseNome + '.jpg';
      const caminhoImg = '/repos/' + REPO + '/contents/' + nomeImg;
      let shaImg = null;
      try { const atual = await gh(caminhoImg); shaImg = atual.sha; } catch (e) {}
      await gh(caminhoImg, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          message: 'Imagem da notícia: ' + document.getElementById('fn-titulo').value,
          content: imagemNoticiaNova,
          ...(shaImg ? {sha: shaImg} : {})
        })
      });
      noticiaAtual.imagem = '/' + nomeImg;
    }

    const conteudo = btoa(unescape(encodeURIComponent(montarMdNoticia())));
    const ehNovo = !noticiaAtual._sha;
    const nomeArquivo = ehNovo
      ? new Date().toISOString().slice(0,10) + '-' + slugify(document.getElementById('fn-titulo').value) + '.md'
      : noticiaAtual._arquivo;

    const bodySalvar = {
      message: (ehNovo ? 'Nova notícia: ' : 'Edita notícia: ') + document.getElementById('fn-titulo').value,
      content: conteudo
    };
    if (!ehNovo) bodySalvar.sha = noticiaAtual._sha;

    await gh('/repos/' + REPO + '/contents/content/posts/' + nomeArquivo, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(bodySalvar)
    });

    toast('Notícia salva! O blog atualiza em ~2 min.');
    fecharEditorNoticia();
    await carregarNoticias();
  } catch (e) {
    toast('Erro ao salvar: ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '💾 Salvar Notícia';
  }
}

async function excluirNoticia(x) {
  if (!confirm('Excluir a notícia "' + (x.title || x._arquivo) + '"?')) return;
  try {
    await gh('/repos/' + REPO + '/contents/content/posts/' + x._arquivo, {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ message: 'Exclui notícia: ' + x.title, sha: x._sha })
    });
    toast('Notícia excluída.');
    await carregarNoticias();
  } catch (e) {
    toast('Erro ao excluir: ' + e.message);
  }
}

// ==========================================================
// PARTE 3'''
if 'PARTE 4' not in src and ancora_js in src:
    src = src.replace(ancora_js, js_noticias, 1); n += 1

# ═══════════════════════════════════════════════
# 6. Carregar notícias junto com álbuns (no entrar/init)
# ═══════════════════════════════════════════════
old6 = "abrirPainel();\n    await carregarAlbuns();"
new6 = "abrirPainel();\n    await carregarAlbuns();\n    carregarNoticias();"
if old6 in src:
    src = src.replace(old6, new6); n += 1
old6b = "abrirPainel();\n      carregarAlbuns();"
new6b = "abrirPainel();\n      carregarAlbuns();\n      carregarNoticias();"
if old6b in src:
    src = src.replace(old6b, new6b); n += 1

# ═══════════════════════════════════════════════
# 7. Stat de notícias no Início (card novo)
# ═══════════════════════════════════════════════
old7 = '''<div class="stat-card"><div class="stat-num" id="stat-generos">—</div><div class="stat-label">Gêneros ativos</div></div>'''
new7 = '''<div class="stat-card"><div class="stat-num" id="stat-generos">—</div><div class="stat-label">Gêneros ativos</div></div>
        <div class="stat-card"><div class="stat-num" id="stat-noticias">—</div><div class="stat-label">Notícias publicadas</div></div>'''
if old7 in src and 'stat-noticias' not in src:
    src = src.replace(old7, new7); n += 1

open(path, "w", encoding="utf-8").write(src)
print("aplicadas:", n, "de 8 edicoes (1 sidebar, 2 pagina, 3 editor, 4 navegacao, 5 JS, 6 carregamento, 7 stat)")
