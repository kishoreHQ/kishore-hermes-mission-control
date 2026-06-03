// Mission Control — Calm Command JavaScript
const S={data:null,serviceHealth:null,runFilter:'',activeSection:'home',drawerOpen:false,showTestData:false};
function $(id){return document.getElementById(id)}
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function fmt(n){const v=Number(n||0);return v>=1_000_000?`${(v/1_000_000).toFixed(1)}M`:v>=1_000?v.toLocaleString():String(v)}
function fd(v){if(!v)return'—';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
function dur(s){if(s==null)return'';const n=Number(s);if(n<60)return`${n.toFixed(1)}s`;if(n<3600)return`${Math.floor(n/60)}m`;return`${Math.floor(n/3600)}h`}
async function api(path,opts={}){const r=await fetch(path,{cache:'no-store',...opts});const d=await r.json();if(!r.ok)throw new Error(d.error||r.statusText);return d}
async function load(){try{S.data=await api(`/api/status?_=${Date.now()}`);try{S.serviceHealth=await api('/api/services/health')}catch(_){S.serviceHealth=null}render()}catch(e){$('mainContent').insertAdjacentHTML('afterbegin',`<div class="mc-error-banner">⚠ ${esc(e.message)} — Retrying in 30s</div>`)}}

// ── Navigation ────────────────────────────────────────────────
function navTo(section){
  S.activeSection=section;
  document.querySelectorAll('.mc-nav-item').forEach(b=>b.classList.remove('active'));
  document.querySelector(`[data-scroll="${section}"]`)?.classList.add('active');
  document.querySelectorAll('#mainContent > section').forEach(s=>s.style.display='none');
  const el=$(section); if(el) el.style.display='block';
  if(section==='home') renderHome();
  else if(section==='runs-section') renderRuns();
  else if(section==='workflows-section') renderWorkflows();
  else if(section==='dispatch-section') loadDispatches();
  else if(section==='agents-section') renderAgents();
  else if(section==='tasks-section') renderTasks();
  else if(section==='services-section') renderServices();
  else if(section==='logs-section') renderLogs();
  else if(section==='nightly-section') renderNightly();
  else if(section==='cron-section') renderCron();
  else if(section==='docs-section') renderDocs();
}

// ── Drawer ─────────────────────────────────────────────────────
function openDrawer(title,html){
  $('drawerTitle').textContent=title;$('drawerBody').innerHTML=html;
  $('drawer').classList.add('open');$('drawerBackdrop').classList.add('open');
  S.drawerOpen=true;
}
function closeDrawer(){
  $('drawer').classList.remove('open');$('drawerBackdrop').classList.remove('open');
  S.drawerOpen=false;
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&S.drawerOpen)closeDrawer()});

// ── Toast ──────────────────────────────────────────────────────
function toast(msg,type='ok'){
  const t=document.createElement('div');t.className=`mc-toast mc-toast-${type}`;t.textContent=msg;
  $('toastContainer').appendChild(t);
  setTimeout(()=>{t.classList.add('mc-toast-out');setTimeout(()=>t.remove(),300)},2800);
}

// ── Badge helper ───────────────────────────────────────────────
function badge(status,label){
  const map={succeeded:'ok',completed:'ok',online:'ok',active:'ok',running:'info',in_progress:'info',
    failed:'err',error:'err',offline:'err',degraded:'warn',warning:'warn',needs_review:'warn',
    queued:'idle',blocked:'idle',draft:'idle',paused:'idle',archived:'idle',unknown:'idle',
    ok:'ok',warn:'warn',err:'err',info:'info',idle:'idle'};
  const cls=map[status]||'idle';
  const glyph=cls==='err'?'!':(cls==='warn'?'△':'');
  return `<span class="mc-badge mc-badge-${cls}">${glyph?`<span class="mc-badge-glyph" aria-hidden="true">${glyph}</span>`:''}${esc(label||status)}</span>`;
}

// ── Master Render ──────────────────────────────────────────────
function render(){
  renderHome(); // always render home (health, metrics, running, activity)
  if(S.activeSection==='runs-section') renderRuns();
  else if(S.activeSection==='workflows-section') renderWorkflows();
}

// ═══════════════════════════════════════════════════════════════
// Data access helper
// ═══════════════════════════════════════════════════════════════
function D(){return S.data||{}}

// ═══════════════════════════════════════════════════════════════
// HOME — Command Center
// ═══════════════════════════════════════════════════════════════
function renderHome(){
  if(!S.data) return;
  renderStatusHero();
  renderHealthBar();
  renderMetrics();
  renderRunningNow();
  renderNeedsAttention();
  renderQuickActions();
  renderActivity();
  $('home').style.display='block';
}

function serviceItems(){return S.serviceHealth||D().services||[]}
function statusBucket(status){
  if(['online','succeeded','completed','active'].includes(status))return'ok';
  if(['degraded','warning','needs_review','blocked','paused'].includes(status))return'warn';
  if(['offline','failed','error','timed_out','retry_exhausted','cancelled'].includes(status))return'err';
  if(['running','in_progress','retrying'].includes(status))return'info';
  return'idle';
}
function timelineClass(status){
  const bucket=statusBucket(status);
  if(['running','retrying','in_progress'].includes(status))return'running';
  if(['queued','draft','pending','blocked','paused'].includes(status))return'queued';
  return bucket==='ok'?'ok':bucket==='err'?'err':bucket==='warn'?'warn':'idle';
}
function statusPriority(status){
  if(['running','retrying','in_progress'].includes(status))return 0;
  if(['queued','draft','pending','blocked','paused'].includes(status))return 1;
  if(statusBucket(status)==='err')return 2;
  if(statusBucket(status)==='warn')return 3;
  return 4;
}
function isTestNoise(item){
  const name=String(item?.title||item?.name||item?.workflow_title||item?.id||'').toUpperCase();
  const method=String(item?.dispatch_method||item?.method||'');
  return /^FINAL\b/.test(name)||/^VERIFY\b/.test(name)||/\bTEST$/.test(name)||/POPEN$/.test(name)||['timeout_test','streaming_test','stderr_test'].includes(method);
}
function renderStatusHero(){
  const services=serviceItems();
  const degraded=services.filter(s=>statusBucket(s.status)!=='ok');
  const failedRuns=(D().recent_runs||[]).filter(r=>statusBucket(r.status)==='err'&&!isTestNoise(r));
  const review=(D().review_queue||[]).filter(j=>!isTestNoise(j));
  const blocked=(D().workflows||[]).filter(w=>w.runtime_state==='blocked'||w.status==='blocked'||w.blocker);
  const failures=failedRuns.length;
  const attention=degraded.length+failures+review.length+blocked.length;
  const level=attention?((degraded.length+failures)>0?'err':'warn'):'ok';
  const verdict=attention?[
    degraded.length?`${degraded.length} service${degraded.length===1?'':'s'} degraded`:null,
    failures?`${failures} run failure${failures===1?'':'s'}`:null,
    review.length?`${review.length} review item${review.length===1?'':'s'}`:null,
    blocked.length?`${blocked.length} blocked workflow${blocked.length===1?'':'s'}`:null
  ].filter(Boolean).join(' · '):'All systems operational';
  const active=(D().active_runs||[]).length;
  $('statusHero').innerHTML=`<div class="mc-status-hero-copy">
    <div class="mc-status-kicker">${badge(level,level==='ok'?'OPERATIONAL':level==='warn'?'ATTENTION':'ACTION REQUIRED')}</div>
    <h1>${esc(verdict)}</h1>
    <p>${esc(active)} active run${active===1?'':'s'} · ${esc(services.length)} monitored service${services.length===1?'':'s'} · updated ${esc(fd(new Date().toISOString()))}</p>
  </div>
  <div class="mc-status-hero-count">
    <span>${esc(attention)}</span>
    <small>needs attention</small>
  </div>`;
}

