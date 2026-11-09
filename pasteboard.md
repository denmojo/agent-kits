# Recipe: Pasteboard for Claude Code

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their machine, walk your user through the choices below and write nothing. In Phase 2 you build with their answers: copy each file exactly as given, change only the lines inside each file's Settings block, fill in the bracketed placeholders, show your user each file before you save it, and run the tests before you report it done.

## What it is

Long Claude Code sessions bury good answers. A useful reply scrolls away under the tool calls that follow it, and copying it out of a terminal brings hard line breaks along with it. Pasteboard is a small web page, served from the user's own machine, where chosen replies are posted word for word. Text always comes from the session transcript on disk, so a post is exactly what Claude wrote, never a retyped copy.

The page has a Board tab for new posts and a Saved tab for keepers. Each post carries a timestamp, a link to itself, and buttons for Raw, Copy, Save (or Move back on the Saved tab) and Clear. Posts render as markdown the way the terminal shows them. Any post can fold to its header line, the Saved tab opens folded so it reads as a list, and Collapse all and Expand all sit at the top. Changes appear in every open browser within about half a second with no reload.

Posts get there three ways:

- The user types `/pasteboard` (or "pasteboard that") and the skill posts Claude's previous reply, a reply further back, a range of turns, or a quoted prompt with its answer.
- Claude flags a reply it expects the user to want again while writing it, and a Stop hook posts that reply when the turn ends.
- Anything else goes in from the command line: `pasteboard post < file`.

## What it needs

- Claude Code. The tool reads its session transcripts from `~/.claude/projects/<project>/<session id>.jsonl` and the `CLAUDE_CODE_SESSION_ID` variable it sets in every shell it starts.
- Python 3.8 or newer, standard library only. Nothing to install.
- A service manager to keep the server up, unless the user would rather start it by hand: launchd on macOS, or a systemd user unit on Linux.
- Optional: Tailscale, to reach the page from a phone or another computer.
- Any current browser.

## Parts

Three scripts, a database the server creates on first use, an optional allow list, a skill and an optional Stop hook. Every location is a Phase 1 choice; the names below are the defaults.

| Part | Default location | Role |
| --- | --- | --- |
| `pasteboard-live` | `~/bin/` | The web server and the page, one file |
| `pasteboard` | `~/bin/` | Command-line tool: posts replies, ranges and files, lists, restores; also the Stop hook's entry point |
| `pasteboard-serve` | `~/bin/` | Launcher the service manager runs |
| `pasteboard.db` and `pending/` | `~/.local/share/pasteboard/` | SQLite database, and flags for replies waiting on the Stop hook |
| `allow` | `~/.config/pasteboard/` | List of LAN addresses allowed to open the page, only if the user wants LAN access |
| `SKILL.md` | `~/.claude/skills/pasteboard/` | The `/pasteboard` skill |
| Stop hook entry | `~/.claude/settings.json` | Posts a reply Claude flagged, once its turn ends |

## Phase 1: look, then ask

Write nothing in this phase.

Look at the machine first, so the defaults you offer fit it: the operating system; `command -v python3` and `python3 --version` (3.8 or newer, and note the full path); whether `~/bin` exists and is on `PATH`; whether `~/.local/share` and `~/.config` are in use; whether `tailscale` is installed; whether port 8795 is free (`lsof -nP -iTCP:8795 -sTCP:LISTEN` on macOS, `ss -ltn` on Linux); and whether `CLAUDE_CONFIG_DIR` is set, which moves the transcripts.

Then put this table in front of your user with the defaults filled in from what you found, and ask them to confirm each row or change it. Wait for their answer before Phase 2.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Folder for the three scripts | `~/bin` | `SCRIPTS` in `pasteboard-serve`; the service file; the hook command; the skill, if the folder isn't on `PATH` |
| 2 | Folder for the database | `~/.local/share/pasteboard` | `DATA_DIR` in both `pasteboard-live` and `pasteboard`, the same value in each; the log path in the service file |
| 3 | Who can open the page: this machine only, also the user's Tailscale devices, or also chosen LAN devices | This machine only | `BIND` in `pasteboard-serve` (`127.0.0.1` for this machine only, `0.0.0.0` otherwise); `ALLOW_TAILNET` in `pasteboard-live` |
| 4 | LAN allow list file and its addresses, only if row 3 includes LAN devices | `~/.config/pasteboard/allow` | `ALLOW_FILE` in `pasteboard-live` (`''` when unused); the file itself, one address per line, `#` for comments |
| 5 | Port | `8795`, or the next free one | `PORT` in `pasteboard-serve`; the page address in the skill |
| 6 | Python | The full path found above | `PYTHON` in `pasteboard-serve` |
| 7 | How it keeps running: launchd, systemd, or started by hand | launchd on macOS, systemd on Linux | Which service file to write, and its label or unit name |
| 8 | Page title | `Pasteboard` | `TITLE` in `pasteboard-live` |
| 9 | Name shown on the user's quoted prompts | `Me` | `PROMPT_LABEL` in `pasteboard` |
| 10 | Slash command name | `pasteboard` | The skill's folder name and its `name:` line |
| 11 | Let Claude post replies on its own initiative | Yes | Whether to add the Stop hook, and whether to keep the skill's "On your own initiative" section |
| 12 | Days a cleared post can be restored | `30` | `KEEP_DAYS` in `pasteboard-live` |
| 13 | Where Claude Code keeps transcripts | `~/.claude/projects`, or `$CLAUDE_CONFIG_DIR/projects` if that is set | `TRANSCRIPTS` in `pasteboard` |

On row 3, tell your user plainly that the page has no login. Whoever can reach it can read every post and clear them, and posts can quote private files. Keep it off the internet entirely, never put it behind Tailscale Funnel, and keep any LAN allow list to their own devices, since a LAN device can claim an allowed address.

## Phase 2: build

1. Create the scripts folder from row 1 if needed, save the three scripts below into it, edit only their Settings blocks to match the answers, and make them executable with `chmod +x`.
2. If row 3 includes LAN devices, write the allow file from row 4. The server reads it on every request, so later edits need no restart.
3. Create the database folder from row 2. Install the service from row 7 and start it, or start `pasteboard-serve` by hand. Confirm with `curl -s http://127.0.0.1:[PORT]/api/version`, which prints `{"version": 0}` on a fresh install.
4. If row 11 is yes, add the Stop hook to `~/.claude/settings.json`, merging into any existing `hooks.Stop` array rather than replacing it.
5. Save the skill under the name from row 10, with the page address and, if the scripts folder isn't on `PATH`, the full path to `pasteboard` in its commands.
6. Run the tests and report each result.

