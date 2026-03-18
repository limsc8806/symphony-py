from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from ..activity_log import ActivityLogStore
from ..alert_state import AlertStateStore
from ..models import CodexConfig
from ..runtime.codex_runner import CodexRunner
from ..thread_index import ThreadIndexStore
from .schemas import HealthResponse


def _require_admin(x_admin_token: str | None, expected: str | None) -> None:
    if expected and x_admin_token != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def _recommended_actions(alert: dict[str, Any]) -> list[dict[str, Any]]:
    kind = alert.get("kind")
    issue_id = alert.get("issue_id")
    thread_id = alert.get("thread_id")
    level = alert.get("level")
    actions: list[dict[str, Any]] = []

    def add(action: str, label: str, priority: int) -> None:
        actions.append({"action": action, "label": label, "priority": priority, "issue_id": issue_id, "thread_id": thread_id})

    if kind == "waiting_on_approval":
        add("detail", "Detail", 1)
        add("ack", "Acknowledge", 2)
        add("snooze_600", "Snooze 10m", 3)
        if issue_id:
            add("wake_issue", "Wake", 4)
    elif kind == "failed_thread":
        add("detail", "Detail", 1)
        if thread_id:
            add("rollback_1", "Rollback 1", 2)
            add("compact", "Compact", 3)
            add("archive", "Archive", 4)
    elif kind == "long_active_thread":
        add("detail", "Detail", 1)
        if thread_id:
            add("compact", "Compact", 2)
        add("ack", "Acknowledge", 3)
        add("snooze_1800", "Snooze 30m", 4)
    elif kind == "stale_watcher":
        add("detail", "Detail", 1)
        if issue_id:
            add("wake_issue", "Wake", 2)
        add("ack", "Acknowledge", 3)
        add("snooze_600", "Snooze 10m", 4)
    elif kind == "retry_hotspot":
        add("detail", "Detail", 1)
        if issue_id:
            add("wake_issue", "Wake", 2)
        add("ack", "Acknowledge", 3)
        add("snooze_1800", "Snooze 30m", 4)

    if level == "bad" and thread_id and kind in {"failed_thread", "long_active_thread"}:
        add("show_thread_activity", "Activity", 99)

    return sorted(actions, key=lambda x: x["priority"])