function renderHealthBar(){
  const svcs=serviceItems();
  const html=svcs.map(s=>{
    const cls=s.status==='online'?'ok':s.status==='degraded'?'warn':'err';
    return `<span class="mc-badge mc-badge-${cls}">${esc(s.name)}</span>`;
  }).join(' ');
  $('healthBar').innerHTML=html||'<span class="mc-badge mc-badge-idle">No services</span>';
  $('healthUpdated').textContent=`Updated ${fd(new Date().toISOString())}`;
}

function renderMetrics(){
  const s=D().summary||{};
  const active=(D().active_runs||[]).length;
  const wfs=(D().workflows_multi||[]).length;
  const failedRuns=(D().recent_runs||[]).filter(r=>r.status==='failed').length;
  const review=s.review_items||0;
  const degraded=serviceItems().filter(x=>statusBucket(x.status)!=='ok').length;
  const items=[
    {v:active,l:'Running',c:'#60a5fa',big:true},
    {v:failedRuns,l:'Failed',c:failedRuns?'#ef4444':'#8892a8',big:failedRuns>0},
    {v:review,l:'Needs Review',c:review?'#f59e0b':'#8892a8'},
    {v:degraded,l:'Service Issues',c:degraded?'#ef4444':'#34d399'},
    {v:wfs,l:'Workflows',c:'#69a7ff'},
    {v:fmt(s.tokens),l:'Tokens',c:'#9aa4b5'},
    {v:`$${Number(s.cost||0).toFixed(2)}`,l:'Cost',c:'#34d399'}
  ];
  $('metricsRow').innerHTML=items.map(i=>`<div class="mc-metric ${i.big?'mc-metric-wide':''}"><span class="mc-metric-value" style="color:${i.c}">${esc(i.v)}</span><span class="mc-metric-label">${esc(i.l)}</span></div>`).join('');
}

function renderRunningNow(){
  const active=D().active_runs||[];
  $('runningCount').textContent=`${active.length} active`;
  if(!active.length){$('runningNowScroll').innerHTML='<div class="mc-empty"><span class="mc-empty-icon">✓</span>All quiet — nothing running.</div>';return}
  $('runningNowScroll').innerHTML=active.map(r=>`<article class="mc-card">
    <div class="mc-card-title">${badge(r.status)} ${esc(r.title)}</div>
    <div class="mc-card-meta">${esc(r.trigger_source)} · ${esc(r.current_step)} · ${esc(r.selected_profile||r.profile||'Default')}</div>
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="openRunDrawer('${esc(r.run_id)}')">Details</button></div>
  </article>`).join('');
}

function renderNeedsAttention(){
  const seen=new Set();
  const items=[];
  const push=(key,html)=>{if(!seen.has(key)){seen.add(key);items.push(html)}};
  serviceItems().filter(s=>statusBucket(s.status)!=='ok'&&(S.showTestData||!isTestNoise(s))).forEach(s=>push(`svc:${s.id||s.name}`,`<article class="mc-card mc-card-attention">
    <div class="mc-card-title">${badge(s.status,s.status)} ${esc(s.name)}</div>
    <div class="mc-card-body">${esc(s.health?.summary||s.systemd?.active||s.notes||'Service health needs review')}</div>
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navTo('services-section')">Services</button></div>
  </article>`));
  (D().recent_runs||[]).filter(r=>r.status==='failed'&&(S.showTestData||!isTestNoise(r))).slice(0,5).forEach(r=>push(`run:${r.run_id||r.title}`,`<article class="mc-card mc-card-attention">
    <div class="mc-card-title">${badge('err','FAILED')} ${esc(r.title)}</div>
    <div class="mc-card-body">${esc(r.error?.message||r.error?.summary||'No error details')}</div>
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="openRunDrawer('${esc(r.run_id)}')">View</button></div>
  </article>`));
  (D().review_queue||[]).filter(j=>S.showTestData||!isTestNoise(j)).slice(0,5).forEach(j=>push(`review:${j.id||j.name}`,`<article class="mc-card mc-card-attention">
    <div class="mc-card-title">${badge('warn','NEEDS REVIEW')} ${esc(j.name)}</div>
    <div class="mc-card-body">${esc(j.last_error||'Check latest run')}</div>
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" data-safe-action="open_output" data-job="${esc(j.id)}">Output</button></div>
  </article>`));
  (D().workflows||[]).filter(w=>(w.runtime_state==='blocked'||w.status==='blocked'||w.blocker)&&(S.showTestData||!isTestNoise(w))).slice(0,5).forEach(w=>push(`wf:${w.id||w.name}`,`<article class="mc-card mc-card-attention">
    <div class="mc-card-title">${badge('warn','BLOCKED')} ${esc(w.name||w.title)}</div>
    <div class="mc-card-body">${esc(w.blocker||w.purpose||'Workflow is blocked')}</div>
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navTo('workflows-section')">Workflows</button></div>
  </article>`));
  if(!items.length) items.push('<div class="mc-empty"><span class="mc-empty-icon">✓</span>Nothing needs attention.</div>');
  $('needsAttention').innerHTML=items.join('');
}

function renderQuickActions(){
  $('quickActions').innerHTML=`
    <button class="mc-btn mc-btn-primary" onclick="createWorkflow()">🔄 Create Workflow</button>
    <button class="mc-btn mc-btn-secondary" data-safe-action="test_adapter">◆ Test Adapter</button>
    <button class="mc-btn mc-btn-secondary" data-safe-action="refresh_all_status">↻ Refresh All</button>
    <button class="mc-btn mc-btn-secondary" data-confirm-action="send_telegram_summary">📤 Send Summary</button>`;
}

function renderActivity(){
  const actions=(D().action_history||[]).slice(0,10);
  const runs=(D().recent_runs||[]).slice(0,5);
  const items=[];
  runs.forEach(r=>items.push(`<div class="mc-activity-item"><span class="time">${fd(r.started_at)}</span> ${badge(r.status,r.status)} ${esc(r.title)}</div>`));
  actions.forEach(a=>items.push(`<div class="mc-activity-item"><span class="time">${fd(a.created_at)}</span> ${esc(a.action)} · ${esc(a.status)}</div>`));
  if(!items.length) items.push('<div class="mc-activity-item">No recent activity.</div>');
  $('activityFeed').innerHTML=items.join('');
}