Save, Move back and Clear are POST requests that need an `X-Pasteboard: 1` header, which stops a form on some other website from clicking them. Clear hides a post for the days set in row 12, during which `pasteboard restore <id>` brings it back; after that the server deletes it.

## The server: `pasteboard-live`

Settings block: `DATA_DIR` (row 2), `ALLOW_FILE` (row 4), `ALLOW_TAILNET` (row 3), `KEEP_DAYS` (row 12), `TITLE` (row 8).

````python
#!/usr/bin/env python3
"""Pasteboard: a private message board for Claude's replies.

Serves one page plus a small JSON API from a SQLite file. Posts arrive from
the pasteboard command (which writes the database directly); /events pushes the
board's version to open pages over Server-Sent Events, and the page redraws
only the posts that changed.

States: board -> saved (Save), saved -> board (Move back), board|saved ->
cleared (Clear). Cleared rows are kept KEEP_DAYS days for recovery
(`pasteboard restore <id>`), then purged at startup and once a day.

Answers loopback, the tailnet when ALLOW_TAILNET is set, and the LAN
addresses in ALLOW_FILE (re-read on every request); everyone else gets 403.
The launcher picks the listening address. No login: this list is the only
lock, so never expose the port to the internet. Standard library only.
"""
import argparse, ipaddress, json, os, sqlite3, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# ---- Settings ----------------------------------------------------------
DATA_DIR = os.path.expanduser('~/.local/share/pasteboard')     # database; same as in the pasteboard command
ALLOW_FILE = os.path.expanduser('~/.config/pasteboard/allow')  # LAN addresses let in; '' for none
ALLOW_TAILNET = True    # answer any Tailscale address (100.64.0.0/10)
KEEP_DAYS = 30          # how long a cleared post can be restored before it is deleted
TITLE = 'Pasteboard'    # page and tab title
# ------------------------------------------------------------------------

ALWAYS = [ipaddress.ip_network('127.0.0.0/8'), ipaddress.ip_network('::1/128')]
if ALLOW_TAILNET:
    ALWAYS.append(ipaddress.ip_network('100.64.0.0/10'))


