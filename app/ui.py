from __future__ import annotations


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Hardline Sovereign Core</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; background:#0b1020; color:#e5e7eb; }
    header { padding:26px 32px; background:linear-gradient(135deg,#111827,#1f2937); border-bottom:1px solid #334155; }
    main { max-width:1280px; margin:0 auto; padding:28px 32px; }
    h1 { margin:0 0 8px; }
    h2 { margin-top:0; font-size:16px; }
    p { color:#cbd5e1; line-height:1.5; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }
    .stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
    .stat { background:#111827; border:1px solid #334155; border-radius:12px; padding:14px; text-align:center; }
    .stat .num { font-size:28px; font-weight:800; color:#60a5fa; }
    .stat .label { color:#94a3b8; font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
    .stat.bad .num { color:#f87171; }
    .stat.good .num { color:#22c55e; }
    .card { background:#111827; border:1px solid #334155; border-radius:14px; padding:18px; box-shadow:0 8px 28px rgba(0,0,0,.2); }
    .list-item { border-bottom:1px solid #1e293b; padding:8px 0; }
    .list-item:last-child { border-bottom:0; }
    input, textarea, select { width:100%; box-sizing:border-box; margin:6px 0 10px; padding:10px; border-radius:9px; border:1px solid #334155; background:#020617; color:#e5e7eb; }
    button { background:#2563eb; color:white; border:0; border-radius:10px; padding:10px 14px; font-weight:700; cursor:pointer; margin:4px 4px 4px 0; }
    button:hover { background:#1d4ed8; }
    button.secondary { background:#334155; }
    button.danger { background:#7f1d1d; }
    button.success { background:#14532d; }
    pre { white-space:pre-wrap; overflow-x:auto; background:#020617; border:1px solid #1e293b; border-radius:12px; padding:14px; color:#dbeafe; max-height:340px; }
    a { color:#93c5fd; text-decoration:none; }
    a:hover { text-decoration:underline; }
    .muted { color:#94a3b8; font-size:13px; }
    .ok { color:#22c55e; font-weight:800; }
    .scroll { max-height:280px; overflow-y:auto; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:700; background:#334155; }
    .pill.pending { background:#78350f; color:#fde68a; }
    .pill.approved { background:#14532d; color:#bbf7d0; }
    .pill.rejected { background:#7f1d1d; color:#fecaca; }
    section.card h2 { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  </style>
</head>
<body>
<header>
  <h1>Hardline Sovereign Core</h1>
  <p>AI-native workspace for tasks, artifacts, memory, approvals, and append-only execution history.</p>
  <p class="muted">v0.1.1 &middot; local-first &middot; mock/offline agent &middot; no paid AI calls &middot; no external writes</p>
</header>
<main>

  <section class="card">
    <h2>Status overview <button class="secondary" onclick="refreshAll()">Refresh</button></h2>
    <div id="statGrid" class="stat-grid">
      <div class="stat"><div class="num">-</div><div class="label">Tasks</div></div>
    </div>
  </section>

  <div class="grid" style="margin-top:16px;">
    <section class="card">
      <h2>Quick actions</h2>
      <button onclick="seedDemo()">Create demo task</button>
      <button onclick="runNewestTask()">Run newest task</button>
      <button class="secondary" onclick="verifyLedger()">Verify ledger</button>
      <button class="secondary" onclick="exportPackage()">Export package</button>
      <p class="muted">All actions run against the local FastAPI backend only. No external network calls are made.</p>
    </section>

    <section class="card">
      <h2>Create task</h2>
      <input id="taskTitle" placeholder="Task title" value="Review current system state">
      <textarea id="taskDescription" rows="3" placeholder="Task description">Create a structured artifact and approval item from this task.</textarea>
      <select id="taskPriority">
        <option>normal</option>
        <option>high</option>
        <option>critical</option>
        <option>low</option>
      </select>
      <button onclick="createTask()">Create task</button>
    </section>
  </div>

  <div class="grid" style="margin-top:16px;">
    <section class="card">
      <h2>Tasks</h2>
      <div id="tasks" class="scroll"></div>
    </section>
    <section class="card">
      <h2>Artifacts</h2>
      <div id="artifacts" class="scroll"></div>
    </section>
    <section class="card">
      <h2>Memory</h2>
      <div id="memory" class="scroll"></div>
    </section>
    <section class="card">
      <h2>Approvals</h2>
      <div id="approvals" class="scroll"></div>
    </section>
  </div>

  <div class="grid" style="margin-top:16px;">
    <section class="card">
      <h2>Ledger (append-only)</h2>
      <div id="ledger" class="scroll"></div>
    </section>
    <section class="card">
      <h2>Exported packages</h2>
      <div id="packages" class="scroll"></div>
    </section>
  </div>

  <section class="card" style="margin-top:16px;">
    <h2>Artifact preview</h2>
    <p class="muted" id="previewLabel">Click an artifact above to preview its content here.</p>
    <pre id="preview">(no artifact selected)</pre>
  </section>

  <section class="card" style="margin-top:16px;">
    <h2>Output log</h2>
    <pre id="output">Ready.</pre>
  </section>
</main>
<script>
async function api(path, opts) {
  const res = await fetch(path, opts || {});
  return await res.json();
}
function show(data) {
  document.getElementById('output').textContent = JSON.stringify(data, null, 2);
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
}

async function refreshStats() {
  const s = await api('/api/stats');
  const ledgerOk = s.ledger && s.ledger.valid;
  const cards = [
    {label:'Tasks', num:s.tasks, cls:''},
    {label:'Runs', num:s.runs, cls:''},
    {label:'Artifacts', num:s.artifacts, cls:''},
    {label:'Memory', num:s.memory, cls:''},
    {label:'Pending approvals', num:s.approvals.pending, cls: s.approvals.pending > 0 ? 'bad' : 'good'},
    {label:'Ledger valid', num: ledgerOk ? 'YES' : 'NO', cls: ledgerOk ? 'good' : 'bad'},
  ];
  document.getElementById('statGrid').innerHTML = cards.map(c =>
    `<div class="stat ${c.cls}"><div class="num">${esc(c.num)}</div><div class="label">${esc(c.label)}</div></div>`
  ).join('');
}

async function createTask() {
  const data = await api('/api/tasks', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      title:document.getElementById('taskTitle').value,
      description:document.getElementById('taskDescription').value,
      priority:document.getElementById('taskPriority').value
    })
  });
  show(data); await refreshAll();
}
async function seedDemo() {
  const data = await api('/api/demo/seed', {method:'POST'});
  show(data); await refreshAll();
}
async function runNewestTask() {
  const tasks = await api('/api/tasks');
  if (!tasks.tasks.length) { show({status:'blocked', reason:'create a task first'}); return; }
  const id = tasks.tasks[0].id;
  const data = await api('/api/tasks/' + id + '/run', {method:'POST'});
  show(data); await refreshAll();
}
async function verifyLedger() {
  const data = await api('/api/ledger/verify');
  show(data); await refreshStats(); await refreshLedger();
}
async function exportPackage() {
  const data = await api('/api/packages/export', {method:'POST'});
  show(data); await refreshPackages(); await refreshStats();
}

async function refreshTasks() {
  const data = await api('/api/tasks');
  document.getElementById('tasks').innerHTML = data.tasks.map(t =>
    `<div class="list-item"><b>${esc(t.title)}</b><br><span class="muted">${esc(t.id)} &middot; ${esc(t.status)} &middot; ${esc(t.priority)}</span></div>`
  ).join('') || '<p class="muted">No tasks yet.</p>';
}
async function previewArtifact(id, name) {
  document.getElementById('previewLabel').textContent = name + ' (' + id + ')';
  const res = await fetch('/api/artifacts/' + id + '/content');
  const text = await res.text();
  document.getElementById('preview').textContent = text;
}
async function refreshArtifacts() {
  const data = await api('/api/artifacts');
  document.getElementById('artifacts').innerHTML = data.artifacts.map(a =>
    `<div class="list-item"><a href="#" onclick="previewArtifact('${a.id}','${esc(a.name)}');return false;">${esc(a.name)}</a> &middot; <a href="/api/artifacts/${a.id}/content" target="_blank">open</a><br><span class="muted">${esc(a.id)} &middot; ${esc(a.size_bytes)} bytes &middot; sha256 ${esc((a.sha256||'').slice(0,12))}&hellip;</span></div>`
  ).join('') || '<p class="muted">No artifacts yet.</p>';
}
async function refreshMemory() {
  const data = await api('/api/memory');
  document.getElementById('memory').innerHTML = data.memory.map(m =>
    `<div class="list-item"><b>${esc(m.title)}</b><br><span class="muted">${esc(m.scope)} &middot; ${esc(m.id)}</span><p class="muted">${esc(m.body)}</p></div>`
  ).join('') || '<p class="muted">No memory entries yet.</p>';
}
async function refreshApprovals() {
  const data = await api('/api/approvals');
  document.getElementById('approvals').innerHTML = data.approvals.map(a =>
    `<div class="list-item"><span class="pill ${esc(a.status)}">${esc(a.status)}</span> ${esc(a.target_type)}<br>
     <span class="muted">${esc(a.id)} &rarr; ${esc(a.target_id)}</span><br>
     ${a.status === 'pending' ? `<button class="success" onclick="decideApproval('${a.id}','approve')">Approve</button><button class="danger" onclick="decideApproval('${a.id}','reject')">Reject</button>` : ''}
     </div>`
  ).join('') || '<p class="muted">No approvals yet.</p>';
}
async function decideApproval(id, action) {
  const data = await api('/api/approvals/' + id + '/' + action, {method:'POST'});
  show(data); await refreshAll();
}
async function refreshLedger() {
  const data = await api('/api/ledger');
  document.getElementById('ledger').innerHTML = data.events.map(e =>
    `<div class="list-item"><b>${esc(e.event_type)}</b> by ${esc(e.actor)}<br><span class="muted">${esc(e.timestamp)} &middot; ${esc(e.target_type)}:${esc(e.target_id)}</span><br><span class="muted">hash ${esc((e.event_hash||'').slice(0,16))}&hellip;</span></div>`
  ).join('') || '<p class="muted">No ledger events yet.</p>';
}
async function refreshPackages() {
  const data = await api('/api/packages');
  document.getElementById('packages').innerHTML = data.packages.map(p =>
    `<div class="list-item"><a href="${p.download_url}">${esc(p.name)}</a><br><span class="muted">${esc(p.size_bytes)} bytes &middot; ${esc(p.created_at)}</span></div>`
  ).join('') || '<p class="muted">No exported packages yet. Use "Export package" above.</p>';
}

async function refreshAll() {
  await refreshStats();
  await refreshTasks();
  await refreshArtifacts();
  await refreshMemory();
  await refreshApprovals();
  await refreshLedger();
  await refreshPackages();
}
refreshAll();
</script>
</body>
</html>"""