// ═══════════════════════════════════════════════════════════════
// RUNS
// ═══════════════════════════════════════════════════════════════
function renderRuns(){
  let runs=D().recent_runs||[];
  if(S.runFilter) runs=runs.filter(r=>r.status===S.runFilter);
  const filters=['','running','succeeded','failed','needs_review'];
  const labels={running:'Active',succeeded:'Succeeded',failed:'Failed',needs_review:'Review'};
  $('runFilters').innerHTML=[`<button class="mc-filter-chip ${!S.runFilter?'active':''}" onclick="S.runFilter='';renderRuns()">All</button>`]
    .concat(filters.slice(1).map(f=>`<button class="mc-filter-chip ${S.runFilter===f?'active':''}" onclick="S.runFilter='${f}';renderRuns()">${labels[f]}</button>`)).join('');
  if(!runs.length){$('runHistory').innerHTML='<div class="mc-empty"><span class="mc-empty-icon">∅</span>No runs found.</div>';return}
  $('runHistory').innerHTML=runs.map(r=>`<article class="mc-card">
    <div class="mc-card-title">${badge(r.status,r.status)} ${esc(r.title)}</div>
    <div class="mc-card-meta">${esc(r.trigger_source)} · ${esc(r.service)} · ${esc(r.selected_profile||r.profile||'Default')} · ${dur(r.duration)}</div>
    ${r.error?.message?`<div class="mc-card-body" style="color:var(--err)">${esc(r.error.message)}</div>`:''}
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="openRunDrawer('${esc(r.run_id)}')">Details</button></div>
  </article>`).join('');
}

function openRunDrawer(runId){
  const run=(D().recent_runs||[]).find(r=>r.run_id===runId);
  if(run){showRunDrawer(run);return}
  api(`/api/runs/${runId}`).then(showRunDrawer).catch(e=>toast(e.message,'err'));
}

function showRunDrawer(run){
  const logs=(run.logs||[]).map(l=>`<span class="${l.level==='error'?'err-line':l.level==='warn'?'warn-line':''}">[${esc(l.level)}] ${esc(l.step)}: ${esc(l.message)}</span>`).join('\n');
  const tg=(run.telegram_updates||[]).map(u=>`<span>${esc(u.event)} ${fd(u.sent_at)}</span>`).join(' · ');
  const st=['queued','running','waiting_for_approval','succeeded','failed','cancelled','timed_out','needs_review']
    .map(s=>`<span class="mc-timeline-step ${run.status===s?'ok':(s==='failed'?'err':'')}">${s.replace(/_/g,' ')}</span>`).join('');
  const html=`
    <div class="mc-card"><strong>Status</strong> ${badge(run.status,run.status)} · <code>${esc(run.run_id)}</code></div>
    <div class="mc-card">
      <div><strong>Source:</strong> ${esc(run.trigger_source)} · ${esc(run.service)}</div>
      <div><strong>Profile:</strong> ${esc(run.selected_profile||run.profile||'Default')} (${run.profile_mode||'auto'})</div>
      <div><strong>Confidence:</strong> ${run.routing_confidence?Math.round(run.routing_confidence*100)+'%':'N/A'}</div>
      <div><strong>Started:</strong> ${fd(run.started_at)} · <strong>Finished:</strong> ${fd(run.finished_at)} · <strong>Duration:</strong> ${dur(run.duration)}</div>
    </div>
    <div class="mc-timeline">${st}</div>
    ${tg?`<div><strong>Telegram:</strong> ${tg}</div>`:''}
    ${logs?`<div><strong>Logs:</strong><pre class="mc-log-viewer">${logs}</pre></div>`:''}
    ${run.output&&Object.keys(run.output).length?`<div><strong>Output:</strong><pre class="mc-log-viewer">${JSON.stringify(run.output,null,2)}</pre></div>`:''}
    ${run.error&&Object.keys(run.error).length?`<div><strong>Error:</strong><pre class="mc-log-viewer" style="color:var(--err)">${JSON.stringify(run.error,null,2)}</pre></div>`:''}
    <div class="mc-btn-group"><button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(run)},null,2));toast('Copied!')">Copy JSON</button></div>`;
  openDrawer(`Run: ${run.title}`,html);
}