def allowed(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if getattr(a, 'ipv4_mapped', None):
        a = a.ipv4_mapped
    if any(a in n for n in ALWAYS):
        return True
    if not ALLOW_FILE:
        return False
    try:
        for line in open(ALLOW_FILE):
            tok = line.split('#', 1)[0].strip()
            if tok and a == ipaddress.ip_address(tok):
                return True
    except (OSError, ValueError):
        pass
    return False


DB = os.path.join(DATA_DIR, 'pasteboard.db')
SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL,          -- ISO 8601 local time with offset
  title TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT '', -- e.g. session id, 'manual'
  state TEXT NOT NULL DEFAULT 'board' CHECK (state IN ('board','saved','cleared')),
  changed TEXT NOT NULL           -- last state change
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v INTEGER NOT NULL);
INSERT OR IGNORE INTO meta VALUES ('version', 0);
"""


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def read_version():
    """Cheap read for the live stream: no schema script, read-only open."""
    try:
        c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=5)
        try:
            return c.execute("SELECT v FROM meta WHERE k='version'").fetchone()[0]
        finally:
            c.close()
    except sqlite3.Error:
        return -1


def bump(c):
    c.execute("UPDATE meta SET v = v + 1 WHERE k = 'version'")


def purge():
    cutoff = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() - KEEP_DAYS * 86400))
    with connect() as c:
        n = c.execute("DELETE FROM posts WHERE state='cleared' AND substr(changed,1,19) < ?", (cutoff,)).rowcount
        if n:
            bump(c)


def purge_loop():
    while True:
        time.sleep(86400)
        try:
            purge()
        except Exception as e:  # keep serving
            print('purge failed:', e, flush=True)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d1d1f;--mute:#6b6b70;--line:#dddbd5;--acc:#2f6f4f;--warn:#a33;--codebg:#f0eee9;}
@media (prefers-color-scheme: dark){:root{--bg:#141416;--card:#1e1e21;--fg:#e8e8ea;--mute:#9a9aa2;--line:#33333a;--acc:#6fbf8f;--warn:#e07070;--codebg:#2a2a2f;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:8px;align-items:center;z-index:2}
h1{font-size:17px;margin:0 12px 0 0}
.tab{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:5px 12px;border-radius:16px;cursor:pointer;font-size:14px}
.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.count{opacity:.75;margin-left:4px}
main{max-width:980px;margin:0 auto;padding:12px 16px 60px}
.post{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:12px 0;overflow:hidden}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);font-size:13px;color:var(--mute)}
.meta b{color:var(--fg);font-weight:600}
.meta .sp{flex:1}
button.act{border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:6px;padding:3px 10px;cursor:pointer;font-size:13px}
button.save{border-color:var(--acc);color:var(--acc)}
button.clear{border-color:var(--warn);color:var(--warn)}
pre.raw{margin:0;padding:12px;white-space:pre-wrap;word-wrap:break-word;font:13.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.md{padding:4px 14px 10px;overflow-wrap:anywhere}
.md p{margin:8px 0}.md h1,.md h2,.md h3,.md h4{margin:14px 0 6px;line-height:1.25}.md h1{font-size:20px}.md h2{font-size:18px}.md h3{font-size:16px}.md h4{font-size:15px}
.md ul,.md ol{margin:6px 0;padding-left:24px}.md li{margin:2px 0}
.md code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--codebg);padding:1px 4px;border-radius:4px}
.md pre{background:var(--codebg);padding:10px 12px;border-radius:6px;overflow-x:auto;margin:8px 0}
.md pre code{background:none;padding:0;white-space:pre}
.md blockquote{margin:8px 0;padding:2px 12px;border-left:3px solid var(--line);color:var(--mute)}
.md table{border-collapse:collapse;margin:8px 0;display:block;overflow-x:auto;font-size:14px}
.md th,.md td{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
.md th{background:var(--codebg)}
.md hr{border:0;border-top:1px solid var(--line);margin:12px 0}
.md a{color:var(--acc)}
.empty{color:var(--mute);text-align:center;margin-top:60px}
header{flex-wrap:wrap}
.tools{margin-left:auto;display:flex;gap:6px;align-items:center}
#live{font-size:12px;color:var(--mute);margin-right:4px}#live.on{color:var(--acc)}
.meta{cursor:pointer;user-select:none}
.chev{border:0;background:none;color:var(--mute);cursor:pointer;font-size:13px;padding:0 2px;transition:transform .15s}
.collapsed .chev{transform:rotate(-90deg)}
.collapsed .meta{border-bottom:0}
.collapsed .md,.collapsed pre.raw,.collapsed .sp{display:none}
a.num{color:var(--fg);font-weight:600;text-decoration:none}a.num:hover{text-decoration:underline}
.ttl{color:var(--fg)}
.prev{flex:1 1 160px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg)}
.post:not(.collapsed) .prev{display:none}
.post.hl{box-shadow:0 0 0 2px var(--acc)}
#notice{max-width:980px;margin:0 auto;padding:0 16px}
.notice{background:var(--card);border:1px solid var(--warn);color:var(--warn);border-radius:8px;padding:8px 12px;margin:12px 0}
</style></head><body>
<header><h1>{{TITLE}}</h1>
<button class="tab on" data-s="board">Board<span class="count" id="c-board"></span></button>
<button class="tab" data-s="saved">Saved<span class="count" id="c-saved"></span></button>
<span class="tools"><span id="live" title="Live updates">● live</span>
<button class="act" id="colall">Collapse all</button><button class="act" id="expall">Expand all</button></span>
</header>
<div id="notice"></div>
<main id="list"></main>
<script>
// Minimal markdown renderer (no third-party code): fences, headings, rules,
// quotes, tables, nested lists, paragraphs; inline code, bold, italic, strike,
// links and bare URLs. Text is HTML-escaped before any markup is added.
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function inl(s){
  const codes=[];
  s=s.replace(/`([^`]+)`/g,(m,c)=>{codes.push(c);return '\u0000'+(codes.length-1)+'\u0000';});
  s=esc(s);
  s=s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,(m,t,u)=>'<a href="'+u+'" target="_blank" rel="noopener">'+t+'</a>');
  s=s.replace(/(^|[\s(*])(https?:\/\/[^\s<)*]+[^\s<).,;:!?'"*])/g,'$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  s=s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g,'<strong>$1</strong>');
  s=s.replace(/(^|[^\w])__(?=\S)([\s\S]*?\S)__(?!\w)/g,'$1<strong>$2</strong>');
  s=s.replace(/(^|[^*\w])\*(?=[^\s*])([^*]*?[^\s*])\*(?![*\w])/g,'$1<em>$2</em>');
  s=s.replace(/(^|[^\w])_(?=[^\s_])([^_]*?[^\s_])_(?!\w)/g,'$1<em>$2</em>');
  s=s.replace(/~~(?=\S)([\s\S]*?\S)~~/g,'<del>$1</del>');
  return s.replace(/\u0000(\d+)\u0000/g,(m,i)=>'<code>'+esc(codes[+i])+'</code>');
}
const RE={fence:/^\s*(```|~~~)/,head:/^(#{1,6})\s+(.*?)\s*#*\s*$/,hr:/^\s*([-*_])(\s*\1){2,}\s*$/,
  quote:/^\s*>\s?/,item:/^(\s*)([-*+]|\d+[.)])\s+(.*)$/,tsep:/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/};
function cells(l){l=l.trim().replace(/^\|/,'').replace(/\|$/,'');return l.split(/(?<!\\)\|/).map(c=>c.trim().replace(/\\\|/g,'|'));}
function list(items,i,ind){
  const ord=/\d/.test(items[i].mark),start=ord?parseInt(items[i].mark):1;
  let h=ord?'<ol'+(start!==1?' start="'+start+'"':'')+'>':'<ul>';
  while(i<items.length&&items[i].ind>=ind&&!(items[i].ind===ind&&/\d/.test(items[i].mark)!==ord)){
    h+='<li>'+items[i].lines.map(inl).join('<br>');i++;
    if(i<items.length&&items[i].ind>ind){const r=list(items,i,items[i].ind);h+=r[0];i=r[1];}
    h+='</li>';
  }
  return [h+(ord?'</ol>':'</ul>'),i];
}
function md(src){
  const L=src.replace(/\r\n?/g,'\n').split('\n');let h='',i=0;
  const starts=l=>RE.fence.test(l)||RE.head.test(l)||RE.hr.test(l)||RE.quote.test(l)||RE.item.test(l);
  while(i<L.length){
    const l=L[i];
    if(!l.trim()){i++;continue;}
    let m;
    if((m=l.match(RE.fence))){const f=m[1];const buf=[];i++;
      while(i<L.length&&!L[i].trim().startsWith(f)){buf.push(L[i]);i++;}i++;
      h+='<pre><code>'+esc(buf.join('\n'))+'</code></pre>';continue;}
    if((m=l.match(RE.head))){const n=m[1].length;h+='<h'+n+'>'+inl(m[2])+'</h'+n+'>';i++;continue;}
    if(RE.hr.test(l)){h+='<hr>';i++;continue;}
    if(l.includes('|')&&i+1<L.length&&RE.tsep.test(L[i+1])){
      const hd=cells(l);i+=2;h+='<table><thead><tr>'+hd.map(c=>'<th>'+inl(c)+'</th>').join('')+'</tr></thead><tbody>';
      while(i<L.length&&L[i].includes('|')&&L[i].trim()){h+='<tr>'+cells(L[i]).map(c=>'<td>'+inl(c)+'</td>').join('')+'</tr>';i++;}
      h+='</tbody></table>';continue;}
    if(RE.quote.test(l)){const buf=[];while(i<L.length&&RE.quote.test(L[i])){buf.push(L[i].replace(RE.quote,''));i++;}
      h+='<blockquote>'+md(buf.join('\n'))+'</blockquote>';continue;}
    if(RE.item.test(l)){const items=[];
      while(i<L.length){const x=L[i];
        if((m=x.match(RE.item))){items.push({ind:m[1].replace(/\t/g,'    ').length,mark:m[2],lines:[m[3]]});i++;continue;}
        if(x.trim()&&/^\s+/.test(x)&&items.length&&!RE.fence.test(x)){items[items.length-1].lines.push(x.trim());i++;continue;}
        if(!x.trim()&&i+1<L.length&&RE.item.test(L[i+1])){i++;continue;}
        break;}
      const base=Math.min(...items.map(t=>t.ind));let j=0;
      while(j<items.length){const r=list(items,j,base);h+=r[0];j=r[1];}
      continue;}
    const buf=[];while(i<L.length&&L[i].trim()&&!(buf.length&&starts(L[i]))&&!(L[i].includes('|')&&i+1<L.length&&RE.tsep.test(L[i+1]))){buf.push(L[i]);i++;}
    h+='<p>'+buf.map(inl).join('<br>')+'</p>';
  }
  return h;
}
let state='board', version=-1, loading=null, again=false;
const nodes=new Map();            // post id -> {card, p}, for the tab on screen
const H={'Content-Type':'application/json','X-Pasteboard':'1'};
const L=document.getElementById('list');
// Collapse state per tab and post, kept in this browser; Saved defaults to collapsed.
let col={};try{col=JSON.parse(localStorage.getItem('pb-col')||'{}');}catch(e){}
function saveCol(){try{localStorage.setItem('pb-col',JSON.stringify(col));}catch(e){}}
function isCol(id){const k=state+':'+id;return k in col?col[k]:state==='saved';}
function setCol(id,v){col[state+':'+id]=v;saveCol();const n=nodes.get(id);if(n)n.card.classList.toggle('collapsed',v);}
function fmt(iso){const d=new Date(iso.replace(/([+-]\d\d)(\d\d)$/,'$1:$2'));
  return isNaN(d)?iso:d.toLocaleString(undefined,{weekday:'short',year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});}
function el(t,cls,txt){const e=document.createElement(t);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
function firstLine(p){const l=p.body.split('\n').find(x=>x.trim())||'';
  return l.replace(/\[([^\]]+)\]\([^)]+\)/g,'$1').replace(/[*_`#>|]/g,'').trim();}
function notice(t){const N=document.getElementById('notice');N.replaceChildren();if(t)N.appendChild(el('div','notice',t));}
async function act(id,what){await fetch('/api/posts/'+id+'/'+what,{method:'POST',headers:H});refresh();}
function build(p){
  const card=el('article','post'),m=el('div','meta');card.id='p'+p.id;
  const chev=el('button','chev','▾');chev.title='Collapse or expand';
  chev.onclick=()=>setCol(p.id,!card.classList.contains('collapsed'));
  const a=el('a','num','#'+p.id);a.href='#p'+p.id;a.title='Link to this post';
  m.append(chev,a,el('span',null,fmt(p.created)));
  if(p.title)m.appendChild(el('span','ttl','· '+p.title));
  if(p.state==='saved')m.appendChild(el('span',null,'· saved '+fmt(p.changed)));
  if(!p.title)m.appendChild(el('span','prev','· '+firstLine(p)));
  m.appendChild(el('span','sp'));
  const view=el('div','md');view.innerHTML=md(p.body);
  const raw=el('pre','raw',p.body);raw.hidden=true;
  const tg=el('button','act','Raw');
  tg.onclick=()=>{raw.hidden=!raw.hidden;view.hidden=!raw.hidden;tg.textContent=raw.hidden?'Raw':'Rendered';};
  const cp=el('button','act','Copy');
  cp.onclick=async()=>{try{await navigator.clipboard.writeText(p.body);cp.textContent='Copied';}catch(e){cp.textContent='Copy failed';}
    setTimeout(()=>cp.textContent='Copy',1200);};
  m.append(tg,cp);
  if(p.state==='board'){const s=el('button','act save','Save');s.onclick=()=>act(p.id,'save');m.appendChild(s);}
  else{const b=el('button','act save','Move back');b.title='Put this post back on the Board';b.onclick=()=>act(p.id,'unsave');m.appendChild(b);}
  const c=el('button','act clear','Clear');c.onclick=()=>act(p.id,'clear');m.appendChild(c);
  m.addEventListener('click',e=>{if(e.target.closest('button,a'))return;chev.click();});
  card.append(m,view,raw);
  return card;
}
async function load(){
  const r=await fetch('/api/posts?state='+state);const j=await r.json();
  document.getElementById('c-board').textContent=j.counts.board?'('+j.counts.board+')':'';
  document.getElementById('c-saved').textContent=j.counts.saved?'('+j.counts.saved+')':'';
  const want=new Set(j.posts.map(p=>p.id));
  for(const [id,n] of nodes)if(!want.has(id)){n.card.remove();nodes.delete(id);}
  const em=L.querySelector('.empty');if(em)em.remove();
  if(!j.posts.length){L.appendChild(el('p','empty',state==='board'?'Nothing on the board.':'Nothing saved.'));return;}
  let prev=null;
  for(const p of j.posts){
    let n=nodes.get(p.id);
    if(!n){n={card:build(p),p};nodes.set(p.id,n);}
    else if(n.p.changed!==p.changed||n.p.body!==p.body||n.p.title!==p.title){const c=build(p);n.card.replaceWith(c);n.card=c;n.p=p;}
    n.card.classList.toggle('collapsed',isCol(p.id));
    const ref=prev?prev.nextSibling:L.firstChild;if(n.card!==ref)L.insertBefore(n.card,ref);
    prev=n.card;
  }
}
// One load at a time; a change that arrives mid-load triggers one more.
async function refresh(){if(loading){again=true;return loading;}
  loading=(async()=>{do{again=false;try{await load();}catch(e){}}while(again);loading=null;})();return loading;}
async function tick(){try{const r=await fetch('/api/version');const j=await r.json();
  if(j.version!==version){version=j.version;await refresh();}}catch(e){}}
function setTab(s){state=s;document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x.dataset.s===s));
  nodes.clear();L.replaceChildren();}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{setTab(b.dataset.s);refresh();});
document.getElementById('colall').onclick=()=>{for(const id of nodes.keys())setCol(id,true);};
document.getElementById('expall').onclick=()=>{for(const id of nodes.keys())setCol(id,false);};
// #p<id>: switch to the post's tab, expand it, scroll to it.
async function follow(){
  const m=location.hash.match(/^#p(\d+)$/);if(!m){notice('');return;}
  const id=+m[1];
  try{const r=await fetch('/api/post/'+id);
    if(!r.ok){notice('Post #'+id+' does not exist.');return;}
    const p=await r.json();
    if(p.state==='cleared'){notice('Post #'+id+' was cleared. "pasteboard restore '+id+'" brings it back.');return;}
    notice('');
    if(p.state!==state)setTab(p.state);
    await refresh();setCol(id,false);
    const n=nodes.get(id);if(n){n.card.scrollIntoView({behavior:'smooth',block:'start'});
      n.card.classList.add('hl');setTimeout(()=>n.card.classList.remove('hl'),2500);}
  }catch(e){}
}
window.addEventListener('hashchange',follow);
// Live updates: the server pushes the version over Server-Sent Events; a slow poll backs it up.
const live=document.getElementById('live');
function stream(){if(!window.EventSource)return;
  const es=new EventSource('/events');
  es.onopen=()=>live.classList.add('on');
  es.onmessage=e=>{const v=+e.data;if(v!==version){version=v;refresh();}};
  es.onerror=()=>live.classList.remove('on');}
stream();
refresh().then(follow);
setInterval(tick,15000);
</script></body></html>
"""


