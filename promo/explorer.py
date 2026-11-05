"""Builds explorer.html: a self-contained, plain-language view of the results for any show.

For each promo it shows the cut on an episode timeline, the script lines inside the cut (hook zone and
cliffhanger marked), the lines right after the cut that the viewer is left wanting, and the scores.
"""
from __future__ import annotations

import html
import json

EPS = 0.05


def promo_lines(show, p):
    segs, out, offset = p["segments"], [], 0.0
    for k, s in enumerate(segs):
        ep, a, b = s["episode"], s["start_s"], s["end_s"]
        for bt in show.beats[ep]:
            if a - EPS <= bt["start"] < b:
                out.append({"t": round(offset + bt["start"] - a, 1), "seg": k, "ep": ep,
                            "kind": bt["kind"], "who": (bt.get("speaker") or "").title(),
                            "tone": bt.get("tone", ""), "text": bt["text"]})
        offset += b - a
    last = segs[-1]
    withheld = [{"kind": bt["kind"], "who": (bt.get("speaker") or "").title(), "text": bt["text"]}
                for bt in show.beats[last["episode"]] if bt["start"] >= last["end_s"] - EPS][:3]
    return out, withheld


def build(show, res, input_name: str) -> str:
    durations = {e["number"]: e["duration"] for e in show.eps}
    loglines = {e["number"]: e["logline"] for e in show.eps}
    items = []
    for p in res["promos"] + res.get("variants", []):
        lines, withheld = promo_lines(show, p)
        wave = "1" if p["funnel"].startswith("acq") else ("2" if p["funnel"].startswith("mid") else "3")
        items.append({**{k: p[k] for k in ("id", "rank", "duration_s", "hook", "cliffhanger", "why", "flags",
                                           "funnel", "components", "kind", "alternate_cuts")},
                      "segments": [{**s, "ep_len": durations[s["episode"]]} for s in p["segments"]],
                      "wave": "V" if p["id"].startswith("V") else wave, "lines": lines, "withheld": withheld,
                      "logline": loglines[p["segments"][0]["episode"]]})
    data = {"show": input_name, "stats": res["stats"], "promos": items}
    return TEMPLATE.replace("__TITLE__", html.escape(input_name)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Promo Explorer</title>
<style>
:root{--bg:#f7f5f0;--panel:#fffdf9;--fg:#1f1d1a;--mut:#6d6a63;--line:#e3ded4;--acc:#a23b2a;--acc2:#2d5f8a;
--hook:#fde7c7;--cliff:#f6d3cc;--held:#eceae5;--ok:#2f6b3a;--chip:#efe9df}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161513;--panel:#1e1c19;--fg:#ece9e3;--mut:#a29e96;
--line:#34312c;--acc:#e48a76;--acc2:#8cb8de;--hook:#4a3a20;--cliff:#4d2a24;--held:#2a2825;--ok:#8fcf98;--chip:#2b2823}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:20px 16px 8px;max-width:1240px;margin:auto}h1{margin:0;font-size:22px}
.sub{color:var(--mut);font-size:14px}.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 4px}
.step{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:13px}
.step b{display:block;font-size:14px;margin-bottom:2px}.step i{color:var(--acc);font-style:normal;font-weight:700;margin-right:6px}
main{max-width:1240px;margin:auto;padding:8px 16px 40px;display:grid;grid-template-columns:330px 1fr;gap:16px}main>section{min-width:0}
.script{overflow-wrap:anywhere}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.tabs button{border:1px solid var(--line);background:var(--panel);
color:var(--fg);border-radius:999px;padding:4px 11px;font-size:13px;cursor:pointer}.tabs button.on{background:var(--fg);color:var(--bg)}
.list{display:flex;flex-direction:column;gap:6px;max-height:78vh;overflow:auto;padding-right:4px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:9px 11px;cursor:pointer}
.card.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}.card .top{display:flex;justify-content:space-between;font-size:12px;color:var(--mut)}
.card .h{font-size:13.5px;margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.badge{display:inline-block;font-size:11px;border-radius:4px;padding:0 6px;background:var(--chip)}
.w1{color:var(--ok)}.w2{color:var(--acc2)}.w3{color:var(--acc)}
.detail{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;min-width:0}
.detail h2{margin:0 0 4px;font-size:19px}.kv{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;font-size:14px;margin:10px 0}
.kv div:nth-child(odd){color:var(--mut)}h3{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:18px 0 6px}
.tl{margin:6px 0}.tl .lab{font-size:12px;color:var(--mut);margin-bottom:2px}.bar{position:relative;height:16px;background:var(--held);border-radius:4px}
.bar span{position:absolute;top:0;bottom:0;background:var(--acc);border-radius:4px}
.script{border:1px solid var(--line);border-radius:8px;overflow:hidden}
.ln{display:grid;grid-template-columns:52px 1fr;gap:8px;padding:5px 10px;border-top:1px solid var(--line);font-size:14px}
.ln:first-child{border-top:0}.ln .t{color:var(--mut);font-variant-numeric:tabular-nums;font-size:12.5px;padding-top:2px}
.ln.hook{background:var(--hook)}.ln.cliff{background:var(--cliff)}.ln.held{background:var(--held);color:var(--mut)}
.ln .who{font-weight:600}.ln .tone{color:var(--mut);font-size:12px}.ln .act{font-style:italic}
.tag{font-size:11px;font-weight:700;letter-spacing:.04em;margin-left:6px}.join{padding:4px 10px;font-size:12px;color:var(--acc2);background:var(--chip)}
.scores{display:grid;grid-template-columns:120px 1fr 44px;gap:6px 10px;align-items:center;font-size:13px;max-width:520px}
.sb{height:9px;background:var(--held);border-radius:5px;overflow:hidden}.sb span{display:block;height:100%;background:var(--acc2)}
.flag{display:inline-block;background:var(--chip);color:var(--acc);border-radius:4px;padding:1px 7px;margin:2px 4px 2px 0;font-size:12.5px}
.why{font-size:15px;background:var(--chip);border-radius:8px;padding:10px 12px}
.legend{font-size:12px;color:var(--mut);margin:4px 0 8px}.legend span{padding:1px 6px;border-radius:3px;margin-right:6px}
@media (max-width:860px){main{grid-template-columns:1fr}.list{max-height:none;flex-direction:row;overflow-x:auto}
.card{min-width:240px}.steps{grid-template-columns:1fr 1fr}.kv{grid-template-columns:90px 1fr}}
</style></head><body>
<header><h1>Promo Explorer</h1><div class="sub" id="sub"></div>
<div class="steps">
<div class="step"><b><i>1</i>Read the scripts</b>Every line, action and sound cue with its exact timestamp.</div>
<div class="step"><b><i>2</i>Score every moment</b>How strong an opener is it (hook)? How badly would you need to know what happens next (cliffhanger)?</div>
<div class="step"><b><i>3</i>Try ~1,400 cuts</b>All 20–60 s, all cut between lines, never mid-sentence. Code guarantees this.</div>
<div class="step"><b><i>4</i>Rank &amp; plan</b>Best first, no near-duplicates, then a posting plan: early free episodes first.</div>
</div></header>
<main><section><div class="tabs" id="tabs"></div><div class="list" id="list"></div></section>
<section class="detail" id="detail"></section></main>
<script>
const D=__DATA__;
const fmt=t=>{t=Math.max(0,t);return Math.floor(t/60)+":"+(t%60).toFixed(1).padStart(4,"0")};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const WAVES=[["all","All"],["1","Wave 1 · post first"],["2","Wave 2"],["3","Wave 3 · retarget"],["V","Cross-episode"]];
const WNAME={1:"Wave 1 · post first",2:"Wave 2 · mid-story",3:"Wave 3 · retargeting",V:"Cross-episode variant"};
document.getElementById("sub").textContent=`${D.show} · ${D.stats.episodes} episodes · ${D.stats.candidates} cuts scored · ${D.promos.filter(p=>p.wave!="V").length} promos picked in ${D.stats.seconds??"?"}s · mode: ${D.stats.provider}`;
let wave="all",cur=D.promos[0].id;
function tabs(){document.getElementById("tabs").innerHTML=WAVES.map(([k,v])=>`<button class="${k==wave?"on":""}" data-w="${k}">${v}</button>`).join("");
document.querySelectorAll("#tabs button").forEach(b=>b.onclick=()=>{wave=b.dataset.w;tabs();list()})}
function list(){const ps=D.promos.filter(p=>wave=="all"?p.wave!="V":p.wave==wave);
document.getElementById("list").innerHTML=ps.map(p=>`<div class="card ${p.id==cur?"on":""}" data-id="${p.id}"><div class="top"><span>${p.id.startsWith("V")?p.id:"#"+p.rank} · ${p.segments.map(s=>"Ep "+s.episode).join(" + ")} · ${p.duration_s.toFixed(0)}s</span><span class="badge w${p.wave}">${p.wave=="V"?"variant":"wave "+p.wave}</span></div><div class="h">${esc(p.hook)}</div></div>`).join("")||"<div class='sub'>None</div>";
document.querySelectorAll(".card").forEach(c=>c.onclick=()=>{cur=c.dataset.id;list();show()})}
function show(){const p=D.promos.find(x=>x.id==cur);const L=p.lines;const end=p.duration_s;
const lastIdx=L.length-1-[...L].reverse().findIndex(l=>l.kind!="SOUND FX");
let rows="",prevSeg=0;L.forEach((l,i)=>{if(l.seg!=prevSeg){rows+=`<div class="join">✂ jump cut → Episode ${p.segments[l.seg].episode} ${p.segments[l.seg].start}</div>`;prevSeg=l.seg}
const cls=l.t<3?"hook":(i==lastIdx?"cliff":"");const tag=l.t<3&&i==L.findIndex(x=>x.t<3)?'<span class="tag w3">HOOK ZONE</span>':(i==lastIdx?'<span class="tag w3">CLIFFHANGER</span>':"");
rows+=`<div class="ln ${cls}"><div class="t">${fmt(l.t)}</div><div>${l.kind=="DIALOGUE"?`<span class="who">${esc(l.who)}</span> <span class="tone">(${esc(l.tone)})</span>: “${esc(l.text)}”`:`<span class="act">[${l.kind=="SOUND FX"?"sound":"action"}] ${esc(l.text)}</span>`}${tag}</div></div>`});
const held=p.withheld.map(l=>`<div class="ln held"><div class="t">after</div><div>${l.kind=="DIALOGUE"?`<span class="who">${esc(l.who)}</span>: “${esc(l.text)}”`:`<span class="act">[${l.kind=="SOUND FX"?"sound":"action"}] ${esc(l.text)}</span>`}</div></div>`).join("");
const tl=p.segments.map(s=>`<div class="tl"><div class="lab">Episode ${s.episode} · cut ${s.start} → ${s.end} of ${fmt(s.ep_len)}</div><div class="bar"><span style="left:${s.start_s/s.ep_len*100}%;width:${Math.max((s.end_s-s.start_s)/s.ep_len*100,1)}%"></span></div></div>`).join("");
const C=p.components,sc=[["Hook strength",C.hook],["Cliffhanger",C.cliff],["Drama inside",C.body],["Makes sense alone",C.standalone]];
const alts=(p.alternate_cuts||[]).map(a=>`<li>${a.segments.map(s=>`Ep ${s.episode} ${s.start}–${s.end}`).join(" + ")} (${a.duration_s.toFixed(0)}s), ends on ${esc(a.cliffhanger)}</li>`).join("");
document.getElementById("detail").innerHTML=`<h2>${p.id.startsWith("V")?p.id:"#"+p.rank} · ${p.duration_s.toFixed(1)}-second promo</h2>
<span class="badge w${p.wave}">${WNAME[p.wave]}</span> <span class="badge">${p.kind=="single"?"one continuous clip":p.kind=="pruned"?"two clips, weak middle removed":"clips from two episodes"}</span>
<div class="kv"><div>Hook</div><div>${esc(p.hook)}</div><div>Cliffhanger</div><div>${esc(p.cliffhanger)}</div><div>Episode summary</div><div class="sub">${esc(p.logline)}</div></div>
<div class="why">💡 ${esc(p.why)}</div>${p.flags.length?`<div style="margin-top:8px">${p.flags.map(f=>`<span class="flag">⚠ ${esc(f)}</span>`).join("")}</div>`:""}
<h3>Where the cut sits in the episode</h3>${tl}
<h3>What the viewer sees (timestamps from the start of the promo)</h3>
<div class="legend"><span style="background:var(--hook)">first 3 seconds: must stop the scroll</span><span style="background:var(--cliff)">last beat: leaves a question</span><span style="background:var(--held)">cut off: what they'd install to see</span></div>
<div class="script">${rows}${held}</div>
<h3>Scores (0 = weak, 1 = strong)</h3><div class="scores">${sc.map(([n,v])=>`<div>${n}</div><div class="sb"><span style="width:${Math.min(v,1)*100}%"></span></div><div>${v.toFixed(2)}</div>`).join("")}</div>
${alts?`<h3>Alternate cuts of the same hook (for A/B tests)</h3><ul>${alts}</ul>`:""}`}
tabs();list();show();
</script></body></html>"""