// ═══════════════════════════════════════════════════════════════
// WORKFLOWS
// ═══════════════════════════════════════════════════════════════
function renderWorkflows(){
  const wfs=D().workflows_multi||[];
  if(!wfs.length){$('workflowList').innerHTML='<div class="mc-empty"><span class="mc-empty-icon">🔄</span>No workflows yet.<br><button class="mc-btn mc-btn-primary" onclick="createWorkflow()" style="margin-top:10px">+ Create Workflow</button></div>';return}
  $('workflowList').innerHTML=wfs.map(wf=>{
    const sts=wf.subtasks||[];
    const done=sts.filter(s=>s.status==='completed').length;
    const fail=sts.filter(s=>['failed','timed_out','retry_exhausted','cancelled'].includes(s.status)).length;
    const profiles=[...new Set(sts.map(s=>s.profile))].join(' → ');
    return `<article class="mc-card">
      <div class="mc-card-title">${badge(wf.status,wf.status)} ${esc(wf.title)}</div>
      <div class="mc-card-meta">${profiles} · ${esc(wf.coordinator_profile)} coordinator</div>
      <div class="mc-progress"><div class="mc-progress-bar" style="width:${sts.length?Math.round(done/sts.length*100):0}%"></div></div>
      <div class="mc-card-meta">${done}/${sts.length} done · ${fail} failed · failure: ${esc(wf.failure_reason||'none')}</div>
      <div class="wf-subtasks">${sts.map(s=>`<span class="wf-subtask-badge ${s.status}">${esc(s.profile)}: ${esc(s.status)}</span>`).join(' ')}</div>
      <div class="mc-btn-group">
        <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="openWfDrawer('${esc(wf.workflow_id)}')">Details</button>
        ${wf.status==='draft'||wf.status==='paused'?`<button class="mc-btn mc-btn-xs mc-btn-primary" onclick="wfAction('${esc(wf.workflow_id)}','start')">Start</button>`:''}
        ${wf.status==='running'?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="wfAction('${esc(wf.workflow_id)}','pause')">Pause</button>`:''}
        <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="wfAction('${esc(wf.workflow_id)}','synthesize')">Synthesize</button>
      </div></article>`;
  }).join('');
}

function openWfDrawer(wfId){
  const wf=(D().workflows_multi||[]).find(w=>w.workflow_id===wfId);
  if(wf){showWfDrawer(wf);return}
  api(`/api/workflows/${wfId}`).then(showWfDrawer).catch(e=>toast(e.message,'err'));
}

function showWfDrawer(wf){
  const sts=wf.subtasks||[];
  const done=sts.filter(s=>s.status==='completed').length;
  const failedStatuses=new Set(['failed','timed_out','retry_exhausted','cancelled']);
  const fail=sts.filter(s=>failedStatuses.has(s.status)).length;
  const syn=wf.final_synthesis;
  const ordered=sts.slice().sort((a,b)=>statusPriority(a.status)-statusPriority(b.status)||(Number(a.order||0)-Number(b.order||0)));
  const priorityHtml=ordered.filter(st=>statusPriority(st.status)<2).map(st=>`<div class="mc-timeline-priority">
    ${badge(st.status,st.status)} <strong>${esc(st.profile)}</strong> · ${esc(st.title)} <span>${esc(st.process_status||'pending')}</span>
  </div>`).join('');
  const stHtml=ordered.map(st=>{
    const stdout=asTail(st.stdout_tail).slice(-6).join('\n');
    const stderr=asTail(st.stderr_tail).slice(-6).join('\n');
    const retryAttempt=st.retry_attempt??st.retries??0;
    const maxRetries=st.max_retries??st.retry_policy?.retry_count??0;
    const did=st.dispatch_id||'';
    const errClass=timelineClass(st.status);
    return `<div class="mc-timeline-step ${errClass}">
    <strong>${esc(st.profile)}</strong>: ${esc(st.title)}
    <div class="mc-card-meta">${badge(st.status,st.status)} · process: ${esc(st.process_status||'n/a')} · order: ${st.order} · retry: ${esc(retryAttempt)}/${esc(maxRetries)} · timeout: ${esc(st.timeout_seconds||120)}s · failure: ${esc(st.failure_reason||'none')}</div>
    <div class="mc-card-meta">dispatch: ${did?`<code>${esc(did)}</code>`:'none'} · pid: ${esc(st.pid||'none')} · exit: ${esc(st.exit_code??'pending')} · duration: ${esc(st.duration_seconds??0)}s</div>
    <div class="mc-card-meta">${st.depends_on?.length?`← waits for: ${st.depends_on.join(', ')}`:'(no deps)'}</div>
    ${st.last_output_chunk?`<div class="mc-card-body" style="color:var(--ok)">stdout: ${esc(st.last_output_chunk).substring(0,240)}</div>`:''}
    ${st.last_error_chunk?`<div class="mc-card-body" style="color:var(--err)">stderr: ${esc(st.last_error_chunk).substring(0,240)}</div>`:''}
    ${(stdout||stderr)?`<details class="mc-log-details"><summary>stdout/stderr tail</summary>${stdout?`<pre class="mc-log-viewer" style="max-height:140px">${esc(stdout)}</pre>`:''}${stderr?`<pre class="mc-log-viewer" style="max-height:140px;color:var(--err)">${esc(stderr)}</pre>`:''}</details>`:''}
    ${st.attempt_history?.length?`<details><summary style="font-size:11px;color:var(--text-muted);cursor:pointer">Attempts (${st.attempt_history.length})</summary><pre class="mc-log-viewer" style="max-height:220px">${esc(JSON.stringify(st.attempt_history,null,2))}</pre></details>`:''}
    ${st.output?`<pre class="mc-log-viewer" style="margin-top:4px">${esc(JSON.stringify(st.output,null,2))}</pre>`:''}
    ${st.error?`<pre class="mc-log-viewer" style="color:var(--err);margin-top:4px">${esc(JSON.stringify(st.error,null,2))}</pre>`:''}
    <div class="mc-btn-group" style="margin-top:4px">
      ${st.status==='queued'?`<button class="mc-btn mc-btn-xs mc-btn-primary" onclick="stAction('${esc(wf.workflow_id)}','${esc(st.id)}','start')">Start</button>`:''}
      ${failedStatuses.has(st.status)?`<button class="mc-btn mc-btn-xs mc-btn-primary" onclick="wfResume('${esc(wf.workflow_id)}','resume_from_failed_step','${esc(st.id)}')">Resume from failed step</button>`:''}
      ${failedStatuses.has(st.status)?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="wfResume('${esc(wf.workflow_id)}','resume_from_next_step','${esc(st.id)}')">Resume from next step</button>`:''}
      <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="wfResume('${esc(wf.workflow_id)}','rerun_selected_step','${esc(st.id)}')">Rerun step</button>
      ${did?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navTo('dispatch-section');dispatchLive('${esc(did)}')">Dispatch details</button>`:''}
      ${st.status!=='completed'?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="stReroute('${esc(wf.workflow_id)}','${esc(st.id)}')">Reroute</button>`:''}
      ${st.status==='running'||st.status==='retrying'?`<button class="mc-btn mc-btn-xs mc-btn-danger" onclick="wfAction('${esc(wf.workflow_id)}','cancel')">Cancel workflow</button>`:''}
    </div></div>`}).join('');
  const synHtml=syn?`<div class="mc-card" style="border-color:var(--ok);margin-top:12px">
    <strong style="color:var(--ok)">Final Synthesis:</strong> ${esc(syn.status)} · ${syn.completed}/${syn.total_subtasks} done · failed: ${esc(syn.failed||0)}
    <div class="mc-card-body">${esc(syn.summary)}</div>
    <div class="mc-card-body">${esc(syn.next_action)}</div></div>`:'';
  const html=`
    <div class="mc-card"><strong>ID:</strong> <code>${esc(wf.workflow_id)}</code> · ${badge(wf.status,wf.status)} · ${esc(wf.mode)} · failure: ${esc(wf.failure_reason||'none')}</div>
    <div class="mc-card"><strong>Coordinator:</strong> ${esc(wf.coordinator_profile)} · <strong>Progress:</strong> ${done}/${sts.length} · failed: ${fail}</div>
    <div class="mc-btn-group">
      ${wf.status==='draft'||wf.status==='paused'?`<button class="mc-btn mc-btn-primary" onclick="wfAction('${esc(wf.workflow_id)}','start')">Start</button>`:''}
      ${wf.status==='running'?`<button class="mc-btn mc-btn-secondary" onclick="wfAction('${esc(wf.workflow_id)}','pause')">Pause</button>`:''}
      ${wf.status==='running'?`<button class="mc-btn mc-btn-danger" onclick="wfAction('${esc(wf.workflow_id)}','cancel')">Cancel</button>`:''}
      <button class="mc-btn mc-btn-secondary" onclick="wfAction('${esc(wf.workflow_id)}','dispatch-parallel')">Dispatch ready</button>
      <button class="mc-btn mc-btn-secondary" onclick="wfTimeline('${esc(wf.workflow_id)}')">Timeline API</button>
      <button class="mc-btn mc-btn-secondary" onclick="wfAction('${esc(wf.workflow_id)}','synthesize')">Synthesize</button>
    </div>
    ${priorityHtml?`<strong>Pending / running steps:</strong><div class="mc-timeline-priorities">${priorityHtml}</div>`:''}
    <strong>Step timeline:</strong>
    <div class="mc-timeline">${stHtml}</div>
    ${synHtml}
    <div class="mc-card-meta">Telegram: ${(wf.telegram_updates||[]).map(u=>`${esc(u.event)} ${fd(u.sent_at)}`).join(' · ')||'None'}</div>`;
  openDrawer(`Workflow: ${wf.title}`,html);
}

async function wfResume(wfId,mode,stepId){
  try{const r=await api(`/api/workflows/${wfId}/resume`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,step_id:stepId,start:true})});
    if(r.ok)toast(`Workflow resumed: ${mode}`);else toast(r.error||'Resume failed','err');setTimeout(load,700)}
  catch(e){toast(e.message,'err')}
}
async function wfTimeline(wfId){
  try{const r=await api(`/api/workflows/${wfId}/timeline`);openDrawer(`Timeline ${wfId}`,`<pre class="mc-log-viewer">${esc(JSON.stringify(r,null,2))}</pre>`)}
  catch(e){toast(e.message,'err')}
}