class H(BaseHTTPRequestHandler):
    server_version = 'pasteboard'

    def log_message(self, fmt, *a):
        pass

    def send(self, code, body, ctype='application/json'):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def events(self):
        """Server-Sent Events: push the board version whenever it changes.

        The CLI writes the database directly, so each stream checks the version
        twice a second (one indexed read) and sends it on change, with a comment
        line every 15 s to keep proxies and sleeping tablets from dropping it.
        """
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        last, beat = None, time.time()
        try:
            self.wfile.write(b'retry: 3000\n\n')
            while True:
                v = read_version()
                if v != last:
                    self.wfile.write(f'data: {v}\n\n'.encode())
                    self.wfile.flush()
                    last, beat = v, time.time()
                elif time.time() - beat > 15:
                    self.wfile.write(b': ping\n\n')
                    self.wfile.flush()
                    beat = time.time()
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def gate(self):
        if allowed(self.client_address[0]):
            return True
        print(f'refused {self.client_address[0]} {self.command} {self.path}', flush=True)
        self.send(403, 'forbidden', 'text/plain')
        return False

    def do_GET(self):
        if not self.gate():
            return
        path, _, q = self.path.partition('?')
        if path == '/':
            return self.send(200, PAGE.replace('{{TITLE}}', TITLE), 'text/html')
        if path == '/api/version':
            return self.send(200, json.dumps({'version': read_version()}))
        if path == '/events':
            return self.events()
        if path.startswith('/api/post/') and path[10:].isdigit():
            with connect() as c:
                r = c.execute("SELECT id, state FROM posts WHERE id=?", (int(path[10:]),)).fetchone()
            return self.send(200, json.dumps(dict(r))) if r else self.send(404, '{"error":"no such post"}')
        if path == '/api/posts':
            st = 'saved' if 'state=saved' in q else 'board'
            order = 'changed DESC' if st == 'saved' else 'id DESC'
            with connect() as c:
                rows = [dict(r) for r in c.execute(f"SELECT * FROM posts WHERE state=? ORDER BY {order}", (st,))]
                counts = {s: c.execute("SELECT count(*) FROM posts WHERE state=?", (s,)).fetchone()[0] for s in ('board', 'saved')}
            return self.send(200, json.dumps({'posts': rows, 'counts': counts}))
        self.send(404, '{"error":"not found"}')

    def do_POST(self):
        if not self.gate():
            return
        # Custom header blocks cross-site form posts from other origins.
        if self.headers.get('X-Pasteboard') != '1':
            return self.send(403, '{"error":"missing header"}')
        parts = self.path.strip('/').split('/')
        # save: board -> saved; unsave: saved -> board ("Move back"); clear: board|saved -> cleared
        moves = {'save': ('saved', ('board',)), 'unsave': ('board', ('saved',)), 'clear': ('cleared', ('board', 'saved'))}
        if len(parts) == 4 and parts[:2] == ['api', 'posts'] and parts[2].isdigit() and parts[3] in moves:
            new, allowed = moves[parts[3]]
            with connect() as c:
                n = c.execute(f"UPDATE posts SET state=?, changed=? WHERE id=? AND state IN ({','.join('?' * len(allowed))})",
                              (new, now(), int(parts[2]), *allowed)).rowcount
                if n:
                    bump(c)
            return self.send(200 if n else 404, json.dumps({'ok': bool(n)}))
        self.send(404, '{"error":"not found"}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bind', required=True)
    ap.add_argument('--port', type=int, default=8795)
    a = ap.parse_args()
    purge()
    threading.Thread(target=purge_loop, daemon=True).start()
    print(f'pasteboard: serving http://{a.bind}:{a.port}/', flush=True)
    ThreadingHTTPServer((a.bind, a.port), H).serve_forever()