def _dashboard_html() -> str:
    return r"""
<!doctype html><html lang="ko"><head><meta charset="utf-8" />
<title>symphony-py ops</title><meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root { --bg:#0f1115; --panel:#171a21; --panel-2:#1d2230; --border:#2b3245; --text:#e8ecf3; --muted:#9aa4b2; --green:#7ee787; --yellow:#f2cc60; --red:#ff7b72; --blue:#79c0ff; --chip:#20283a; }
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif;} header{padding:18px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:12px;position:sticky;top:0;background:rgba(15,17,21,.95);backdrop-filter:blur(8px);z-index:10;} h1{margin:0;font-size:20px;} .muted{color:var(--muted);} .wrap{padding:18px 20px 32px;} .grid{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:14px;margin-bottom:16px;} .card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:14px;box-shadow:0 6px 18px rgba(0,0,0,.18);} .metric-label{color:var(--muted);font-size:12px;margin-bottom:8px;} .metric-value{font-size:26px;font-weight:700;} .row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;} .section-title{margin:0 0 12px 0;font-size:16px;display:flex;align-items:center;justify-content:space-between;gap:10px;} table{width:100%;border-collapse:collapse;font-size:13px;} th,td{border-bottom:1px solid var(--border);padding:9px 8px;text-align:left;vertical-align:top;} th{color:var(--muted);font-weight:600;font-size:12px;position:sticky;top:0;background:var(--panel);} .table-wrap{overflow:auto;max-height:420px;border:1px solid var(--border);border-radius:12px;} .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all;} .chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--chip);border:1px solid var(--border);font-size:12px;margin-right:4px;margin-bottom:4px;color:var(--text);} .ok{color:var(--green);} .warn{color:var(--yellow);} .bad{color:var(--red);} .info{color:var(--blue);} .toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;} button,input,select{background:var(--panel-2);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:8px 10px;font-size:13px;} button{cursor:pointer;} input[type=password],input[type=text]{min-width:220px;} .small{font-size:12px;color:var(--muted);} .pill{display:inline-flex;align-items:center;border-radius:999px;padding:3px 8px;font-size:12px;border:1px solid var(--border);background:var(--chip);} .banner{border-radius:12px;padding:12px 14px;margin-bottom:10px;border:1px solid var(--border);background:var(--panel);} .banner.warn{border-color:#6b5a1f;background:rgba(242,204,96,.10);} .banner.bad{border-color:#6b2a2a;background:rgba(255,123,114,.10);} .banner.ok{border-color:#245c34;background:rgba(126,231,135,.10);} .highlight-item{border-bottom:1px solid var(--border);padding:8px 0;} .highlight-item:last-child{border-bottom:none;} dialog{width:min(1000px,92vw);border:1px solid var(--border);border-radius:16px;background:var(--panel);color:var(--text);padding:0;} dialog::backdrop{background:rgba(0,0,0,.55);} .modal-head,.modal-body{padding:16px;} .modal-head{border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;} pre{white-space:pre-wrap;word-break:break-word;} .footer-note{margin-top:16px;color:var(--muted);font-size:12px;} .toast{min-width:280px;max-width:420px;border-radius:12px;padding:12px 14px;border:1px solid var(--border);background:var(--panel);box-shadow:0 10px 24px rgba(0,0,0,.28);} .toast.ok{border-color:#245c34;background:rgba(126,231,135,.10);} .toast.warn{border-color:#6b5a1f;background:rgba(242,204,96,.10);} .toast.bad{border-color:#6b2a2a;background:rgba(255,123,114,.10);} @media (max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(180px,1fr));}.row{grid-template-columns:1fr;}} @media (max-width:640px){.grid{grid-template-columns:1fr;}header{flex-direction:column;align-items:stretch;}}
</style></head><body>
<header><div><h1>symphony-py ops</h1><div class="small">운영 조회 + 관리자 액션</div></div><div class="toolbar"><input id="adminToken" type="password" placeholder="Admin token" /><button onclick="saveAdminToken()">Token 저장</button><button onclick="refreshAll()">새로고침</button><label class="small"><input id="autoRefresh" type="checkbox" checked />자동 새로고침</label><label class="small"><input id="includeSuppressedAlerts" type="checkbox" onchange="refreshAll()" />suppressed 포함</label></div></header>
<div class="wrap"><div id="warningBanners" style="margin-bottom:16px;"></div><div id="eventHighlights" class="card" style="margin-bottom:16px;"><div class="section-title"><span>New Highlights</span></div><div id="eventHighlightsBody"></div></div><div class="grid"><div class="card"><div class="metric-label">Health</div><div id="metricHealth" class="metric-value">-</div></div><div class="card"><div class="metric-label">Running Issues</div><div id="metricRunning" class="metric-value">0</div></div><div class="card"><div class="metric-label">Watching Issues</div><div id="metricWatching" class="metric-value">0</div></div><div class="card"><div class="metric-label">Loaded Threads</div><div id="metricLoaded" class="metric-value">0</div></div></div>
<div class="row"><div class="card"><div class="section-title"><span>State Snapshot</span></div><details open><summary>state JSON</summary><pre id="stateJson"></pre></details></div><div class="card"><div class="section-title"><span>Retry Queue</span></div><div class="table-wrap"><table><thead><tr><th>Issue ID</th><th>Attempts</th><th>Next Allowed</th><th>Action</th></tr></thead><tbody id="retryTable"></tbody></table></div></div></div>
<div class="card" style="margin-bottom:16px;"><div class="section-title"><span>Issues</span></div><div class="table-wrap"><table><thead><tr><th>Issue</th><th>Title</th><th>Status</th><th>Thread</th><th>Archived</th><th>PR</th></tr></thead><tbody id="issuesTable"></tbody></table></div></div>
<div class="card"><div class="section-title"><span>Threads</span><div class="toolbar"><input id="threadSearch" type="text" placeholder="thread / issue / title 검색" /><input id="threadIssueFilter" type="text" placeholder="issue identifier 예: CORE-12" /><select id="threadArchived" onchange="loadThreads()"><option value="false">Active</option><option value="true">Archived</option></select><select id="threadSortKey" onchange="loadThreads()"><option value="updated_at">updated_at</option><option value="created_at">created_at</option></select><label class="small"><input id="loadedOnly" type="checkbox" onchange="loadThreads()" />loaded only</label><button onclick="loadThreads()">적용</button></div></div><div class="table-wrap"><table><thead><tr><th>Thread</th><th>Status</th><th>Issue</th><th>Name</th><th>Updated</th><th>Actions</th></tr></thead><tbody id="threadsTable"></tbody></table></div><div class="toolbar" style="margin-top:10px;"><button id="nextThreadsBtn" onclick="loadNextThreads()">다음 페이지</button><span id="threadsCursorInfo" class="small"></span></div></div>
<div class="card" style="margin-top:16px;"><div class="section-title"><span>Recent Activity</span></div><div id="recentActivity"></div></div>
</div>
<dialog id="threadDialog"><div class="modal-head"><strong>Thread Detail</strong><button onclick="closeThreadDialog()">닫기</button></div><div class="modal-body"><div id="threadQuickActions" style="margin-bottom:10px;"></div><div class="grid" style="grid-template-columns:1fr 1fr;"><div class="card"><h3 style="margin-top:0;">Thread Summary</h3><pre id="threadSummary"></pre></div><div class="card"><h3 style="margin-top:0;">Mapped Issue</h3><pre id="threadMappedIssue"></pre></div></div><div class="card" style="margin-top:16px;"><h3 style="margin-top:0;">Turns</h3><div class="table-wrap"><table><thead><tr><th>#</th><th>Turn ID</th><th>Status</th><th>Summary</th></tr></thead><tbody id="threadTurnsTable"></tbody></table></div></div><div class="card" style="margin-top:16px;"><h3 style="margin-top:0;">Activity Feed</h3><div id="threadActivityFeed"></div></div><details style="margin-top:16px;"><summary>Raw JSON</summary><pre id="threadDetail"></pre></details></div></dialog>
<div id="toastRoot" style="position:fixed;right:20px;bottom:20px;display:flex;flex-direction:column;gap:10px;z-index:9999;"></div>
<script>
let cache={state:null,issues:null,threads:null,loaded:null,health:null,activity:null,alerts:null,highlights:null};
const pendingActions=new Set();
function adminToken(){return localStorage.getItem('symphony_admin_token')||'';}
function saveAdminToken(){localStorage.setItem('symphony_admin_token',document.getElementById('adminToken').value||'');alert('Admin token 저장됨');}
function initToken(){document.getElementById('adminToken').value=adminToken();}
function escapeHtml(str){return String(str).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');}
function fmtTs(ts){if(!ts)return '-'; try{return new Date(ts*1000).toLocaleString();}catch{return String(ts);}}
function badgeForStatus(status){const s=typeof status==='string'?status:(status?.type||'-'); let cls='info'; if(['completed','success','idle'].includes(s)) cls='ok'; if(['failed','interrupted'].includes(s)) cls='bad'; if(['active','inProgress','rollingBack','archiving','unarchiving'].includes(s)) cls='warn'; return `<span class="pill ${cls}">${escapeHtml(String(s))}</span>`;}
async function getJson(url, options={}){const res=await fetch(url, options); const text=await res.text(); try{const data=text?JSON.parse(text):{}; if(!res.ok){return {error:data.detail||(`${res.status} ${res.statusText}`)};} return data;}catch{if(!res.ok)return {error:`${res.status} ${res.statusText}`}; return {raw:text};}}
function pushToast(message, level='ok', ttl=3000){const root=document.getElementById('toastRoot'); const div=document.createElement('div'); div.className=`toast ${level}`; div.innerHTML=`<div style="display:flex; justify-content:space-between; gap:8px; align-items:flex-start;"><div>${escapeHtml(message)}</div><button onclick="this.parentElement.parentElement.remove()">닫기</button></div>`; root.appendChild(div); setTimeout(()=>div.remove(), ttl);}
async function postAdmin(url, options={}){const {optimistic=null, rollback=null, successMessage='작업 완료', failureMessage='작업 실패'}=options; if(optimistic){try{optimistic();}catch{}} const data=await getJson(url,{method:'POST',headers:{'x-admin-token':adminToken()}}); if(data.error){if(rollback){try{rollback();}catch{}} pushToast(`${failureMessage}: ${data.error}`,'bad',5000); return {ok:false,error:data.error};} pushToast(successMessage,'ok',2500); await refreshAll(); return {ok:true,data};}
async function withPending(key, fn){if(pendingActions.has(key))return; pendingActions.add(key); try{return await fn();} finally{pendingActions.delete(key);}}
function mutateThreadRow(threadId, updater){const items=cache.threads?.items||[]; const idx=items.findIndex(x=>x.thread?.id===threadId); if(idx===-1)return null; const prev=JSON.parse(JSON.stringify(items[idx])); updater(items[idx]); renderThreads(); return ()=>{items[idx]=prev; renderThreads();};}
function renderMetrics(){document.getElementById('metricHealth').textContent=cache.health?.ok?'OK':'ERR'; document.getElementById('metricHealth').className='metric-value '+(cache.health?.ok?'ok':'bad'); document.getElementById('metricRunning').textContent=(cache.state?.running_issue_ids||[]).length; document.getElementById('metricWatching').textContent=(cache.state?.watching_issue_ids||[]).length; document.getElementById('metricLoaded').textContent=(cache.loaded?.items||[]).length;}
function renderState(){document.getElementById('stateJson').textContent=JSON.stringify(cache.state||{},null,2); const retry=cache.state?.retry||{}; const tbody=document.getElementById('retryTable'); tbody.innerHTML=''; Object.entries(retry).forEach(([issueId,row])=>{const tr=document.createElement('tr'); tr.innerHTML=`<td class="mono">${escapeHtml(issueId)}</td><td>${escapeHtml(row.attempts??'-')}</td><td>${fmtTs(row.next_allowed_at)}</td><td><button onclick="wakeIssue('${issueId}')">Wake</button></td>`; tbody.appendChild(tr);});}
function renderIssues(){const tbody=document.getElementById('issuesTable'); tbody.innerHTML=''; (cache.issues?.items||[]).forEach((row)=>{const tr=document.createElement('tr'); tr.innerHTML=`<td class="mono">${escapeHtml(row.issue_identifier||row.issue_id||'-')}</td><td>${escapeHtml(row.title||'-')}</td><td>${badgeForStatus(row.status)}</td><td class="mono">${escapeHtml(row.thread_id||'-')}</td><td>${row.archived?'<span class="pill warn">yes</span>':'<span class="pill ok">no</span>'}</td><td>${row.pr_url?`<a href="${row.pr_url}" target="_blank" rel="noreferrer">open</a>`:'-'}</td>`; tbody.appendChild(tr);});}
function renderThreads(){const tbody=document.getElementById('threadsTable'); tbody.innerHTML=''; const items=cache.threads?.items||[]; items.forEach((row)=>{const t=row.thread||{}; const mapped=row.mapped_issue||{}; const threadId=t.id||'-'; const issueId=mapped.issue_identifier||'-'; const issueRowId=mapped.issue_id||''; const updated=fmtTs(t.updatedAt); const status=t.status||{}; const activeFlags=status.activeFlags||[]; const flagsHtml=activeFlags.map(x=>`<span class="chip">${escapeHtml(x)}</span>`).join(''); const isArchivedView=document.getElementById('threadArchived').value==='true'; const actionButtons=[`<button onclick="showThread('${threadId}')">Detail</button>`, isArchivedView?`<button onclick="unarchiveThread('${threadId}')">Unarchive</button>`:`<button onclick="archiveThread('${threadId}')">Archive</button>`, `<button onclick="compactThread('${threadId}')">Compact</button>`, `<button onclick="rollbackThreadWithTurns('${threadId}',1)">Rollback</button>`, issueRowId?`<button onclick="wakeIssue('${issueRowId}')">Wake Issue</button>`:''].join(' '); const tr=document.createElement('tr'); tr.innerHTML=`<td class="mono">${escapeHtml(threadId)}</td><td>${badgeForStatus(status)}<div style="margin-top:4px;">${flagsHtml}</div></td><td class="mono">${escapeHtml(issueId)}</td><td>${escapeHtml(t.name||t.preview||'-')}</td><td>${updated}</td><td>${actionButtons}</td>`; tbody.appendChild(tr);}); const nextCursor=cache.threads?.next_cursor||''; document.getElementById('threadsCursorInfo').textContent=nextCursor?'next_cursor 있음':'마지막 페이지'; document.getElementById('nextThreadsBtn').disabled=!nextCursor;}
function renderRecentActivity(){const root=document.getElementById('recentActivity'); root.innerHTML=''; (cache.activity?.items||[]).forEach((item)=>{const div=document.createElement('div'); div.className='card'; div.style.marginBottom='8px'; div.innerHTML=`<div style="display:flex; justify-content:space-between; gap:8px;"><strong>${escapeHtml(item.kind||'-')}</strong><span class="small">${fmtTs(item.ts)}</span></div><div style="margin-top:6px;">${escapeHtml(item.message||'-')}</div><div class="small" style="margin-top:6px;">issue=${escapeHtml(item.issue_identifier||item.issue_id||'-')} / thread=${escapeHtml(item.thread_id||'-')}</div>`; root.appendChild(div);});}
function renderWarningBanners(){const root=document.getElementById('warningBanners'); root.innerHTML=''; const items=cache.alerts?.items||[]; if(!items.length){root.innerHTML='<div class="banner ok">문제 thread 경고 없음</div>'; return;} items.forEach((item)=>{const div=document.createElement('div'); div.className=`banner ${item.level||'warn'}`; const buttons=(item.recommended_actions||[]).map((a)=>`<button onclick="runRecommendedAction('${a.action}','${a.issue_id||''}','${a.thread_id||''}','${item.kind}')">${escapeHtml(a.label)}</button>`).join(' '); const ageText=item.meta?.age_seconds?` / age=${Math.floor(item.meta.age_seconds)}s`:item.meta?.watch_age_seconds?` / watch_age=${Math.floor(item.meta.watch_age_seconds)}s`:''; const suppressedChip=item.suppressed?`<span class="chip">suppressed</span>`:''; div.innerHTML=`<div style="display:flex; justify-content:space-between; gap:8px; align-items:flex-start;"><div><strong>${escapeHtml(item.title||item.kind||'alert')}</strong> ${suppressedChip}<div class="small" style="margin-top:4px;">issue=${escapeHtml(item.issue_identifier||item.issue_id||'-')} / thread=${escapeHtml(item.thread_id||'-')} ${escapeHtml(ageText)}</div></div><div style="display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end;">${buttons}</div></div><details style="margin-top:8px;"><summary>meta</summary><pre>${escapeHtml(JSON.stringify(item.meta||{},null,2))}</pre></details>`; root.appendChild(div);});}
function renderEventHighlights(){const root=document.getElementById('eventHighlightsBody'); root.innerHTML=''; const items=cache.highlights?.items||[]; if(!items.length){root.innerHTML='<div class="small">최근 30초 새 이벤트 없음</div>'; return;} items.forEach((item)=>{const div=document.createElement('div'); div.className='highlight-item'; const emphKinds=new Set(['watcher_ready','watcher_started','admin_compact','admin_rollback']); if(emphKinds.has(item.kind)){div.style.background='rgba(121, 192, 255, 0.08)'; div.style.borderRadius='10px'; div.style.padding='8px';} div.innerHTML=`<div style="display:flex; justify-content:space-between; gap:8px;"><strong>${escapeHtml(item.kind||'-')}</strong><span class="small">${fmtTs(item.ts)}</span></div><div style="margin-top:4px;">${escapeHtml(item.message||'-')}</div><div class="small" style="margin-top:4px;">issue=${escapeHtml(item.issue_identifier||item.issue_id||'-')} / thread=${escapeHtml(item.thread_id||'-')}</div>`; root.appendChild(div);});}
async function loadThreads(cursor=null){const archived=document.getElementById('threadArchived').value; const q=document.getElementById('threadSearch').value||''; const issueIdentifier=document.getElementById('threadIssueFilter').value||''; const sortKey=document.getElementById('threadSortKey').value||'updated_at'; const loadedOnly=document.getElementById('loadedOnly').checked?'true':'false'; const params=new URLSearchParams({archived,sort_key:sortKey,loaded_only:loadedOnly}); if(q.trim()) params.set('q', q.trim()); if(issueIdentifier.trim()) params.set('issue_identifier', issueIdentifier.trim()); if(cursor) params.set('cursor', cursor); cache.threads=await getJson(`/threads?${params.toString()}`); renderThreads();}
async function loadNextThreads(){const nextCursor=cache.threads?.next_cursor; if(!nextCursor)return; await loadThreads(nextCursor);} 
async function showThread(threadId){const data=await getJson(`/threads/${threadId}`); document.getElementById('threadDetail').textContent=JSON.stringify(data,null,2); document.getElementById('threadSummary').textContent=JSON.stringify(data.thread||{},null,2); document.getElementById('threadMappedIssue').textContent=JSON.stringify(data.mapped_issue||{},null,2); renderThreadQuickActions(threadId, data.mapped_issue||{}); const turnsBody=document.getElementById('threadTurnsTable'); turnsBody.innerHTML=''; (data.turns||[]).forEach((turn)=>{const tr=document.createElement('tr'); tr.innerHTML=`<td>${turn.seq??'-'}</td><td class="mono">${escapeHtml(turn.id||'-')}</td><td>${badgeForStatus(turn.status)}</td><td>${escapeHtml(turn.summary||'-')}</td>`; turnsBody.appendChild(tr);}); const feed=document.getElementById('threadActivityFeed'); feed.innerHTML=''; (data.activity||[]).forEach((item)=>{const div=document.createElement('div'); div.className='card'; div.style.marginBottom='8px'; div.innerHTML=`<div style="display:flex; justify-content:space-between; gap:8px;"><strong>${escapeHtml(item.kind||'-')}</strong><span class="small">${fmtTs(item.ts)}</span></div><div style="margin-top:6px;">${escapeHtml(item.message||'-')}</div><details style="margin-top:6px;"><summary>meta</summary><pre>${escapeHtml(JSON.stringify(item.meta||{},null,2))}</pre></details>`; feed.appendChild(div);}); document.getElementById('threadDialog').showModal();}
function closeThreadDialog(){document.getElementById('threadDialog').close();}
function renderThreadQuickActions(threadId, mappedIssue){const root=document.getElementById('threadQuickActions'); const issueId=mappedIssue?.issue_id||''; root.innerHTML=`<button onclick="compactThread('${threadId}')">Compact</button> <button onclick="rollbackThreadWithTurns('${threadId}',1)">Rollback 1</button> <button onclick="archiveThread('${threadId}')">Archive</button> ${issueId?`<button onclick="wakeIssue('${issueId}')">Wake Issue</button>`:''}`;}
async function archiveThread(threadId){return withPending(`archive:${threadId}`, async ()=>{const rollback=mutateThreadRow(threadId,(row)=>{row.thread.status={type:'archiving'}; if(row.mapped_issue) row.mapped_issue.archived=true;}); const res=await postAdmin(`/admin/threads/${threadId}/archive`,{rollback,successMessage:`Thread ${threadId} archived`,failureMessage:`Thread ${threadId} archive failed`}); if(res.ok){cache.threads.items=(cache.threads.items||[]).filter((x)=>x.thread?.id!==threadId); renderThreads();}});}
async function unarchiveThread(threadId){return withPending(`unarchive:${threadId}`, async ()=>{const rollback=mutateThreadRow(threadId,(row)=>{row.thread.status={type:'unarchiving'}; if(row.mapped_issue) row.mapped_issue.archived=false;}); const res=await postAdmin(`/admin/threads/${threadId}/unarchive`,{rollback,successMessage:`Thread ${threadId} unarchived`,failureMessage:`Thread ${threadId} unarchive failed`}); if(res.ok){cache.threads.items=(cache.threads.items||[]).filter((x)=>x.thread?.id!==threadId); renderThreads();}});}
async function compactThread(threadId){return withPending(`compact:${threadId}`, async ()=>{const rollback=mutateThreadRow(threadId,(row)=>{row.thread.status={type:'active', activeFlags:['compacting']};}); await postAdmin(`/admin/threads/${threadId}/compact`,{rollback,successMessage:`Thread ${threadId} compaction started`,failureMessage:`Thread ${threadId} compaction failed`});});}
async function rollbackThreadWithTurns(threadId, turns){return withPending(`rollback:${threadId}:${turns}`, async ()=>{const rollback=mutateThreadRow(threadId,(row)=>{row.thread.status={type:'rollingBack'};}); await postAdmin(`/admin/threads/${threadId}/rollback?turns=${encodeURIComponent(turns)}`,{rollback,successMessage:`Thread ${threadId} rolled back by ${turns} turn(s)`,failureMessage:`Thread ${threadId} rollback failed`});});}
async function wakeIssue(issueId){const prevRetry=cache.state?.retry?JSON.parse(JSON.stringify(cache.state.retry)):{}; if(cache.state?.retry?.[issueId]){delete cache.state.retry[issueId]; renderState();} return withPending(`wake:${issueId}`, async ()=>{await postAdmin(`/admin/issues/${issueId}/wake`,{rollback:()=>{if(cache.state){cache.state.retry=prevRetry; renderState();}},successMessage:`Issue ${issueId} wake requested`,failureMessage:`Issue ${issueId} wake failed`});});}
async function ackAlert(kind, issueId, threadId){const prev=cache.alerts?JSON.parse(JSON.stringify(cache.alerts)):{items:[]}; if(cache.alerts?.items){cache.alerts.items=cache.alerts.items.filter((x)=>!(x.kind===kind&&(x.issue_id||'')===issueId&&(x.thread_id||'')===threadId)); renderWarningBanners();} const note=prompt('ack note','')||''; const qs=new URLSearchParams({kind}); if(issueId) qs.set('issue_id', issueId); if(threadId) qs.set('thread_id', threadId); if(note) qs.set('note', note); await postAdmin(`/admin/alerts/ack?${qs.toString()}`,{rollback:()=>{cache.alerts=prev; renderWarningBanners();},successMessage:'Alert acknowledged',failureMessage:'Alert acknowledge failed'});}
async function quickSnooze(kind, issueId, threadId, seconds){const prev=cache.alerts?JSON.parse(JSON.stringify(cache.alerts)):{items:[]}; if(cache.alerts?.items){cache.alerts.items=cache.alerts.items.filter((x)=>!(x.kind===kind&&(x.issue_id||'')===issueId&&(x.thread_id||'')===threadId)); renderWarningBanners();} const qs=new URLSearchParams({kind, seconds:String(seconds)}); if(issueId) qs.set('issue_id', issueId); if(threadId) qs.set('thread_id', threadId); await postAdmin(`/admin/alerts/snooze?${qs.toString()}`,{rollback:()=>{cache.alerts=prev; renderWarningBanners();},successMessage:`Alert snoozed for ${seconds}s`,failureMessage:'Alert snooze failed'});}
async function clearAlertState(kind, issueId, threadId){const qs=new URLSearchParams({kind}); if(issueId) qs.set('issue_id', issueId); if(threadId) qs.set('thread_id', threadId); await postAdmin(`/admin/alerts/clear?${qs.toString()}`,{successMessage:'Alert suppression cleared',failureMessage:'Clear failed'});}
async function runRecommendedAction(action, issueId, threadId, alertKind){if(action==='detail'&&threadId){await showThread(threadId); return;} if(action==='show_thread_activity'&&threadId){await showThread(threadId); return;} if(action==='ack'){await ackAlert(alertKind, issueId, threadId); return;} if(action==='snooze_600'){await quickSnooze(alertKind, issueId, threadId, 600); return;} if(action==='snooze_1800'){await quickSnooze(alertKind, issueId, threadId, 1800); return;} if(action==='wake_issue'&&issueId){await wakeIssue(issueId); return;} if(action==='compact'&&threadId){await compactThread(threadId); return;} if(action==='rollback_1'&&threadId){await rollbackThreadWithTurns(threadId,1); return;} if(action==='archive'&&threadId){await archiveThread(threadId); return;}}
async function refreshAll(){cache.health=await getJson('/health'); cache.state=await getJson('/state'); cache.issues=await getJson('/issues'); cache.loaded=await getJson('/threads/loaded'); const includeSuppressed=document.getElementById('includeSuppressedAlerts')?.checked?'true':'false'; cache.alerts=await getJson(`/alerts?include_suppressed=${includeSuppressed}`); cache.highlights=await getJson('/activity?limit=20&since_seconds=30'); cache.activity=await getJson('/activity?limit=30'); await loadThreads(); renderMetrics(); renderState(); renderIssues(); renderThreads(); renderRecentActivity(); renderWarningBanners(); renderEventHighlights();}
document.addEventListener('DOMContentLoaded', ()=>{initToken(); ['threadSearch','threadIssueFilter'].forEach((id)=>{const el=document.getElementById(id); if(!el)return; el.addEventListener('keydown',(e)=>{if(e.key==='Enter') loadThreads();});}); refreshAll(); setInterval(()=>{const auto=document.getElementById('autoRefresh'); if(auto && auto.checked) refreshAll();},5000);});
</script></body></html>
"""