async function createWorkflow(){
  const title=prompt('Describe the task:');
  if(!title)return;
  try{const r=await api('/api/workflows/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title})});
    if(r.ok){toast('Workflow created');setTimeout(load,500);navTo('workflows-section')}else toast(r.error,'err')}
  catch(e){toast(e.message,'err')}
}

async function wfAction(id,action){
  try{const r=await api(`/api/workflows/${id}/${action}`,{method:'POST'});
    if(r.ok)toast(`Workflow ${action}`);else toast(r.error,'err');setTimeout(load,400)}
  catch(e){toast(e.message,'err')}
}

async function stAction(wfId,stId,action){
  try{
    let r;
    if(action==='start') r=await api(`/api/workflows/${wfId}/subtasks/${stId}/start`,{method:'POST'});
    else if(action==='retry') r=await api(`/api/workflows/${wfId}/subtasks/${stId}/retry`,{method:'POST'});
    else if(action==='complete'){
      const out=prompt('Output summary?'); if(!out)return;
      r=await api(`/api/workflows/${wfId}/subtasks/${stId}/complete`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({output:{result:out}})});
    }else if(action==='fail'){
      const err=prompt('Error message?'); if(!err)return;
      r=await api(`/api/workflows/${wfId}/subtasks/${stId}/fail`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({error:{message:err}})});
    }
    if(r&&r.ok)toast(`Subtask ${action}`);else if(r)toast(r.error,'err');setTimeout(load,400)}
  catch(e){toast(e.message,'err')}
}

async function stReroute(wfId,stId){
  const profile=prompt('Reroute to profile (Coder, ContentCreator, DeepResearch, MarketAnalyst, Tutor, Default):');
  if(!profile)return;
  try{const r=await api(`/api/workflows/${wfId}/subtasks/${stId}/reroute`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile})});
    if(r.ok)toast(`Rerouted to ${profile}`);else toast(r.error,'err');setTimeout(load,400)}
  catch(e){toast(e.message,'err')}
}