if __name__ == '__main__':
    main()
````

## The command-line tool: `pasteboard`

Settings block: `DATA_DIR` (row 2, same value as the server), `TRANSCRIPTS` (row 13), `PROMPT_LABEL` (row 9). A `PASTEBOARD_NAME` variable in the environment overrides the label.

````python
#!/usr/bin/env python3
"""pasteboard - put text on the Pasteboard page (pasteboard-live).

  pasteboard last [N] [--whole] [--title T]
        Post Claude's reply from N turns back in this session (default 1: the
        reply before the current prompt), copied verbatim from the session
        transcript. The reply is the text after the turn's last tool call;
        --whole takes every text block in the turn.
  pasteboard span [N] [--from TEXT [--to TEXT]] [--whole] [--title T]
        Post a stretch of conversation: each of your prompts as a quote
        followed by Claude's reply, turns separated by rules. N counts finished
        turns back (default 2). --from starts at the latest turn whose prompt
        or reply contains TEXT; --to ends at the first turn from there that
        contains its TEXT (default: the last finished turn). Matching ignores
        markdown marks, line breaks and case, so text copied out of tmux works.
  pasteboard mark [--title T]
        Flag the turn in progress; the Stop hook (pasteboard stop-hook) posts
        its final reply verbatim from the transcript once the turn ends.
  pasteboard post [--title T] [FILE]
        Post FILE (or stdin) as is.
  pasteboard list [--state board|saved|cleared]
  pasteboard restore ID      Put a cleared post back on the board.
  pasteboard stop-hook       Stop hook entry; reads the hook JSON on stdin.

Session comes from CLAUDE_CODE_SESSION_ID (or --session). Paths and the
label on quoted prompts are in the Settings block below; PASTEBOARD_NAME in
the environment overrides the label.
"""
import argparse, glob, json, os, re, sqlite3, sys, time