def build_api(*, orchestrator: Any, workspace_root: str, thread_index_file: str, codex_config: CodexConfig, admin_token: str | None) -> FastAPI:
    app = FastAPI(title="symphony-py ops", version="0.3.0")
    runner = CodexRunner(codex_config)
    index = ThreadIndexStore(thread_index_file)
    workspace = Path(workspace_root).expanduser().resolve()
    activity = ActivityLogStore(workspace / "_activity_log.json")
    alert_state = AlertStateStore(Path(orchestrator.workflow.config.alert_state.state_file or (workspace / "_alert_state.json")))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(ok=True, service="symphony-py-ops", version="0.3.0")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard() -> str:
        return _dashboard_html()

    @app.get("/state")
    async def state() -> dict[str, Any]:
        return orchestrator.snapshot()

    @app.get("/issues")
    async def issues(q: str | None = None) -> dict[str, Any]:
        rows = list(index.all_issue_entries().values())
        if q:
            q_lower = q.lower().strip()
            rows = [row for row in rows if q_lower in " ".join([str(row.get("issue_identifier", "")), str(row.get("title", "")), str(row.get("thread_id", "")), str(row.get("status", ""))]).lower()]
        return {"items": rows}

    @app.get("/threads")
    async def threads(archived: bool = False, limit: int = 50, cursor: str | None = None, q: str | None = None, sort_key: str = "updated_at", issue_identifier: str | None = None, loaded_only: bool = False) -> dict[str, Any]:
        result = await runner.list_threads(workspace=workspace, archived=archived, limit=limit, cursor=cursor, cwd_filter=str(workspace), sort_key=sort_key)
        rows = result.get("data", [])
        loaded_ids: set[str] = set(await runner.list_loaded_threads(workspace=workspace)) if loaded_only else set()
        enriched = []
        q_lower = q.lower().strip() if q else None
        for row in rows:
            mapped = index.get_by_thread_id(row["id"])
            if loaded_only and row["id"] not in loaded_ids:
                continue
            if issue_identifier and (mapped or {}).get("issue_identifier", "") != issue_identifier:
                continue
            if q_lower:
                haystack = " ".join([str(row.get("id", "")), str(row.get("name", "")), str(row.get("preview", "")), str((mapped or {}).get("issue_identifier", "")), str((mapped or {}).get("title", ""))]).lower()
                if q_lower not in haystack:
                    continue
            enriched.append({"thread": row, "mapped_issue": mapped})
        return {"items": enriched, "next_cursor": result.get("nextCursor")}

    @app.get("/threads/loaded")
    async def loaded_threads() -> dict[str, Any]:
        return {"items": await runner.list_loaded_threads(workspace=workspace)}

    @app.get("/threads/{thread_id}")
    async def thread_detail(thread_id: str) -> dict[str, Any]:
        mapped = index.get_by_thread_id(thread_id)
        if not mapped:
            raise HTTPException(status_code=404, detail="thread not found in local index")
        thread = await runner.inspect_thread(workspace=workspace, thread_id=thread_id, include_turns=True)
        turns = thread.get("turns", []) or []
        normalized_turns = [{"seq": idx, "id": turn.get("id"), "status": turn.get("status"), "summary": turn.get("summary"), "createdAt": turn.get("createdAt"), "updatedAt": turn.get("updatedAt")} for idx, turn in enumerate(turns, start=1)]
        return {"thread": thread, "mapped_issue": mapped, "turns": normalized_turns, "activity": activity.list_for_thread(thread_id=thread_id, limit=100)}

    @app.get("/activity")
    async def all_activity(limit: int = 100, since_seconds: int | None = None) -> dict[str, Any]:
        items = activity.list_all(limit=max(limit, 300))
        if since_seconds is not None:
            cutoff = time.time() - since_seconds
            items = [x for x in items if float(x.get("ts", 0)) >= cutoff]
        return {"items": items[:limit]}

    @app.get("/alerts")
    async def alerts(include_suppressed: bool = False) -> dict[str, Any]:
        now = time.time()
        cfg = orchestrator.workflow.config.alerting
        snapshot = orchestrator.snapshot()
        retry = snapshot.get("retry", {})
        items: list[dict[str, Any]] = []
        for issue_id, row in retry.items():
            attempts = int(row.get("attempts", 0))
            idx_row = index.get_by_issue_id(issue_id)
            level = None
            if attempts >= cfg.retry_bad_attempts:
                level = "bad"
            elif attempts >= cfg.retry_warn_attempts:
                level = "warn"
            if level:
                items.append({"level": level, "kind": "retry_hotspot", "title": f"Retry attempts elevated: {attempts}", "issue_id": issue_id, "issue_identifier": (idx_row or {}).get("issue_identifier"), "thread_id": (idx_row or {}).get("thread_id"), "meta": row})
        for issue_id, row in index.all_issue_entries().items():
            thread_id = row.get("thread_id")
            status_type = row.get("last_status_type")
            flags = row.get("last_active_flags", []) or []
            status_changed_at = float(row.get("status_changed_at") or row.get("updated_at") or now)
            age = max(0, now - status_changed_at)
            if status_type == "active" and "waitingOnApproval" in flags:
                level = "bad" if age >= cfg.waiting_on_approval_bad_after_seconds else "warn" if age >= cfg.waiting_on_approval_warn_after_seconds else None
                if level:
                    items.append({"level": level, "kind": "waiting_on_approval", "title": f"Thread waiting on approval for {int(age)}s", "issue_id": issue_id, "issue_identifier": row.get("issue_identifier"), "thread_id": thread_id, "meta": {"age_seconds": age, "activeFlags": flags}})
            elif status_type == "active":
                level = "bad" if age >= cfg.active_thread_bad_after_seconds else "warn" if age >= cfg.active_thread_warn_after_seconds else None
                if level:
                    items.append({"level": level, "kind": "long_active_thread", "title": f"Thread active for {int(age)}s", "issue_id": issue_id, "issue_identifier": row.get("issue_identifier"), "thread_id": thread_id, "meta": {"age_seconds": age, "activeFlags": flags}})
            watch_started_at = row.get("watch_started_at")
            if watch_started_at:
                watch_age = max(0, now - float(watch_started_at))
                level = "bad" if watch_age >= cfg.watcher_bad_after_seconds else "warn" if watch_age >= cfg.watcher_warn_after_seconds else None
                if level:
                    items.append({"level": level, "kind": "stale_watcher", "title": f"Watcher active for {int(watch_age)}s", "issue_id": issue_id, "issue_identifier": row.get("issue_identifier"), "thread_id": thread_id, "meta": {"watch_age_seconds": watch_age}})
            if row.get("status") == "failed" and not row.get("archived"):
                items.append({"level": "bad", "kind": "failed_thread", "title": "Failed thread still active in catalog", "issue_id": issue_id, "issue_identifier": row.get("issue_identifier"), "thread_id": thread_id, "meta": {"status": row.get("status")}})
        dedup: dict[tuple[Any, Any, Any], dict[str, Any]] = {}
        for item in items:
            key = (item["kind"], item.get("issue_id"), item.get("thread_id"))
            dedup[key] = item
        final_items = []
        for item in dedup.values():
            kind = item.get("kind")
            issue_id = item.get("issue_id")
            thread_id = item.get("thread_id")
            suppressed = False
            suppression = None
            if orchestrator.workflow.config.alert_state.enabled:
                suppressed = alert_state.is_suppressed(kind=kind, issue_id=issue_id, thread_id=thread_id)
                suppression = alert_state.get_state(kind=kind, issue_id=issue_id, thread_id=thread_id)
            item["suppression"] = suppression
            item["recommended_actions"] = _recommended_actions(item)
            if include_suppressed or not suppressed:
                item["suppressed"] = suppressed
                final_items.append(item)
        return {"items": final_items}

    @app.post("/admin/issues/{issue_id}/wake")
    async def admin_wake_issue(issue_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        if issue_id in orchestrator._retry:
            orchestrator._retry[issue_id].next_allowed_at = 0.0
        orchestrator._wake_event.set()
        activity.append(kind="admin_wake_issue", message="admin requested wake", issue_id=issue_id)
        return {"ok": True, "issue_id": issue_id, "action": "wake"}

    @app.post("/admin/threads/{thread_id}/archive")
    async def admin_archive_thread(thread_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        mapped = index.get_by_thread_id(thread_id)
        if not mapped:
            raise HTTPException(status_code=404, detail="thread not found in local index")
        workspace_for_thread = workspace / mapped["issue_identifier"]
        await runner.archive_thread(workspace=workspace_for_thread, thread_id=thread_id)
        index.mark_archived(thread_id, archived=True)
        activity.append(kind="admin_archive", message="admin archived thread", thread_id=thread_id, issue_id=mapped.get("issue_id"), issue_identifier=mapped.get("issue_identifier"))
        return {"ok": True, "thread_id": thread_id, "action": "archive"}

    @app.post("/admin/threads/{thread_id}/unarchive")
    async def admin_unarchive_thread(thread_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        mapped = index.get_by_thread_id(thread_id)
        if not mapped:
            raise HTTPException(status_code=404, detail="thread not found in local index")
        workspace_for_thread = workspace / mapped["issue_identifier"]
        thread = await runner.unarchive_thread(workspace=workspace_for_thread, thread_id=thread_id)
        index.mark_archived(thread_id, archived=False)
        activity.append(kind="admin_unarchive", message="admin unarchived thread", thread_id=thread_id, issue_id=mapped.get("issue_id"), issue_identifier=mapped.get("issue_identifier"))
        return {"ok": True, "thread_id": thread_id, "action": "unarchive", "thread": thread}

    @app.post("/admin/threads/{thread_id}/compact")
    async def admin_compact_thread(thread_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        mapped = index.get_by_thread_id(thread_id)
        if not mapped:
            raise HTTPException(status_code=404, detail="thread not found in local index")
        workspace_for_thread = workspace / mapped["issue_identifier"]
        await runner.compact_thread(workspace=workspace_for_thread, thread_id=thread_id)
        activity.append(kind="admin_compact", message="admin started thread compaction", thread_id=thread_id, issue_id=mapped.get("issue_id"), issue_identifier=mapped.get("issue_identifier"))
        return {"ok": True, "thread_id": thread_id, "action": "compact-started"}

    @app.post("/admin/threads/{thread_id}/rollback")
    async def admin_rollback_thread(thread_id: str, turns: int = 1, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        mapped = index.get_by_thread_id(thread_id)
        if not mapped:
            raise HTTPException(status_code=404, detail="thread not found in local index")
        workspace_for_thread = workspace / mapped["issue_identifier"]
        thread = await runner.rollback_thread(workspace=workspace_for_thread, thread_id=thread_id, turns=turns)
        activity.append(kind="admin_rollback", message=f"admin rolled back {turns} turn(s)", thread_id=thread_id, issue_id=mapped.get("issue_id"), issue_identifier=mapped.get("issue_identifier"), meta={"turns": turns})
        return {"ok": True, "thread_id": thread_id, "action": "rollback", "thread": thread}

    @app.post("/admin/alerts/ack")
    async def admin_ack_alert(kind: str, issue_id: str | None = None, thread_id: str | None = None, note: str | None = None, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        alert_state.acknowledge(kind=kind, issue_id=issue_id, thread_id=thread_id, note=note)
        activity.append(kind="admin_alert_ack", message="admin acknowledged alert", issue_id=issue_id, thread_id=thread_id, meta={"alert_kind": kind, "note": note})
        return {"ok": True, "action": "ack", "kind": kind, "issue_id": issue_id, "thread_id": thread_id}

    @app.post("/admin/alerts/snooze")
    async def admin_snooze_alert(kind: str, issue_id: str | None = None, thread_id: str | None = None, seconds: int | None = None, note: str | None = None, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        ttl = seconds or orchestrator.workflow.config.alert_state.default_snooze_seconds
        alert_state.snooze(kind=kind, issue_id=issue_id, thread_id=thread_id, seconds=ttl, note=note)
        activity.append(kind="admin_alert_snooze", message="admin snoozed alert", issue_id=issue_id, thread_id=thread_id, meta={"alert_kind": kind, "seconds": ttl, "note": note})
        return {"ok": True, "action": "snooze", "kind": kind, "issue_id": issue_id, "thread_id": thread_id, "seconds": ttl}

    @app.post("/admin/alerts/clear")
    async def admin_clear_alert_state(kind: str, issue_id: str | None = None, thread_id: str | None = None, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(x_admin_token, admin_token)
        alert_state.clear(kind=kind, issue_id=issue_id, thread_id=thread_id)
        activity.append(kind="admin_alert_clear", message="admin cleared alert suppression", issue_id=issue_id, thread_id=thread_id, meta={"alert_kind": kind})
        return {"ok": True, "action": "clear", "kind": kind, "issue_id": issue_id, "thread_id": thread_id}

    return app