// ═══════════════════════════════════════════════════════════════
// DISPATCH
// ═══════════════════════════════════════════════════════════════
async function loadDispatches(){
  try{const r=await api('/api/dispatch');renderDispatchList(r)}catch(e){$('dispatchList').innerHTML='<div class="mc-error-banner">Failed to load: '+esc(e.message)+'</div>'}
}
function asTail(v){return Array.isArray(v)?v:(v?String(v).split('\n').filter(Boolean):[])}
function renderDispatchList(items){
  $('dispatchCount').textContent=`${items.length} total`;
  if(!items.length){$('dispatchList').innerHTML='<div class="mc-empty"><span class="mc-empty-icon">⚡</span>No dispatches yet. Create a workflow and dispatch it.</div>';return}
  $('dispatchList').innerHTML=items.map(d=>{
    const stdout=asTail(d.stdout_tail).slice(-8).join('\n');
    const stderr=asTail(d.stderr_tail).slice(-8).join('\n');
    const liveMeta=`PID: ${esc(d.pid||'none')} · Process: ${esc(d.process_status||d.status||'unknown')} · Exit: ${esc(d.exit_code??'pending')} · Elapsed: ${esc(d.elapsed_seconds||0)}s · Timeout: ${esc(d.timeout_seconds||120)}s`;
    const timeline=dispatchTimeline(d);
    return `<article class="mc-card">
    <div class="mc-card-title">${badge(d.status,d.status)} ${esc(d.profile)}: ${esc(d.title||d.workflow_title)}</div>
    <div class="mc-card-meta">Method: ${esc(d.dispatch_method)} · Session: ${esc(d.session_id||'none')} · ${d.finished_at?fd(d.finished_at):'pending'}</div>
    <div class="mc-card-meta">${liveMeta} · Retry: ${esc(d.retry_count||0)}/${esc(d.max_retries||0)} · Failure: ${esc(d.failure_reason||'none')}</div>
    <div class="mc-dispatch-timeline">${timeline}</div>
    ${d.last_output_chunk?`<div class="mc-card-body" style="color:var(--ok)">stdout: ${esc(d.last_output_chunk).substring(0,240)}</div>`:''}
    ${d.last_error_chunk?`<div class="mc-card-body" style="color:var(--err)">stderr: ${esc(d.last_error_chunk).substring(0,240)}</div>`:''}
    ${d.output?.response?`<div class="mc-card-body" style="color:var(--ok)">${esc(d.output.response).substring(0,200)}</div>`:''}
    ${d.error?.message?`<div class="mc-card-body" style="color:var(--err)">${esc(d.error.message).substring(0,200)}</div>`:''}
    ${(stdout||stderr)?`<details class="mc-log-details"><summary>Live stdout/stderr</summary>${stdout?`<pre class="mc-log-viewer" style="max-height:160px">${esc(stdout)}</pre>`:''}${stderr?`<pre class="mc-log-viewer" style="max-height:160px;color:var(--err)">${esc(stderr)}</pre>`:''}</details>`:''}
    ${d.prompt?`<details class="mc-log-details"><summary>Prompt</summary><pre class="mc-log-viewer" style="max-height:200px" id="prompt-${esc(d.dispatch_id)}">${esc(d.prompt)}</pre></details>`:''}
    <div class="mc-btn-group">
      ${d.status==='queued'?`<button class="mc-btn mc-btn-xs mc-btn-primary" onclick="dispatchStart('${esc(d.dispatch_id)}')">▶ Start</button>`:''}
      ${(d.status==='failed'||d.status==='timed_out'||d.status==='retry_exhausted')?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="dispatchStart('${esc(d.dispatch_id)}')">Retry</button>`:''}
      ${(d.status==='queued'||d.status==='running'||d.status==='retrying'||d.status==='cancelling')?`<button class="mc-btn mc-btn-xs mc-btn-danger" onclick="dispatchCancel('${esc(d.dispatch_id)}')">Cancel</button>`:''}
      <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="dispatchLive('${esc(d.dispatch_id)}')">Live</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="dispatchManual('${esc(d.dispatch_id)}')">Manual Output</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navigator.clipboard.writeText(document.getElementById('prompt-${esc(d.dispatch_id)}')?.textContent||'');toast('Copied!')">Copy Prompt</button>
      ${d.session_id?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="dispatchLogs('${esc(d.dispatch_id)}')">Logs</button>`:''}
      ${d.workflow_id?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navTo('workflows-section');openWfDrawer('${esc(d.workflow_id)}')">Workflow</button>`:''}
    </div></article>`}).join('');
}
function dispatchTimeline(d){
  const steps=[
    {label:'queued',status:d.created_at?'completed':'queued'},
    {label:'started',status:d.started_at?'completed':'queued'},
    {label:'running',status:['running','retrying','cancelling'].includes(d.status)?'running':(d.started_at?'completed':'queued')},
    {label:d.status||'pending',status:d.status||'queued'}
  ];
  return steps.map(s=>`<span class="mc-dispatch-step ${timelineClass(s.status)}">${esc(s.label)}</span>`).join('');
}

async function dispatchStart(id){
  try{const r=await api(`/api/dispatch/${id}/start`,{method:'POST'});
    if(r.ok)toast('Started');else toast(r.error||'Failed','err');
    loadDispatches();setTimeout(load,500)}
  catch(e){toast(e.message,'err')}}
async function dispatchCancel(id){
  try{const r=await api(`/api/dispatch/${id}/cancel`,{method:'POST'});
    if(r.ok)toast('Cancelled');loadDispatches()}
  catch(e){toast(e.message,'err')}}
async function dispatchManual(id){
  const out=prompt('Paste output or enter summary:');
  if(!out)return;
  try{const r=await api(`/api/dispatch/${id}/manual-output`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({output:{manual:true,result:out}})});
    if(r.ok)toast('Output recorded');loadDispatches();setTimeout(load,500)}
  catch(e){toast(e.message,'err')}}

async function dispatchLive(id){
  try{const r=await api(`/api/dispatch/${id}/live`);
    const stdout=asTail(r.stdout_tail).join('\n');
    const stderr=asTail(r.stderr_tail).join('\n');
    const html=`<div class="mc-card">
      <div class="mc-card-title">${badge(r.status,r.status)} Live Dispatch</div>
      <div class="mc-card-meta">PID: ${esc(r.pid||'none')} · Process: ${esc(r.process_status||'')} · Exit: ${esc(r.exit_code??'pending')} · Elapsed: ${esc(r.elapsed_seconds||0)}s</div>
      <div class="mc-dispatch-timeline">${dispatchTimeline(r)}</div>
    </div>
    <details class="mc-log-details"><summary>stdout</summary><pre class="mc-log-viewer">${esc(stdout||r.last_output_chunk||'No stdout yet')}</pre></details>
    <details class="mc-log-details"><summary>stderr</summary><pre class="mc-log-viewer" style="color:var(--err)">${esc(stderr||r.last_error_chunk||'No stderr yet')}</pre></details>`;
    openDrawer(`Dispatch: ${id}`,html)}
  catch(e){toast(e.message,'err')}}

async function dispatchLogs(id){
  try{const r=await api(`/api/dispatch/${id}/logs`);
    const html=`<h4>Dispatch Logs</h4><pre class="mc-log-viewer">${esc(r.logs||'No logs')}</pre>`;
    openDrawer(`Dispatch Logs: ${id}`,html)}
  catch(e){toast(e.message,'err')}}

// ═══════════════════════════════════════════════════════════════
// AGENTS / PROFILES
// ═══════════════════════════════════════════════════════════════
function renderAgents(){
  const profiles=D().profiles||[];
  const icons={Default:'◆',Coder:'⌘',ContentCreator:'✍',DeepResearch:'⌕',MarketAnalyst:'📈',Tutor:'📖'};
  const activeRuns=D().active_runs||[];
  if(!profiles.length){$('agentCards').innerHTML='<div class="mc-empty">No profiles found.</div>';return}
  $('agentCards').innerHTML=profiles.map(p=>{
    const pruns=activeRuns.filter(r=>(r.selected_profile||r.profile||'')===p.name);
    const recent=(D().recent_runs||[]).filter(r=>(r.selected_profile||r.profile||'')===p.name).slice(0,3);
    return `<article class="mc-profile-card">
      <h3>${icons[p.name]||'•'} ${esc(p.name)}</h3>
      <div class="desc">${esc(p.description)}</div>
      <div class="mc-profile-meta">
        <span>SOUL.md<br><b>${p.has_soul?'✓ '+p.soul_size+'B':'✗'}</b></span>
        <span>Active<br><b>${pruns.length}</b></span>
        <span>Routing<br><b>${p.directory!=='built-in'?'ready':'static'}</b></span></div>
      ${recent.length?`<div class="mc-card-meta">Recent: ${recent.map(r=>badge(r.status,esc(r.title).substring(0,15))).join(' ')}</div>`:''}
      <div class="mc-btn-group">
        ${p.name!=='Default'?`<button class="mc-btn mc-btn-xs mc-btn-secondary" data-safe-action="test_profile_routing" data-profile="${esc(p.name)}">Test</button>`:''}
        ${p.name!=='Default'?`<button class="mc-btn mc-btn-xs mc-btn-secondary" data-confirm-action="reload_profile" data-profile="${esc(p.name)}">Reload</button>`:''}
        ${p.name!=='Default'?`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="editProf('${esc(p.name)}')">Edit</button>`:''}
      </div></article>`;
  }).join('');
}

async function editProf(name){
  const desc=prompt(`Edit ${name} description:`);
  if(!desc)return;
  try{const r=await api('/api/profiles/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:name,description:desc})});
    if(r.ok){toast('Updated');setTimeout(load,500)}else toast(r.error,'err')}
  catch(e){toast(e.message,'err')}
}

// ═══════════════════════════════════════════════════════════════
// TASKS / KANBAN
// ═══════════════════════════════════════════════════════════════
let draggedTaskId=null;

function renderTasks(){
  const tasks=D().tasks||[];
  const lanes={in_progress:[],in_review:[],scheduled:[],archived:[]};
  tasks.forEach(t=>{const l=t.status;lanes[l]?lanes[l].push(t):lanes.in_progress.push(t)});
  const labels={in_progress:'In Progress',in_review:'Needs Review',scheduled:'Scheduled',archived:'Archived'};
  $('taskBoard').innerHTML=Object.entries(lanes).map(([k,items])=>`<div class="mc-kanban-col" ondragover="event.preventDefault();this.classList.add('drag-over')" ondragleave="this.classList.remove('drag-over')" ondrop="handleDrop(event,'${k}')">
    <h3>${labels[k]} · ${items.length}</h3>
    ${items.map(c=>`<div class="mc-kanban-card" draggable="true" ondragstart="dragStart(event,'${esc(c.id)}')" ondragend="dragEnd(event)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <strong>${esc(c.title)}</strong><span class="mc-badge mc-badge-idle">${esc(c.priority||'normal')}</span></div>
      <div class="mc-card-meta">${esc(c.assignee||'unassigned')}</div>
      <div class="mc-btn-group" style="margin-top:6px">
        <select onchange="assignTask('${esc(c.id)}',this.value);this.value=''" style="font-size:10px;padding:2px 4px;border-radius:4px;border:1px solid var(--border);background:var(--bg-base);color:var(--text)"><option value="">Assign…</option>${['Default','Coder','ContentCreator','DeepResearch','MarketAnalyst','Tutor'].map(p=>`<option value="${p}">${p}</option>`).join('')}</select>
        <button class="mc-btn mc-btn-xs mc-btn-danger" onclick="archiveTask('${esc(c.id)}')">Archive</button>
      </div></div>`).join('')||'<div class="mc-empty">Drop tasks here</div>'}</div>`).join('');
}

function dragStart(e,id){draggedTaskId=id;e.target.classList.add('dragging')}
function dragEnd(e){e.target.classList.remove('dragging');document.querySelectorAll('.mc-kanban-col').forEach(c=>c.classList.remove('drag-over'))}
async function handleDrop(e,lane){e.preventDefault();e.target.closest('.mc-kanban-col')?.classList.remove('drag-over');if(!draggedTaskId)return;
  try{const r=await api('/api/tasks/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:draggedTaskId,status:lane})});
    if(r.ok)toast(`Moved to ${lane.replace(/_/g,' ')}`);draggedTaskId=null;setTimeout(load,400)}
  catch(err){toast(err.message,'err')}}
async function archiveTask(id){if(!confirm('Archive?'))return;
  try{const r=await api('/api/tasks/archive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:id})});
    if(r.ok)toast('Archived');setTimeout(load,300)}
  catch(e){toast(e.message,'err')}}
async function assignTask(id,profile){if(!profile)return;
  try{const r=await api('/api/tasks/assign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:id,profile})});
    if(r.ok)toast(`→ ${profile}`);setTimeout(load,300)}
  catch(e){toast(e.message,'err')}}
async function createTask(){const t=prompt('Task title?');if(!t)return;
  try{await api('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:t,status:'in_progress',assignee:'Hermes',priority:'normal'})});toast('Task created');setTimeout(load,400)}
  catch(e){toast(e.message,'err')}}

// ═══════════════════════════════════════════════════════════════
// SERVICES
// ═══════════════════════════════════════════════════════════════
function renderServices(){
  const svcs=D().services||[];
  if(!svcs.length){$('serviceCards').innerHTML='<div class="mc-empty">No services found.</div>';return}
  $('serviceCards').innerHTML=svcs.map(s=>`<article class="mc-card">
    <div class="mc-card-title">${badge(s.status,s.status)} ${esc(s.name)}</div>
    <div class="mc-card-meta">${esc(s.type)} · :${esc(s.port)} · ${esc(s.systemd_service)}</div>
    <div class="mc-card-meta">${esc(s.health?.summary||s.notes||'')}</div>
    <div class="mc-btn-group">
      <a href="${esc(s.public_url||s.url)}" target="_blank" class="mc-btn mc-btn-xs mc-btn-secondary">Open</a>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="navTo('logs-section');$('logServiceSelect').value='${esc(s.systemd_service)}';loadLogs('${esc(s.systemd_service)}')">Logs</button>
      ${(s.actions||[]).includes('restart_service')?`<button class="mc-btn mc-btn-xs mc-btn-secondary" data-confirm-action="restart_service" data-service="${esc(s.systemd_service)}">Restart</button>`:''}
    </div></article>`).join('');
}

// ═══════════════════════════════════════════════════════════════
// LOGS
// ═══════════════════════════════════════════════════════════════
function renderLogs(){
  const svcs=D().services||[];
  const sel=$('logServiceSelect');const cur=sel.value;
  sel.innerHTML=svcs.map(s=>`<option value="${esc(s.systemd_service)}">${esc(s.name)}</option>`).join('');
  if(cur)sel.value=cur;
  else if(svcs.length)sel.value=svcs[0].systemd_service;
  sel.onchange=function(){loadLogs(this.value)};
  if(svcs.length&&!$('logsOutput').textContent.includes('Select'))loadLogs(sel.value);
}

async function loadLogs(service){
  try{const r=await api(`/api/logs?service=${encodeURIComponent(service)}&lines=200`);
    const lines=(r.logs||'').split('\n').map(l=>{
      const lo=l.toLowerCase();
      if(lo.includes('error')||lo.includes('fail')||lo.includes('traceback'))return `<span class="err-line">${esc(l)}</span>`;
      if(lo.includes('warn'))return `<span class="warn-line">${esc(l)}</span>`;
      return esc(l);
    }).join('\n');
    $('logsOutput').innerHTML=lines||'No log output.'}
  catch(e){$('logsOutput').textContent='Failed: '+e.message}
}

// ═══════════════════════════════════════════════════════════════
// NIGHTLY BUILDS
// ═══════════════════════════════════════════════════════════════
function renderNightly(){
  const builds=D().nightly_builds||[];
  if(!builds.length){$('nightlyBuilds').innerHTML='<div class="mc-empty"><span class="mc-empty-icon">☾</span>No nightly builds yet.</div>';return}
  $('nightlyBuilds').innerHTML=builds.map(b=>{
    const chk=b.checklist||{};const done=Object.values(chk).filter(Boolean).length;const total=Object.keys(chk).length;
    return `<article class="mc-card">
      <div class="mc-card-title">${badge(b.status,b.status)} ${esc(b.name)}</div>
      <div class="mc-card-body">${esc(b.problem_solved||'')}</div>
      <div class="mc-card-meta">Checklist: ${done}/${total}</div>
      <div class="mc-card-meta">${Object.entries(chk).map(([k,v])=>`<span class="${v?'check-done':'check-pending'}">${v?'✓':'○'} ${k.replace(/_/g,' ')}</span>`).join(' · ')}</div>
      ${b.rollback?`<div class="mc-card-meta">Rollback: <code>${esc(b.rollback)}</code></div>`:''}
      <div class="mc-btn-group">
        ${['Testing','Good Candidate','Promoted','Rejected','Archived'].map(s=>`<button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="updateBuild('${esc(b.id)}','${s}')">${s}</button>`).join('')}
        <button class="mc-btn mc-btn-xs mc-btn-secondary" onclick="uploadFile('${esc(b.id)}')">📎</button>
      </div></article>`;
  }).join('');
}

async function createBuild(){const n=prompt('Nightly build name?');if(!n)return;
  try{await api('/api/nightly-builds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,status:'Built',problem_solved:'Registered from MC'})});toast('Build created');setTimeout(load,400)}
  catch(e){toast(e.message,'err')}}
async function updateBuild(id,status){const b=(D().nightly_builds||[]).find(x=>x.id===id);
  try{await api('/api/nightly-builds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...(b||{}),id,status})});toast(`→ ${status}`);setTimeout(load,400)}
  catch(e){toast(e.message,'err')}}
async function uploadFile(buildId){const inp=document.createElement('input');inp.type='file';inp.accept='image/*,.png,.jpg,.pdf,.txt,.md';
  inp.onchange=async()=>{const f=inp.files[0];if(!f||f.size>5_000_000){toast('File too large (max 5MB)','err');return}
    try{const buf=await f.arrayBuffer();const b64=btoa(String.fromCharCode(...new Uint8Array(buf)));
      const r=await api('/api/nightly-builds/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({build_id:buildId,filename:f.name,data:b64})});
      if(r.ok){toast(`Uploaded ${f.name}`);setTimeout(load,400)}else toast(r.error,'err')}
    catch(e){toast(e.message,'err')}};inp.click()}

// ═══════════════════════════════════════════════════════════════
// CRON
// ═══════════════════════════════════════════════════════════════
function renderCron(){
  const review=D().review_queue||[];
  const jobs=D().scheduled_tasks||[];
  $('reviewQueue').innerHTML=review.length?review.map(j=>`<article class="mc-card">
    <div class="mc-card-title">${badge('err','NEEDS REVIEW')} ${esc(j.name)}</div>
    <div class="mc-card-body">${esc(j.last_error||'Check run status')}</div>
    <div class="mc-btn-group">
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-confirm-action="run_cron" data-job="${esc(j.id)}">Run</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-safe-action="open_output" data-job="${esc(j.id)}">Output</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-safe-action="fix_prompt" data-job="${esc(j.id)}">Fix</button>
    </div></article>`).join(''):'<div class="mc-empty">✓ No review items.</div>';
  $('scheduledTasks').innerHTML=jobs.length?jobs.map(j=>`<article class="mc-card">
    <div class="mc-card-title">${esc(j.name)} <span class="mc-badge mc-badge-${j.enabled?'ok':'idle'}">${j.enabled?'enabled':'paused'}</span></div>
    <div class="mc-card-meta">${esc(j.schedule)} · ${esc(j.mode)} · ${esc(j.deliver)}</div>
    <div class="mc-card-meta">Last: ${fd(j.last_run_at)} · Next: ${fd(j.next_run_at)}</div>
    <div class="mc-btn-group">
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-confirm-action="run_cron" data-job="${esc(j.id)}">Run</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-confirm-action="${j.enabled?'pause_cron':'resume_cron'}" data-job="${esc(j.id)}">${j.enabled?'Pause':'Resume'}</button>
      <button class="mc-btn mc-btn-xs mc-btn-secondary" data-safe-action="open_output" data-job="${esc(j.id)}" ${j.has_output?'':'disabled'}>Output</button>
    </div></article>`).join(''):'';
}

// ═══════════════════════════════════════════════════════════════
// DOCS
// ═══════════════════════════════════════════════════════════════
function renderDocs(){
  const g=D().governance||{};
  const c=D().cost_tracker||{};
  const files=D().recent_files||[];
  $('governancePanel').innerHTML=`
    <div class="mc-card">
      <div class="mc-card-title">Governance</div>
      <div class="mc-card-meta">Score: ${esc(g.security_score)} · Posture: ${esc(g.posture)}</div>
      <div class="mc-card-meta">${(g.checks||[]).map(c=>`<div>${esc(c.label)}: ${esc(c.value)}</div>`).join('')}</div>
    </div>
    <div class="mc-card" style="margin-top:8px">
      <div class="mc-card-title">Cost</div>
      <div class="mc-card-meta">$${Number(c.estimated_cost_usd||0).toFixed(2)} · ${fmt(c.tokens)} tokens</div>
      ${(c.models||[]).map(m=>`<div class="mc-card-meta">${esc(m.model)}: ${esc(m.sessions)} sessions</div>`).join('')}
    </div>`;
  $('recentFiles').innerHTML=files.length?files.map(f=>`<div class="mc-activity-item"><span class="time">${fd(f.updated_at)}</span> ${esc(f.name)}</div>`).join(''):'<div class="mc-empty">No recent files.</div>';
}

// ═══════════════════════════════════════════════════════════════
// COMMAND PALETTE
// ═══════════════════════════════════════════════════════════════
const PALETTE_ACTIONS=[
  {label:'Go to Home',action:()=>navTo('home'),shortcut:'G H'},
  {label:'Go to Runs',action:()=>navTo('runs-section'),shortcut:'G R'},
  {label:'Go to Workflows',action:()=>navTo('workflows-section'),shortcut:'G W'},
  {label:'Go to Agents',action:()=>navTo('agents-section'),shortcut:'G A'},
  {label:'Go to Tasks',action:()=>navTo('tasks-section'),shortcut:'G T'},
  {label:'Go to Services',action:()=>navTo('services-section'),shortcut:'G S'},
  {label:'Go to Logs',action:()=>navTo('logs-section'),shortcut:'G L'},
  {label:'Create Workflow',action:()=>createWorkflow(),shortcut:''},
  {label:'Create Task',action:()=>createTask(),shortcut:''},
  {label:'Refresh All',action:()=>refresh(),shortcut:'R'},
  {label:'Send Summary',action:()=>sendSummary(),shortcut:''},
  {label:'Test Adapter',action:()=>runSafe('test_adapter'),shortcut:''},
];

function openPalette(){
  $('palette').classList.add('open');$('paletteBackdrop').classList.add('open');$('paletteInput').value='';$('paletteInput').focus();renderPaletteItems('')}
function closePalette(){$('palette').classList.remove('open');$('paletteBackdrop').classList.remove('open')}

function renderPaletteItems(query){
  const q=query.toLowerCase();const items=PALETTE_ACTIONS.filter(a=>a.label.toLowerCase().includes(q));
  $('paletteItems').innerHTML=items.map((a,i)=>`<div class="mc-palette-item ${i===0?'selected':''}" onclick="closePalette();${a.action.toString().replace(/^\(\)=>/,'')}">
    <span>${esc(a.label)}</span><span class="shortcut">${esc(a.shortcut)}</span></div>`).join('');
}

// ═══════════════════════════════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════════════════════════════
async function runSafe(action,extra={}){
  if(action==='create_workflow'){createWorkflow();return}
  try{const r=await api('/api/actions/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});
    const txt=r.prompt||r.content||r.output||r.logs||JSON.stringify(r,null,2);
    if(['refresh_all_status','create_task','update_task','move_task','archive_task','assign_task'].includes(action))setTimeout(load,400);
    if(r.ok)toast(action.replace(/_/g,' '));else toast(r.error||'Failed','err')}
  catch(e){toast(e.message,'err')}
}

let pendingApproval=null;
async function prepareConfirm(action,extra={}){
  try{const r=await api('/api/actions/prepare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});
    pendingApproval=r;const code=prompt(`${r.message}\n\nEnter approval code:`);
    if(!code)return;
    try{const r2=await api('/api/actions/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({approval_id:r.approval_id,approval_code:code})});
      if(r2.ok)toast('Action executed');else toast(r2.error,'err');setTimeout(load,800)}
    catch(e){toast(e.message,'err')}}
  catch(e){toast(e.message,'err')}
}

async function sendSummary(){try{await prepareConfirm('send_telegram_summary')}catch(e){toast(e.message,'err')}}

// ═══════════════════════════════════════════════════════════════
// EVENT HANDLERS
// ═══════════════════════════════════════════════════════════════
document.body.addEventListener('click',e=>{
  const safe=e.target.closest('[data-safe-action]');if(safe&&!safe.disabled){runSafe(safe.dataset.safeAction,{job_id:safe.dataset.job,service:safe.dataset.service,profile:safe.dataset.profile})}
  const conf=e.target.closest('[data-confirm-action]');if(conf&&!conf.disabled){prepareConfirm(conf.dataset.confirmAction,{job_id:conf.dataset.job,service:conf.dataset.service,profile:conf.dataset.profile})}
});
document.querySelectorAll('.mc-nav-item').forEach(btn=>btn.addEventListener('click',()=>navTo(btn.dataset.scroll)));
$('searchInput').addEventListener('input',e=>{/* future: filter within current section */});
$('showTestData').addEventListener('change',e=>{S.showTestData=e.target.checked;renderNeedsAttention();renderStatusHero()});
$('paletteInput').addEventListener('input',e=>renderPaletteItems(e.target.value));
$('paletteInput').addEventListener('keydown',e=>{if(e.key==='Enter'){const sel=document.querySelector('.mc-palette-item.selected');if(sel)sel.click()}});

document.addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette()}
  if(e.key==='Escape'&&!S.drawerOpen)closePalette();
});

// Profile mode
function setProfileMode(mode){
  $('profileSelect').disabled=(mode==='auto');if(mode==='auto')$('profileSelect').value='';
  api('/api/settings/profile-mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile_mode:mode})}).catch(()=>{})}
function setManualProfile(prof){if(!prof)return;
  api('/api/settings/profile-mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile_mode:'manual',default_profile:prof})}).catch(()=>{})}

async function refresh(){try{await load()}catch(e){toast(e.message,'err')}}

// Init
async function init(){
  try{
    await load();
    // Load profile mode
    const ps=await api('/api/settings/profile-mode');
    $('profileMode').value=ps.profile_mode||'auto';
    $('profileSelect').disabled=(ps.profile_mode!=='manual');
    if(ps.default_profile&&ps.default_profile!=='Default')$('profileSelect').value=ps.default_profile;
    // Load logs for first service
    const svcs=S.data?.services||[];
    if(svcs.length){$('logServiceSelect').value=svcs[0].systemd_service;loadLogs(svcs[0].systemd_service).catch(()=>{})}
    navTo('home');
  }catch(e){$('mainContent').insertAdjacentHTML('afterbegin',`<div class="mc-error-banner">⚠ ${esc(e.message)}</div>`)}
}
init();
setInterval(load,30000);