# ---- Settings ----------------------------------------------------------
DATA_DIR = os.path.expanduser('~/.local/share/pasteboard')     # database; same as in pasteboard-live
TRANSCRIPTS = os.path.expanduser('~/.claude/projects')        # Claude Code session transcripts
PROMPT_LABEL = os.environ.get('PASTEBOARD_NAME', 'Me')     # name on quoted prompts
# ------------------------------------------------------------------------

BASE = DATA_DIR
DB = os.path.join(BASE, 'pasteboard.db')
PENDING = os.path.join(BASE, 'pending')
SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '', body TEXT NOT NULL, source TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL DEFAULT 'board' CHECK (state IN ('board','saved','cleared')),
  changed TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v INTEGER NOT NULL);
INSERT OR IGNORE INTO meta VALUES ('version', 0);
"""


def db():
    os.makedirs(BASE, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.executescript(SCHEMA)
    return c


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def insert(body, title='', source=''):
    body = body.rstrip('\n')
    if not body.strip():
        sys.exit('pasteboard: nothing to post (empty text)')
    with db() as c:
        t = now()
        cur = c.execute("INSERT INTO posts (created,title,body,source,state,changed) VALUES (?,?,?,?, 'board', ?)",
                        (t, title, body, source, t))
        c.execute("UPDATE meta SET v = v + 1 WHERE k='version'")
        return cur.lastrowid


def transcript(sid, path=None):
    if path and os.path.exists(path):
        return path
    hits = glob.glob(os.path.join(TRANSCRIPTS, '*', f'{sid}.jsonl'))
    if not hits:
        sys.exit(f'pasteboard: no transcript found for session {sid}')
    return max(hits, key=os.path.getmtime)


def is_prompt(e):
    """A prompt the user typed (or a slash command), not a tool result or injected text."""
    if e.get('type') != 'user' or e.get('isMeta') or e.get('isCompactSummary') or e.get('isSidechain'):
        return False
    c = e.get('message', {}).get('content')
    if isinstance(c, str):
        return True
    if isinstance(c, list):
        return not any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c)
    return False


def turns(path):
    out = []  # each: list of ('text', str) | ('tool', None)
    for line in open(path, encoding='utf-8'):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('isSidechain'):
            continue
        if is_prompt(e):
            out.append([])
        elif e.get('type') == 'assistant' and out:
            for b in e.get('message', {}).get('content', []) or []:
                if not isinstance(b, dict):
                    continue
                if b.get('type') == 'text' and b.get('text', '').strip():
                    out[-1].append(('text', b['text']))
                elif b.get('type') == 'tool_use':
                    out[-1].append(('tool', None))
    return [t for t in out if any(k == 'text' for k, _ in t)]


def reply(blocks, whole=False):
    if not whole:
        last_tool = max((i for i, (k, _) in enumerate(blocks) if k == 'tool'), default=-1)
        tail = [v for k, v in blocks[last_tool + 1:] if k == 'text']
        if tail:
            return '\n\n'.join(tail)
    return '\n\n'.join(v for k, v in blocks if k == 'text')


def session_id(a):
    sid = a.session or os.environ.get('CLAUDE_CODE_SESSION_ID')
    if not sid:
        sys.exit('pasteboard: no session id (CLAUDE_CODE_SESSION_ID unset; pass --session)')
    return sid


def cmd_last(a):
    sid = session_id(a)
    # The latest prompt (the one asking for this post) opens the turn in progress;
    # count back from the turn before it.
    done = turns_before_current(transcript(sid))
    if a.n < 1 or a.n > len(done):
        sys.exit(f'pasteboard: only {len(done)} finished replies in this session')
    body = reply(done[-a.n], a.whole)
    if a.with_prompt:
        prompt = done[-a.n][0][1].strip()
        body = quote_prompt(prompt) + '\n\n' + body
    pid = insert(body, a.title, sid)
    print(f'posted #{pid}')


def turns_before_current(path):
    """Finished turns, excluding the one opened by the latest prompt."""
    out, cur = [], None
    for line in open(path, encoding='utf-8'):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('isSidechain'):
            continue
        if is_prompt(e):
            if cur is not None:
                out.append(cur)
            c = e.get('message', {}).get('content')
            txt = c if isinstance(c, str) else '\n'.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
            cur = [('prompt', txt)]
        elif e.get('type') == 'assistant' and cur is not None:
            for b in e.get('message', {}).get('content', []) or []:
                if isinstance(b, dict) and b.get('type') == 'text' and b.get('text', '').strip():
                    cur.append(('text', b['text']))
                elif isinstance(b, dict) and b.get('type') == 'tool_use':
                    cur.append(('tool', None))
    return [t for t in out if any(k == 'text' for k, _ in t)]


def clean_prompt(t):
    """Prompt text as typed: hook reminders dropped, slash commands shown as typed."""
    t = re.sub(r'<system-reminder>.*?</system-reminder>', '', t, flags=re.S)
    m = re.search(r'<command-name>(.*?)</command-name>', t, re.S)
    if m:
        args = re.search(r'<command-args>(.*?)</command-args>', t, re.S)
        t = m.group(1).strip() + (' ' + args.group(1).strip() if args and args.group(1).strip() else '')
    return t.strip()


def quote_prompt(t):
    return '\n'.join('> ' + l if l else '>' for l in (f'**{PROMPT_LABEL}:** ' + clean_prompt(t)).split('\n'))


def norm(s):
    """For matching text copied from the terminal: no markdown marks, one space, lower case."""
    return ' '.join(re.sub(r'[*`_#>|]', ' ', s).split()).lower()


def cmd_span(a):
    sid = session_id(a)
    done = turns_before_current(transcript(sid))
    if a.frm:
        f = norm(a.frm)
        full = [norm(t[0][1] + ' ' + ' '.join(v for k, v in t[1:] if k == 'text')) for t in done]
        hits = [i for i, s in enumerate(full) if f in s]
        if not hits:
            sys.exit('pasteboard: start text not found in any finished turn')
        start = hits[-1]  # latest match: the recent conversation is the usual target
        end = len(done) - 1
        if a.to:
            t = norm(a.to)
            ends = [i for i in range(start, len(done)) if t in full[i]]
            if not ends:
                sys.exit('pasteboard: end text not found at or after the start')
            end = ends[0]
        sel = done[start:end + 1]
    else:
        if a.n < 1 or a.n > len(done):
            sys.exit(f'pasteboard: only {len(done)} finished replies in this session')
        sel = done[-a.n:]
    parts = [quote_prompt(t[0][1]) + '\n\n' + reply(t, a.whole) for t in sel]
    pid = insert('\n\n---\n\n'.join(parts), a.title, sid)
    print(f'posted #{pid} ({len(sel)} turns)')


def cmd_mark(a):
    sid = session_id(a)
    os.makedirs(PENDING, exist_ok=True)
    with open(os.path.join(PENDING, sid), 'w') as f:
        json.dump({'title': a.title, 'whole': a.whole, 'marked': now()}, f)
    print('marked: this turn\'s reply goes to the pasteboard when it ends')


def cmd_stop_hook(a):
    try:
        h = json.load(sys.stdin)
    except ValueError:
        return
    sid = h.get('session_id', '')
    flag = os.path.join(PENDING, sid)
    if not sid or not os.path.exists(flag):
        return
    try:
        opts = json.load(open(flag))
    except ValueError:
        opts = {}
    path = transcript(sid, h.get('transcript_path'))
    # The transcript can trail the Stop event by a moment; wait for the final text.
    for _ in range(10):
        ts = turns(path)
        if ts and reply(ts[-1], opts.get('whole')):
            break
        time.sleep(0.3)
    if ts:
        insert(reply(ts[-1], opts.get('whole')), opts.get('title', ''), sid)
    os.remove(flag)


def cmd_post(a):
    body = open(a.file, encoding='utf-8').read() if a.file and a.file != '-' else sys.stdin.read()
    print(f'posted #{insert(body, a.title, a.source or "manual")}')


def cmd_list(a):
    with db() as c:
        for r in c.execute("SELECT id, created, title, substr(replace(body, char(10), ' '), 1, 70) FROM posts WHERE state=? ORDER BY id DESC", (a.state,)):
            print(f'#{r[0]}  {r[1]}  {r[2] + " | " if r[2] else ""}{r[3]}')


def cmd_restore(a):
    with db() as c:
        n = c.execute("UPDATE posts SET state='board', changed=? WHERE id=? AND state='cleared'", (now(), a.id)).rowcount
        if n:
            c.execute("UPDATE meta SET v = v + 1 WHERE k='version'")
    print('restored' if n else 'no cleared post with that id')


def main():
    ap = argparse.ArgumentParser(prog='pasteboard', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--session')
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('last'); p.add_argument('n', nargs='?', type=int, default=1)
    p.add_argument('--whole', action='store_true'); p.add_argument('--with-prompt', action='store_true')
    p.add_argument('--title', default=''); p.set_defaults(f=cmd_last)
    p = sp.add_parser('span'); p.add_argument('n', nargs='?', type=int, default=2)
    p.add_argument('--from', dest='frm', default=''); p.add_argument('--to', default='')
    p.add_argument('--whole', action='store_true'); p.add_argument('--title', default=''); p.set_defaults(f=cmd_span)
    p = sp.add_parser('mark'); p.add_argument('--whole', action='store_true'); p.add_argument('--title', default=''); p.set_defaults(f=cmd_mark)
    p = sp.add_parser('post'); p.add_argument('file', nargs='?'); p.add_argument('--title', default=''); p.add_argument('--source', default=''); p.set_defaults(f=cmd_post)
    p = sp.add_parser('list'); p.add_argument('--state', default='board', choices=['board', 'saved', 'cleared']); p.set_defaults(f=cmd_list)
    p = sp.add_parser('restore'); p.add_argument('id', type=int); p.set_defaults(f=cmd_restore)
    p = sp.add_parser('stop-hook'); p.set_defaults(f=cmd_stop_hook)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
````

## The launcher: `pasteboard-serve`

Settings block: `PYTHON` (row 6), `SCRIPTS` (row 1), `BIND` (row 3), `PORT` (row 5). It ships set to this machine only.

````sh
#!/bin/sh
# Launcher for pasteboard-live, kept running by the service manager.
# pasteboard-live decides who it answers; BIND decides where it listens.

# ---- Settings ----------------------------------------------------------
PYTHON=/usr/bin/python3      # Python 3.8+; a full path, since service managers start with a bare PATH
SCRIPTS="$HOME/bin"          # folder holding pasteboard-live
BIND=127.0.0.1               # 127.0.0.1 = this machine only; 0.0.0.0 = also tailnet and LAN
PORT=8795
# ------------------------------------------------------------------------

exec "$PYTHON" -I "$SCRIPTS/pasteboard-live" --bind "$BIND" --port "$PORT"
````

## Keeping it running

Use the one row 7 chose. Both run `pasteboard-serve` from the scripts folder, and both need full paths, since neither expands `~`. With "started by hand", skip this section and run `pasteboard-serve` in a terminal when the page is wanted.

On macOS, save this as `~/Library/LaunchAgents/[LABEL].plist`, where `[LABEL]` is a reverse-domain name such as `com.example.pasteboard`. Replace `[SCRIPTS]` with the row 1 folder and `[DATA_DIR]` with the row 2 folder, both as full paths.

````xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>[LABEL]</string>
  <key>ProgramArguments</key>
  <array>
    <string>[SCRIPTS]/pasteboard-serve</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>[DATA_DIR]/server.log</string>
  <key>StandardErrorPath</key><string>[DATA_DIR]/server.log</string>
</dict>
</plist>
````

Create the database folder first, then load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/[LABEL].plist`. Restart after an edit with `launchctl kickstart -k gui/$(id -u)/[LABEL]`.

On Linux, save this as `~/.config/systemd/user/pasteboard.service`, with `[SCRIPTS]` replaced by the row 1 folder as a full path, then run `systemctl --user daemon-reload` and `systemctl --user enable --now pasteboard`. Restart with `systemctl --user restart pasteboard`. To keep it running while the user is logged out, `loginctl enable-linger` is also needed.

````ini
[Unit]
Description=Pasteboard for Claude Code replies

[Service]
ExecStart=[SCRIPTS]/pasteboard-serve
Restart=always

[Install]
WantedBy=default.target
````

## The Stop hook

Only if row 11 is yes. Add this entry to the `hooks.Stop` array in `~/.claude/settings.json`, with `[SCRIPTS]` replaced by the row 1 folder as a full path and `python3` by the row 6 Python if it isn't the one on `PATH`. If the file already has Stop hooks, add it beside them. It does nothing unless Claude flagged the turn with `pasteboard mark`, and its errors are swallowed so it can never block a reply.

````json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 -I [SCRIPTS]/pasteboard stop-hook 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
````

## The skill: `~/.claude/skills/[COMMAND]/SKILL.md`

Replace `[COMMAND]` with the row 10 name, in the folder name and the `name:` line, and in the trigger phrases if the user wants them to match. Replace `[PAGE ADDRESS]` with the address the user opens the page at, such as `http://localhost:8795/` or the machine's tailnet address with the row 5 port. If the scripts folder isn't on `PATH`, write `pasteboard` as its full path throughout. If row 11 is no, delete the "On your own initiative" section.

````markdown
---
name: [COMMAND]
description: Use when the user says "pasteboard", "pasteboard that", "put that on the pasteboard", "/[COMMAND]" (optionally with a number, a range or text), or asks to keep a reply somewhere they can find it later. Posts Claude's reply, verbatim from the session transcript, to the Pasteboard page at [PAGE ADDRESS]. Also use on Claude's own initiative for a reply the user will want to refer back to.
---

# Pasteboard

A private web page for replies the user wants to read again without scrolling the terminal. Page: [PAGE ADDRESS]. Board and Saved tabs; each post has a timestamp, a link to itself, and Raw, Copy, Save or Move back, and Clear. Cleared posts come back for a while with `pasteboard restore <id>`. Run `pasteboard -h` for every option.

Text always comes from the transcript, so what reaches the page is exactly what the user saw. Never retype a reply into `pasteboard post`.

## When the user asks

| They say | Run |
| --- | --- |
| `/[COMMAND]`, "pasteboard that" | `pasteboard last` (the reply before their prompt) |
| `/[COMMAND] 3`, "the one three back" | `pasteboard last 3` |
| `/[COMMAND] whole`, "with the narration" | `pasteboard last --whole` (every text block in that turn, including the lines before tool calls) |
| "with my question", "include what I said" | `pasteboard last --with-prompt` (their prompt as a quote above the reply) |
| "the last 4 exchanges" | `pasteboard span 4` (each prompt quoted above its reply, turns divided by rules) |
| a pasted chunk of the conversation, or "from <phrase> to <phrase>" | `pasteboard span --from "<opening words>" --to "<closing words>"` (whole turns; matching ignores markdown marks, line breaks and case) |
| `/[COMMAND] <text>` where the text is their own words for the board | write the text to a temporary file, then `pasteboard post --title "note" <file>` |

Add `--title "<few words>"` naming the subject. Then answer in one line: the post number and its link, `[PAGE ADDRESS]#p<number>`.

If they name an older reply by topic rather than count, check the transcript for which count it is before running `pasteboard last N`; never guess.

## On your own initiative

When a reply holds something the user will likely come back to (a list of steps, a table, a command set, a long explanation), run `pasteboard mark --title "<few words>"` during that turn, before the final reply. The Stop hook posts the turn's final reply verbatim once the turn ends. Say so in the reply, in a few words ("on the pasteboard"). Don't mark short answers or chit-chat.

## Notes

- `pasteboard list [--state board|saved|cleared]` shows what is there.
- Never widen who can reach the page without the user's say-so: replies can quote private files.
````

## Tests

Run these in order and report each result to the user.

Use the row 5 port wherever `[PORT]` appears, and skip a test whose part the user left out in Phase 1.

1. `curl -s http://127.0.0.1:[PORT]/api/version` prints a JSON version number.
2. `echo "hello from the recipe" | pasteboard post --title test` prints `posted #1`, and the page shows the post within a second, with the green "live" marker lit.
3. Save it from the page, check that it moves to the Saved tab folded to its header line, then use Move back, then Clear. `pasteboard list --state cleared` should list it, and `pasteboard restore 1` should put it back.
4. `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:[PORT]/api/posts/1/save` prints 403, because the header is missing.
5. Reach matches row 3. With this machine only, another device gets no answer at all. With LAN devices, a LAN device missing from the allow file gets 403 and a listed one gets the page.
6. In a Claude Code session, ask a question, then type `/[COMMAND]`. The answer appears on the page word for word, rendered as markdown.
7. Ask Claude for a list of steps and tell it to put that reply on the pasteboard itself. Once the turn ends, the reply appears without a second command, and the `pending/` folder inside the database folder is empty.
8. Open `[PAGE ADDRESS]#p1`. The page jumps to post 1, expands it and outlines it for a moment.

## Notes for the builder

- Built and run on macOS with the system Python 3.9.6 and a launchd agent. A second run changed every setting from its default (scripts and database in other folders, another transcripts folder, port, title, label, no tailnet, no allow list, localhost only) and behaved as set. The Linux service file above hasn't been run.
- The page uses a regular-expression lookbehind, which needs Safari 16.4 or newer; other current browsers have it.
- Posting reads Claude Code's transcript format: one JSON object per line, user entries flagged `isMeta` for injected text, and `tool_use` and `tool_result` blocks. If a future Claude Code release changes that layout, `pasteboard last` is the place to adjust.
- The default post is the text after the turn's last tool call, which matches what the terminal shows as the final answer. `--whole` brings back the short narration lines Claude writes between tool calls.
- Nothing is sent anywhere. The page uses no outside scripts, fonts or libraries, so it works with the internet down.
