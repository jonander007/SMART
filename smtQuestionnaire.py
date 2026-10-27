#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json, html as _html, itertools, ast
from pathlib import Path
from .constants import tmp_dir
from .utilities import encode_tuples

__AUTHOR__        = 'Cristian Garrido Tamm'
__VERSION__       = '1.0.0'

# ── Saaty scale ───────────────────────────────────────────────────────────────
_SAATY = {
    9:'Extreme importance', 8:'Very-very strong importance',
    7:'Very strong importance', 6:'Strong-to-very strong importance',
    5:'Strong importance', 4:'Moderate-to-strong importance',
    3:'Moderate importance', 2:'Weak importance', 1:'Equal importance',
}
# Slider scale: LEFT favours criterion A, RIGHT favours criterion B.
# idx 0 → '9'  (A extremely more important)
# idx 8 → '1'  (equal)
# idx 16→ '1/9'(B extremely more important)
_SAATY_LABELS = (
    [str(i) for i in range(9,1,-1)] + ['1'] +
    ['1/'+str(i) for i in range(2,10)]
)

# Saaty importance phrases — mirrors constants.py::saaty_scale in the SMART app
_SAATY_PHRASES = {
    '1': 'equally as important as',
    '2': 'equally to moderately more important than',
    '3': 'moderately more important than',
    '4': 'moderately to strongly more important than',
    '5': 'strongly more important than',
    '6': 'strongly to very strongly more important than',
    '7': 'very strongly more important than',
    '8': 'very strongly to extremely more important than',
    '9': 'extremely more important than',
}

def _saaty_phrase(idx, a, b):
    """Build the comparison sentence for slider index idx, like the SMART app."""
    lbl = _SAATY_LABELS[idx]
    if lbl == '1':
        return f'Criterion {a} is {_SAATY_PHRASES["1"]} Criterion {b}'
    if '/' in lbl:
        k = lbl.split('/')[1]
        return f'Criterion {b} is {_SAATY_PHRASES[k]} Criterion {a}'
    return f'Criterion {a} is {_SAATY_PHRASES[lbl]} Criterion {b}'

def _saaty_phrase_html(idx, a, b):
    """Like _saaty_phrase but with the two names coloured (A red, B blue)."""
    a_h = f'<span class="q-name q-a">{_e(a)}</span>'
    b_h = f'<span class="q-name q-b">{_e(b)}</span>'
    lbl = _SAATY_LABELS[idx]
    if lbl == '1':
        return f'Criterion {a_h} is {_SAATY_PHRASES["1"]} Criterion {b_h}'
    if '/' in lbl:
        k = lbl.split('/')[1]
        return f'Criterion {b_h} is {_SAATY_PHRASES[k]} Criterion {a_h}'
    return f'Criterion {a_h} is {_SAATY_PHRASES[lbl]} Criterion {b_h}'


# ── Colour palette ────────────────────────────────────────────────────────────
_C = {
    'primary':   '#2C3E50',
    'accent':    '#C47A20',
    'goal_f':    '#F5E6B8',
    'goal_s':    '#C9A830',
    'crit_f':    '#F2C98A',
    'crit_s':    '#C47A20',
    'scale_f':   '#D5F5E3',
    'scale_s':   '#1E8449',
    'rs_f':      '#E8F4FD',
    'rs_s':      '#2E86C1',
    'white':     '#FFFFFF',
    'light':     '#F8F9FA',
    'border':    '#DEE2E6',
    'text':      '#2C3E50',
    'muted':     '#6C757D',
    'danger':    '#E74C3C',
    'success':   '#27AE60',
    'start_btn': '#1a6b3a',
}

# ─────────────────────────────────────────────────────────────────────────────
def _safe(s):
    import unicodedata
    s = str(s)
    # Normalize accented chars to ASCII equivalents (é→e, ñ→n, etc.)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.replace(' ','_').replace('&','').replace('/','_').replace("'","").replace('"','').replace('(','').replace(')','').replace(',','')

def _e(s):
    return _html.escape(str(s))

def _pair_id(a, b):
    return f'p_{_safe(a)}__{_safe(b)}'

def _to_pair(k):
    """Accept a key that is already a tuple OR a string repr of one."""
    if isinstance(k, tuple):
        return k
    return ast.literal_eval(k)

def _saved_pairs_lookup(pairs_dict):
    """Build a lookup {frozenset({a,b}): value} from a saved comparisons dict,
    so we can find a saved value regardless of the (a,b) vs (b,a) order."""
    lookup = {}
    if not pairs_dict:
        return lookup
    for k, v in pairs_dict.items():
        try:
            a, b = _to_pair(k)
            lookup[frozenset((a, b))] = (a, b, v)
        except Exception:
            continue
    return lookup

def _pairs_from_children(children):
    """Generate ordered (a,b) pairs for all combinations of a children list."""
    from itertools import combinations
    return list(combinations(children, 2))

def _node_name(item):
    """Return the name of a tree node (str leaf or {name: {...}} dict)."""
    return item if isinstance(item, str) else list(item.keys())[0]

def _node_children(item):
    """Return the children list of a tree node, or [] for a leaf."""
    if isinstance(item, dict):
        name = list(item.keys())[0]
        return item[name].get('children', [])
    return []

def _collect_comparison_nodes(children):
    """Walk a criteria subtree and yield every node that has 2+ children, as
    (parent_name, [child_names]) tuples. This captures comparisons at ANY depth
    (criteria, subcriteria, sub-subcriteria, ...), not just the first two levels.
    """
    nodes = []
    for item in children:
        kids = _node_children(item)
        kid_names = [_node_name(k) for k in kids]
        if len(kid_names) >= 2:
            nodes.append((_node_name(item), kid_names))
        # Recurse into children to catch deeper comparison groups
        if kids:
            nodes.extend(_collect_comparison_nodes(kids))
    return nodes

def _build_existing_for_pairs(pairs, saved_lookup):
    """Return an {'(a, b)': value} dict for the given pairs, pulling values from
    saved_lookup where the same unordered pair exists (any order). Pairs with no
    saved value are omitted so the slider falls back to its neutral default."""
    existing = {}
    for a, b in pairs:
        hit = saved_lookup.get(frozenset((a, b)))
        if hit is None:
            continue
        sa, sb, val = hit
        # If saved order is reversed relative to (a,b), invert the Saaty value
        if (sa, sb) == (a, b):
            existing[str((a, b))] = val
        else:
            try:
                existing[str((a, b))] = 1.0 / val if val else val
            except Exception:
                existing[str((a, b))] = val
    return existing

# ── Hierarchy SVG (reused from criteriaHierarchy logic, standalone) ───────────
def _build_hierarchy_svg(tree_data, rating_scales, uses_rating_scales=True):
    """Minimal standalone hierarchy SVG (2-level, no scale items).

    When uses_rating_scales is False (pure pairwise case), the blue
    "With Rating Scale" legend entry is omitted and no node is highlighted.
    """
    import html as _h
    def wrap(text, mc=14):
        words=text.split(); lines,cur=[],''
        for w in words:
            if cur and len(cur)+1+len(w)>mc: lines.append(cur); cur=w
            else: cur=(cur+' '+w).strip() if cur else w
        if cur: lines.append(cur)
        return lines or ['']
    def tspan(x,y,lines,fs,fw,fill,lh=14):
        th=len(lines)*lh; y0=y-th/2+lh/2; out=''
        for i,ln in enumerate(lines):
            out+=(f'<text x="{x:.0f}" y="{y0+i*lh:.0f}" text-anchor="middle" '
                  f'dominant-baseline="middle" font-size="{fs}" font-weight="{fw}" '
                  f'font-family="Arial,sans-serif" fill="{fill}">{_h.escape(ln)}</text>')
        return out
    PW,PH,CW,CH,GSIB=110,46,86,36,10
    MARGIN=24; CW_=1030
    goal=tree_data['goal']; criteria=tree_data['criteria']
    # pack rows
    avail=CW_-2*MARGIN; rows,cur_row,cur_w=[],[],0
    for c in criteria:
        n=len(c['children']); chw=n*CW+max(0,n-1)*GSIB if n else 0
        cw=max(PW,chw); gap=GSIB if cur_row else 0
        if cur_row and cur_w+gap+cw>avail: rows.append(cur_row); cur_row,cur_w=[c],cw
        else: cur_row.append(c); cur_w+=gap+cw
    if cur_row: rows.append(cur_row)
    # y metrics
    GL=wrap(goal,44); GH=max(44,len(GL)*15+14); GW=min(CW_-2*MARGIN,400)
    SPINE_X=MARGIN-4; BKT=20; RSX=SPINE_X+BKT
    GAP_GB=20; GAP_BP=20; GAP_PCH=14; GAP_CHCH=8; GAP_ROW=36
    def row_h(row):
        mph=max(max(PH,len(wrap(c['name'],14))*14+10) for c in row)
        mch=max((max(CH,len(wrap(ch['name'],12))*13+10) for c in row for ch in c['children']),default=0)
        h=GAP_BP+mph
        if any(c['children'] for c in row): h+=GAP_PCH+GAP_CHCH+mch
        return h,mph,mch
    y_buses=[]; y_cur=GH+18+GAP_GB
    rms=[]
    for row in rows:
        h,mph,mch=row_h(row); rms.append((h,mph,mch)); y_buses.append(y_cur); y_cur+=h+GAP_ROW
    total_h=int(y_cur+28)
    S,T,L=[],[],[]
    def ln(x1,y1,x2,y2,sw='1.5',col='#999'):
        L.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{col}" stroke-width="{sw}"/>')
    def rc(x,y,w,h,f,s,rx=5,sw='1.5'):
        S.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"/>')
    # goal
    gx=CW_/2-GW/2; gmy=18+GH/2
    rc(gx,18,GW,GH,'#F5E6B8','#C9A830',rx=7,sw='2')
    T.append(tspan(CW_/2,gmy,GL,12,'bold','#5a2a00',lh=15))
    ln(gx,gmy,SPINE_X,gmy,sw='2')
    ln(SPINE_X,gmy,SPINE_X,y_buses[-1],sw='2')
    for ri,(row,yb,(rmh,mph,mch)) in enumerate(zip(rows,y_buses,rms)):
        col_ws=[max(PW,len(c['children'])*CW+max(0,len(c['children'])-1)*GSIB) for c in row]
        pcents=[]; xc=RSX
        for cw in col_ws: pcents.append(xc+cw/2); xc+=cw+GSIB
        ln(SPINE_X,yb,pcents[0],yb,sw='2')
        S.append(f'<circle cx="{SPINE_X:.0f}" cy="{yb:.0f}" r="3.5" fill="#999"/>')
        if len(pcents)>1: ln(pcents[0],yb,pcents[-1],yb)
        if ri>0:
            TW,TH=40,14; tx=SPINE_X-TW-4; ty=yb-TH/2
            S.append(f'<rect x="{tx:.0f}" y="{ty:.0f}" width="{TW}" height="{TH}" rx="3" fill="#F2C98A" stroke="#C47A20" stroke-width="1"/>')
            T.append(f'<text x="{tx+TW/2:.0f}" y="{yb:.0f}" text-anchor="middle" dominant-baseline="middle" font-size="9" font-weight="bold" font-family="Arial,sans-serif" fill="#4a1f00">criteria</text>')
        ypt=yb+GAP_BP; ypb=ypt+mph
        ycb=ypb+GAP_PCH; yct=ycb+GAP_CHCH
        for c,cx in zip(row,pcents):
            px=cx-PW/2; pl=wrap(c['name'],14)
            ln(cx,yb,cx,ypt)
            rc(px,ypt,PW,mph,'#F2C98A','#C47A20',rx=5)
            T.append(tspan(cx,ypt+mph/2,pl,11,'bold','#4a1f00',lh=14))
            if not c['children']: continue
            ln(cx,ypb,cx,ycb,sw='1')
            chs=c['children']; n=len(chs)
            bw=n*CW+(n-1)*GSIB; sx=cx-bw/2
            cxs=[sx+j*(CW+GSIB)+CW/2 for j in range(n)]
            if n>1: ln(cxs[0],ycb,cxs[-1],ycb,sw='1')
            for ch,ccx in zip(chs,cxs):
                hs=ch.get('has_scale',False)
                ff='#E8F4FD' if hs else '#FFF'; fs='#2E86C1' if hs else '#BBB'; ft='#0a3a5a' if hs else '#1a1a1a'
                ln(ccx,ycb,ccx,yct,sw='1')
                rc(ccx-CW/2,yct,CW,mch,ff,fs,rx=4,sw='1')
                T.append(tspan(ccx,yct+mch/2,wrap(ch['name'],12),10,'normal',ft,lh=13))
    # legend
    ly=total_h-18; lx=MARGIN
    def leg(label,f,s):
        nonlocal lx
        S.append(f'<rect x="{lx}" y="{ly-10}" width="16" height="12" rx="3" fill="{f}" stroke="{s}" stroke-width="1"/>')
        T.append(f'<text x="{lx+20}" y="{ly}" font-size="10" font-family="Arial,sans-serif" fill="#444">{_h.escape(label)}</text>')
        lx+=len(label)*6+36
    leg('Criteria','#F2C98A','#C47A20'); leg('Subcriteria','#FFF','#BBB')
    if uses_rating_scales:
        leg('With Rating Scale','#E8F4FD','#2E86C1')
    body='\n'.join(L)+'\n'+'\n'.join(S)+'\n'+''.join(T)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW_}" height="{total_h}" '
            f'viewBox="0 0 {CW_} {total_h}" style="background:#fff;max-width:100%;">'
            f'<rect width="{CW_}" height="{total_h}" fill="#fff"/>{body}</svg>'), CW_, total_h


# ── Pairwise slider block ─────────────────────────────────────────────────────
def _pairwise_block(block_id, parent_label, pairs, existing=None, disabled=False):
    """Returns HTML string for one pairwise comparison block with sliders."""
    existing = existing or {}
    # Term used in the question header: top-level criteria vs subcriteria vs scale.
    if block_id.startswith('cc_'):
        term = 'criterion'
    elif block_id.startswith('sc_'):
        term = 'subcriterion'
    else:
        term = 'option'
    rows = ''
    for a, b in pairs:
        pid   = _pair_id(a, b)
        fid   = f'{block_id}__{pid}'
        val   = existing.get(str((a,b)), existing.get(f"('{a}', '{b}')", 1))
        # val is a float/int; convert to slider index (0..16)
        # labels: 1/9..1/2, 1, 2..9  → index 0..16
        def _val_to_idx(v):
            v = float(v)
            # Inverted scale: value 9 → idx 0 (left), 1 → idx 8, 1/9 → idx 16 (right)
            if v >= 1:
                return max(0, 8 - (round(v) - 1))    # 9→0, 1→8
            else:
                return min(16, 8 + round(1/v) - 1)   # 1/2→9, 1/9→16
        idx = _val_to_idx(val)
        opts_html = ''
        for i, lbl in enumerate(_SAATY_LABELS):
            sel = 'selected' if i == idx else ''
            opts_html += f'<option value="{i}" {sel}>{lbl}</option>'
        dis_attr = 'disabled' if disabled else ''
        # Coloured criterion names: A in red, B in blue (matching slider sides).
        a_html = f'<span class="q-name q-a">{_e(a)}</span>'
        b_html = f'<span class="q-name q-b">{_e(b)}</span>'
        # For subcriteria, prefix the question with the parent criterion context.
        if block_id.startswith('sc_'):
            prefix = f'In criterion <span class="q-parent">{_e(parent_label)}</span>, how important is '
        else:
            prefix = 'How important is '
        question = (f'{prefix}{term} {a_html} compared to {term} {b_html}?')
        rows += f'''
        <div class="pair-card" data-block="{block_id}" data-a="{_e(a)}" data-b="{_e(b)}" data-id="{fid}">
          <div class="pair-question">{question}</div>
          <div class="pair-slider-row">
            <span class="side-label prefer-a">◀ {_e(a)}</span>
            <input type="range" class="pairwise-range" id="{fid}"
                   min="0" max="16" value="{idx}"
                   data-a="{_e(a)}" data-b="{_e(b)}" data-block="{block_id}"
                   data-parent="{_e(parent_label)}" {dis_attr}>
            <span class="side-label prefer-b">{_e(b)} ▶</span>
            <button class="comment-btn" title="Add comment"
                    onclick="toggleComment('cmt_{fid}')" id="cbtn_{fid}">💬</button>
          </div>
          <div class="scale-value-row">
            <span class="scale-value" id="scale_{fid}">{_SAATY_LABELS[idx]}</span>
          </div>
          <div class="slider-label" id="lbl_{fid}">{_saaty_phrase_html(idx, a, b)}</div>
          <div class="comment-box" id="cmt_{fid}" style="display:none;">
            <textarea class="comment-input" id="txt_{fid}"
                      data-pair-id="{fid}" data-a="{_e(a)}" data-b="{_e(b)}"
                      data-block="{block_id}" data-block-label="{_e(parent_label)}"
                      placeholder="Add your comment…" rows="2"></textarea>
          </div>
        </div>'''
    return f'''
    <div class="comparison-block" id="block_{block_id}">
      <div class="block-header">{_e(parent_label)}</div>
      <div class="pair-cards">{rows}</div>
      <div class="cr-bar" id="cr_{block_id}">
        <span class="cr-label">Consistency Ratio (CR):</span>
        <span class="cr-value" id="crv_{block_id}">—</span>
        <span class="cr-badge" id="crb_{block_id}"></span>
        <span class="cr-hint" id="crh_{block_id}"></span>
      </div>
    </div>'''


# ── Main generator ────────────────────────────────────────────────────────────
def generate_questionnaire_html(smt_data: dict, output_path: str = None,
                                rs_mode: str = 'editable') -> str:
    """Generate the questionnaire HTML.

    rs_mode:
      'hidden'   – Rating Scales Comparison tab is omitted entirely.
      'readonly' – Tab shown with current values, sliders disabled.
      'editable' – Tab fully editable (default).
    """

    gen  = smt_data.get('General', {})
    alts_raw = smt_data['Alternatives']['Alternatives']
    alts = [a for a in alts_raw if a != 'Use Rating Scale']
    tree_dict = smt_data['Criteria']['Criteria']
    cc   = smt_data['Criteria Comparison']['Criteria Comparison']
    ar   = smt_data['Alternative Rating']
    rs_creation  = ar.get('Rating Scales Creation', {})
    rs_comparison= ar.get('Rating Scales Comparison', {})
    rt_data      = ar.get('Rating Table', {})

    # Show rating-scale styling (blue nodes + legend) only when the section is
    # actually present in the questionnaire. This is False when:
    #   - the user chose "Omit section" in the export dialog (rs_mode='hidden'), OR
    #   - no rating scales are defined at all (pure pairwise case).
    uses_rating_scales = (rs_mode != 'hidden') and bool(rs_creation)

    goal = list(tree_dict.keys())[0]
    criteria_raw = tree_dict[goal].get('children', [])

    # Build criteria tree for hierarchy SVG
    rating_scale_names = set(rs_creation.keys())
    criteria_list = []
    for item in criteria_raw:
        if isinstance(item, str):
            criteria_list.append({'name': item, 'children': []})
        elif isinstance(item, dict):
            cname = list(item.keys())[0]
            ch = []
            for sub in item[cname].get('children', []):
                sname = sub if isinstance(sub, str) else list(sub.keys())[0]
                ch.append({'name': sname,
                           'has_scale': uses_rating_scales and sname in rating_scale_names,
                           'scale_items': [v for v in rs_creation.get(sname,[]) if isinstance(v,str)]})
            criteria_list.append({'name': cname, 'children': ch})

    hier_svg, _, _ = _build_hierarchy_svg({'goal': goal, 'criteria': criteria_list}, rs_creation, uses_rating_scales)

    # ── Tab 1: Introduction ───────────────────────────────────────────────────
    desc   = _e(gen.get('Description','AHP decision support study'))
    analyst= _e(gen.get('Analyst',''))
    date   = _e(gen.get('Date',''))
    alt_pills = ''.join(f'<span class="alt-pill">{_e(a)}</span>' for a in alts)

    tab1_html = f'''
    <div class="intro-card">
      <h2>Welcome to the IDOM-SMART Expert Survey</h2>
      <p class="intro-desc">{desc}</p>
      <div class="meta-row">
        <span><b>Analyst:</b> {analyst}</span>
        <span><b>Date:</b> {date}</span>
      </div>
      <hr>
      <h3>What is this survey?</h3>
      <p>This questionnaire applies the <b>Analytic Hierarchy Process (AHP)</b> developed by Thomas Saaty.
      You will be asked to compare criteria, subcriteria and rating scale values in pairs using a
      1–9 importance scale. Your responses will be used to derive priority weights for a
      multi-criteria decision analysis.</p>
      <h3>Alternatives under evaluation</h3>
      <div class="alt-pills">{alt_pills}</div>
      <h3>How to answer</h3>
      <ol>
        <li>Review the <b>Alternatives</b> and <b>Hierarchy</b> tabs to familiarise yourself with the study.</li>
        <li>Click <b>Start Survey</b> to begin.</li>
        <li>For each pair, move the slider towards the element you consider more important.</li>
        <li>When finished, click <b>Download Results</b> to save your responses.</li>
      </ol>
      <div class="start-row">
        <button class="start-btn" onclick="goTab('tab-cc')">▶ &nbsp;Start Survey</button>
      </div>
    </div>'''

    # ── Tab 2: Alternatives + Rating Scales (read-only) ───────────────────────
    # Build table: rows = subcriteria with scale, cols = alternatives
    subcriteria_with_scale = [s for s in rs_creation.keys()]

    header_alts = ''.join(f'<th>{_e(a)}</th>' for a in alts)
    rt_rows = ''
    for i, sub in enumerate(subcriteria_with_scale):
        bg = '#f9f9f9' if i % 2 == 0 else '#fff'
        options = [v for v in rs_creation[sub] if isinstance(v, str)]
        opts_html = ''.join(f'<span class="scale-opt">{_e(o)}</span>' for o in options)
        tds = f'<td class="sub-label">{_e(sub)}<div class="scale-opts">{opts_html}</div></td>'
        for alt in alts:
            val = rt_data.get(alt, {}).get(sub, '—')
            tds += f'<td class="rt-val" style="background:{bg}">{_e(val)}</td>'
        rt_rows += f'<tr style="background:{bg}">{tds}</tr>'

    tab2_html = f'''
    <h2 class="tab-title">Alternatives &amp; Rating Scales</h2>
    <p class="tab-desc">The table below shows the current rating scale assignments for each alternative.
    These values are for reference only and cannot be modified here.</p>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th style="min-width:180px;text-align:left">Subcriteria / Scale options</th>
          {header_alts}
        </tr></thead>
        <tbody>{rt_rows}</tbody>
      </table>
    </div>'''

    # ── Tab 3: Hierarchy ──────────────────────────────────────────────────────
    _blue_note = (' Subcriteria highlighted in blue use a Rating Scale.'
                  if uses_rating_scales else '')
    tab3_html = f'''
    <h2 class="tab-title">Criteria Hierarchy</h2>
    <p class="tab-desc">The diagram below shows the full hierarchy of criteria and subcriteria
    used in this study.{_blue_note}</p>
    <div class="hier-wrap">{hier_svg}</div>
    <div class="start-row" style="margin-top:24px;">
      <button class="start-btn" onclick="goTab('tab-cc')">▶ &nbsp;Start Survey</button>
    </div>'''

    # ── Tab 4: Criteria Comparison ────────────────────────────────────────────
    # Generate comparison blocks from the CURRENT criteria tree, not from the
    # saved Criteria Comparison dict (which can be stale if the tree was renamed
    # after the comparisons were made). Saved values are used only to pre-fill
    # sliders where the same pair still exists.
    cc_blocks = ''
    # Top-level: compare the top criteria against each other (parent = goal)
    top_criteria_names = [list(c.keys())[0] if isinstance(c, dict) else c
                          for c in criteria_raw]
    if len(top_criteria_names) > 1:
        goal_pairs = _pairs_from_children(top_criteria_names)
        goal_saved = _saved_pairs_lookup(cc.get(goal, {}))
        goal_existing = _build_existing_for_pairs(goal_pairs, goal_saved)
        cc_blocks += _pairwise_block(
            block_id=f'cc_{_safe(goal)}',
            parent_label=goal,
            pairs=goal_pairs,
            existing=goal_existing
        )
    tab4_html = f'''
    <h2 class="tab-title">Criteria Comparison</h2>
    <p class="tab-desc">Compare the importance of each pair of criteria.
    Move the slider towards the element you consider more important and how strongly.</p>
    {cc_blocks}'''

    # ── Tab 5: Subcriteria Comparison (within each criterion) ─────────────────
    # Build one block per parent node with 2+ children at ANY depth below the
    # top level (subcriteria, sub-subcriteria, ...). The top-level comparison
    # lives in Tab 4; everything deeper belongs here.
    sc_blocks = ''
    # Every comparison group at any depth below the goal. Because criteria_raw
    # is the goal's children (not the goal itself), this naturally yields each
    # criterion's subcriteria group plus any deeper groups — but NOT the
    # top-level criteria group (that one is rendered in Tab 4 above).
    sub_comparison_nodes = _collect_comparison_nodes(criteria_raw)

    if sub_comparison_nodes:
        for parent_name, child_names in sub_comparison_nodes:
            sub_pairs = _pairs_from_children(child_names)
            sub_saved = _saved_pairs_lookup(cc.get(parent_name, {}))
            sub_existing = _build_existing_for_pairs(sub_pairs, sub_saved)
            sc_blocks += _pairwise_block(
                block_id=f'sc_{_safe(parent_name)}',
                parent_label=parent_name,
                pairs=sub_pairs,
                existing=sub_existing
            )
    if not sub_comparison_nodes:
        sc_blocks = '<p class="tab-desc muted">No subcriteria comparisons defined.</p>'
    tab5_html = f'''
    <h2 class="tab-title">Subcriteria Comparison</h2>
    <p class="tab-desc">Compare subcriteria within each criterion group.</p>
    {sc_blocks}'''

    # ── Tab 6: Rating Scales Comparison ───────────────────────────────────────
    rs_blocks = ''
    if rs_mode != 'hidden':
        for sub, pairs_dict_raw in rs_comparison.items():
            pairs_dict = pairs_dict_raw if isinstance(pairs_dict_raw, dict) else {}
            pairs = [_to_pair(k) for k in pairs_dict.keys()]
            rs_blocks += _pairwise_block(
                block_id=f'rs_{_safe(sub)}',
                parent_label=sub,
                pairs=pairs,
                existing=pairs_dict,
                disabled=(rs_mode == 'readonly')
            )
        if not rs_blocks:
            rs_blocks = '<p class="tab-desc muted">No rating scale comparisons defined.</p>'

    if rs_mode == 'hidden':
        rs_tab_btn   = ''
        rs_tab_panel = ''
    elif rs_mode == 'readonly':
        tab6_html = f'''
    <h2 class="tab-title">Rating Scales Comparison</h2>
    <div class="readonly-banner">
      🔒 This section is provided for reference only — the values reflect the
      analyst's judgements and <strong>cannot be modified</strong>.
    </div>
    {rs_blocks}'''
        rs_tab_btn   = '<button class="tab-btn" onclick="goTab(\'tab-rs\')" id="btn-tab-rs">🎚️ Rating Scales Comparison 🔒</button>'
        rs_tab_panel = f'<div class="tab-panel" id="tab-rs">{tab6_html}</div>'
    else:
        tab6_html = f'''
    <h2 class="tab-title">Rating Scales Comparison</h2>
    <p class="tab-desc">Compare the relative value of each option within a rating scale.</p>
    {rs_blocks}'''
        rs_tab_btn   = '<button class="tab-btn" onclick="goTab(\'tab-rs\')" id="btn-tab-rs">🎚️ Rating Scales Comparison</button>'
        rs_tab_panel = f'<div class="tab-panel" id="tab-rs">{tab6_html}</div>'

    # ── Assemble full HTML ────────────────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IDOM-SMART Expert Survey</title>
<style>
/* ── Reset & base ── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#2C3E50;background:#F0F2F5;}}
a{{color:#2E86C1;}}

/* ── Shell ── */
.shell{{max-width:1100px;margin:0 auto;padding:0 0 40px;}}

/* ── Header ── */
.app-header{{background:#2C3E50;color:#fff;padding:16px 28px;display:flex;align-items:center;gap:16px;}}
.app-header h1{{font-size:18px;font-weight:700;letter-spacing:.02em;}}
.app-header .badge{{background:#C47A20;color:#fff;font-size:11px;font-weight:600;
  padding:3px 10px;border-radius:12px;letter-spacing:.05em;}}

/* ── Tab bar ── */
.tab-bar{{position:sticky;top:0;z-index:1000;display:flex;background:#1a252f;overflow-x:auto;border-bottom:3px solid #C47A20;}}
.tab-btn{{flex:none;padding:11px 14px;font-size:12px;font-weight:500;color:#aab7c4;
  background:transparent;border:none;cursor:pointer;white-space:nowrap;transition:all .15s;
  border-bottom:3px solid transparent;margin-bottom:-3px;}}
.tab-btn:hover{{color:#fff;background:rgba(255,255,255,.06);}}
.tab-btn.active{{color:#fff;border-bottom:3px solid #C47A20;background:rgba(196,122,32,.12);}}

/* ── Tab panels ── */
.tab-panel{{display:none;padding:28px;background:#fff;border-radius:0 0 6px 6px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);}}
.tab-panel.active{{display:block;}}

/* ── Intro card ── */
.intro-card h2{{font-size:20px;color:#2C3E50;margin-bottom:12px;}}
.intro-card h3{{font-size:15px;margin:20px 0 8px;color:#C47A20;}}
.intro-card p,.intro-desc{{line-height:1.7;color:#444;margin-bottom:8px;}}
.intro-card ol{{padding-left:20px;line-height:2;color:#444;}}
.meta-row{{display:flex;gap:24px;font-size:13px;color:#666;margin:10px 0;}}
.alt-pills{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0;}}
.alt-pill{{background:#E8F4FD;color:#1A5276;border:1px solid #2E86C1;
  border-radius:20px;padding:4px 14px;font-size:13px;font-weight:500;}}
.start-row{{margin-top:28px;text-align:center;}}
.start-btn{{background:#1a6b3a;color:#fff;border:none;padding:12px 36px;
  font-size:14px;font-weight:600;border-radius:6px;cursor:pointer;letter-spacing:.03em;
  box-shadow:0 2px 6px rgba(0,0,0,.15);transition:background .15s;}}
.start-btn:hover{{background:#145530;}}

/* ── Tab titles ── */
.tab-title{{font-size:17px;font-weight:700;color:#2C3E50;margin-bottom:8px;}}
.tab-desc{{color:#555;line-height:1.6;margin-bottom:20px;max-width:800px;}}
.tab-desc.muted{{color:#999;font-style:italic;}}

/* ── Alternatives table ── */
.table-wrap{{overflow-x:auto;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.1);}}
.data-table{{border-collapse:collapse;width:100%;min-width:500px;}}
.data-table thead th{{background:#2C3E50;color:#fff;font-size:12px;font-weight:600;
  padding:10px 14px;border:1px solid #1a252f;white-space:nowrap;}}
.data-table thead th:first-child{{background:#1a252f;text-align:left;}}
.sub-label{{padding:6px 14px;font-weight:500;border:1px solid #ddd;
  font-size:12px;vertical-align:top;min-width:180px;}}
.scale-opts{{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;}}
.scale-opt{{background:#F2C98A;color:#4a1f00;font-size:10px;border-radius:10px;
  padding:2px 8px;border:1px solid #C47A20;white-space:nowrap;}}
.rt-val{{padding:8px 14px;border:1px solid #ddd;font-size:12px;
  text-align:center;vertical-align:middle;}}

/* ── Hierarchy ── */
.hier-wrap{{overflow-x:auto;border:1px solid #ddd;border-radius:6px;padding:12px;background:#fafafa;}}

/* ── Comparison blocks ── */
.comparison-block{{margin-bottom:28px;border:1px solid #DEE2E6;border-radius:8px;overflow:hidden;background:#f7f9fb;}}
.block-header{{background:#F2C98A;color:#4a1f00;font-weight:700;font-size:13px;
  padding:10px 16px;border-bottom:1px solid #C47A20;letter-spacing:.02em;}}
/* ── Comparison cards (one vertical card per pairwise comparison) ── */
.pair-cards{{display:flex;flex-direction:column;gap:18px;padding:18px;}}
.pair-card{{background:#fff;border:1px solid #e8ecf1;border-radius:12px;
  padding:22px 24px;transition:box-shadow .15s,border-color .15s;}}
.pair-card:hover{{border-color:#d8dee6;box-shadow:0 3px 12px rgba(44,62,80,.07);}}

/* Question — sits at the top of the card */
.pair-question{{font-size:15px;font-weight:600;color:#2C3E50;
  line-height:1.5;margin-bottom:20px;}}

/* Slider row: A label | slider | B label | comment button.
   The two side labels carry the criterion names (A red, B blue) and may wrap
   onto two lines so long names are never truncated. The slider stays centred. */
.pair-slider-row{{display:flex;align-items:center;gap:14px;}}
.pairwise-range{{flex:1;height:6px;cursor:pointer;accent-color:#C47A20;min-width:120px;}}
.side-label{{font-size:12px;font-weight:600;line-height:1.3;
  flex:0 0 22%;max-width:22%;word-break:break-word;}}
.prefer-a{{color:#C0392B;text-align:right;}}
.prefer-b{{color:#2980B9;text-align:left;}}

/* Current Saaty value of the slider, shown as a single badge under it. */
.scale-value-row{{display:flex;justify-content:center;margin-top:10px;}}
.scale-value{{font-size:16px;font-weight:800;color:#C47A20;
  font-variant-numeric:tabular-nums;
  background:#FEF4E4;border:1px solid #E8C99A;border-radius:8px;
  padding:2px 14px;min-width:48px;text-align:center;}}

/* Result phrase — large, centred under the slider, reads as the answer */
.slider-label{{text-align:center;font-size:15px;color:#444;margin-top:18px;
  font-style:italic;min-height:22px;line-height:1.5;
  padding-top:16px;border-top:1px solid #f0f2f5;}}

/* Coloured criterion names inside the question and the result phrase.
   A = red, B = blue — matching the slider-side labels. */
.q-name{{font-weight:700;}}
.q-a{{color:#C0392B;}}
.q-b{{color:#2980B9;}}
/* Parent-criterion context shown for subcriteria questions. */
.q-parent{{color:#C47A20;font-weight:700;font-style:normal;}}

/* ── CR bar ── */
.cr-bar{{display:flex;align-items:center;gap:10px;padding:9px 16px;
  background:#f8f9fa;border-top:1px solid #dee2e6;flex-wrap:wrap;}}
.cr-label{{font-size:12px;color:#666;font-weight:600;}}
.cr-value{{font-size:13px;font-weight:700;color:#2C3E50;min-width:52px;}}
.cr-badge{{font-size:11px;font-weight:700;padding:3px 10px;border-radius:10px;}}
.cr-badge.ok{{background:#D5F5E3;color:#1E8449;border:1px solid #1E8449;}}
.cr-badge.bad{{background:#FDECEA;color:#C0392B;border:1px solid #E74C3C;}}
.cr-hint{{font-size:11px;color:#999;font-style:italic;}}

/* ── Floating CR indicator (always visible while comparing) ── */
.floating-cr{{position:fixed;top:80px;right:24px;z-index:900;
  display:flex;align-items:center;gap:12px;
  background:#fff;border:1px solid #dee2e6;border-radius:12px;
  box-shadow:0 6px 20px rgba(44,62,80,.15);
  padding:10px 16px;min-width:200px;
  transition:transform .2s,opacity .2s;}}
.fcr-block{{font-size:11px;font-weight:600;color:#888;max-width:120px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  border-right:1px solid #eee;padding-right:12px;}}
.fcr-main{{display:flex;flex-direction:column;align-items:center;line-height:1.1;}}
.fcr-label{{font-size:10px;font-weight:700;color:#999;letter-spacing:.05em;}}
.fcr-value{{font-size:18px;font-weight:800;color:#2C3E50;}}
.fcr-badge{{font-size:16px;font-weight:800;width:26px;height:26px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;}}
.fcr-badge.ok{{background:#D5F5E3;color:#1E8449;}}
.fcr-badge.bad{{background:#FDECEA;color:#C0392B;}}
.floating-cr.ok{{border-color:#27AE60;}}
.floating-cr.bad{{border-color:#E74C3C;}}
@media (max-width:700px){{
  .floating-cr{{top:auto;bottom:16px;right:16px;left:16px;min-width:0;}}
}}

/* ── Readonly banner ── */
.readonly-banner{{background:#FEF9E7;border:1px solid #F39C12;border-radius:6px;
  padding:10px 16px;margin-bottom:20px;font-size:13px;color:#7D6608;line-height:1.6;}}
input[type=range]:disabled{{opacity:.4;cursor:not-allowed;pointer-events:none;}}

/* ── Comment ── */
.comment-btn{{background:none;border:1px solid transparent;border-radius:6px;
  font-size:16px;cursor:pointer;padding:4px 7px;line-height:1;color:#bbb;
  transition:all .15s;flex-shrink:0;}}
.comment-btn:hover{{background:#FEF9E7;border-color:#F39C12;color:#C47A20;}}
.comment-btn.has-comment{{color:#C47A20;border-color:#C47A20;background:#FEF9E7;}}
.comment-box{{margin-top:14px;}}
.comment-input{{width:100%;font-size:13px;border:1px solid #C47A20;border-radius:6px;
  padding:8px 10px;resize:vertical;font-family:Arial,sans-serif;
  background:#FFFDF5;color:#2C3E50;outline:none;}}
.comment-input:focus{{border-color:#a5641a;box-shadow:0 0 0 2px rgba(196,122,32,.15);}}

/* ── Download bar ── */
.dl-bar{{position:sticky;bottom:0;z-index:100;background:#2C3E50;padding:12px 28px;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 -2px 8px rgba(0,0,0,.2);}}
.dl-bar span{{color:#aab7c4;font-size:13px;}}
.dl-btn{{background:#C47A20;color:#fff;border:none;padding:9px 28px;
  font-size:13px;font-weight:600;border-radius:5px;cursor:pointer;}}
.dl-btn:hover{{background:#a5641a;}}
.progress-pill{{background:#27AE60;color:#fff;font-size:11px;border-radius:10px;
  padding:3px 12px;margin-left:12px;display:inline-block;}}
</style>
</head>
<body>
<!-- Floating CR indicator — always visible while comparing -->
<div id="floating-cr" class="floating-cr" style="display:none;">
  <div class="fcr-block" id="fcr-block">—</div>
  <div class="fcr-main">
    <span class="fcr-label">CR</span>
    <span class="fcr-value" id="fcr-value">—</span>
  </div>
  <div class="fcr-badge" id="fcr-badge"></div>
</div>
<div class="shell">

<!-- Header -->
<div class="app-header">
  <div>
    <h1>IDOM-SMART · Expert Survey</h1>
    <div style="font-size:12px;color:#aab7c4;margin-top:3px;">{_e(goal)}</div>
  </div>
  <span class="badge">AHP</span>
</div>

<!-- Tab bar -->
<div class="tab-bar">
  <button class="tab-btn active" onclick="goTab('tab-intro')" id="btn-tab-intro">📋 Introduction</button>
  <button class="tab-btn" onclick="goTab('tab-alts')"  id="btn-tab-alts">🔵 Alternatives</button>
  <button class="tab-btn" onclick="goTab('tab-hier')"  id="btn-tab-hier">🌳 Hierarchy</button>
  <button class="tab-btn" onclick="goTab('tab-cc')"    id="btn-tab-cc">⚖️ Criteria Comparison</button>
  <button class="tab-btn" onclick="goTab('tab-sc')"    id="btn-tab-sc">📊 Subcriteria Comparison</button>
  {rs_tab_btn}
</div>

<!-- Panels -->
<div class="tab-panel active" id="tab-intro">{tab1_html}</div>
<div class="tab-panel" id="tab-alts">{tab2_html}</div>
<div class="tab-panel" id="tab-hier">{tab3_html}</div>
<div class="tab-panel" id="tab-cc">{tab4_html}</div>
<div class="tab-panel" id="tab-sc">{tab5_html}</div>
{rs_tab_panel}

<!-- Download bar -->
<div class="dl-bar">
  <div>
    <span>Responses ready to export</span>
    <span class="progress-pill" id="progress-pill">0 / 0 answered</span>
  </div>
  <div style="display:flex;gap:10px;">
    <button class="dl-btn" style="background:#6C757D;" onclick="downloadComments()">💬 Download Comments (.txt)</button>
    <button class="dl-btn" onclick="downloadResults()">⬇ Download Results (.smt)</button>
  </div>
</div>

</div><!-- /shell -->

<script>
// ── Tab navigation ─────────────────────────────────────────────────────────────
const TABS = ['tab-intro','tab-alts','tab-hier','tab-cc','tab-sc','tab-rs'];
function goTab(id) {{
  TABS.forEach(t => {{
    var el  = document.getElementById(t);
    var btn = document.getElementById('btn-'+t);
    if (el)  el.classList.toggle('active', t===id);
    if (btn) btn.classList.toggle('active', t===id);
  }});
  window.scrollTo(0,0);
  // Refresh the floating CR for the newly shown tab (hides it on non-comparison tabs)
  if (typeof refreshFloatingForVisibleBlock === 'function') {{
    setTimeout(refreshFloatingForVisibleBlock, 50);
  }}
}}

// ── Saaty scale ────────────────────────────────────────────────────────────────
const SAATY_LABELS = {json.dumps(_SAATY_LABELS)};
// Saaty importance phrases (mirrors constants.py::saaty_scale in the SMART app)
const SAATY_PHRASES = {{
  '1': 'equally as important as',
  '2': 'equally to moderately more important than',
  '3': 'moderately more important than',
  '4': 'moderately to strongly more important than',
  '5': 'strongly more important than',
  '6': 'strongly to very strongly more important than',
  '7': 'very strongly more important than',
  '8': 'very strongly to extremely more important than',
  '9': 'extremely more important than'
}};

// Build the comparison sentence for a slider, exactly as the SMART app does:
//   idx 0..7  → left side (A) less important → B is the more-important one
//   idx 8     → equal
//   idx 9..16 → right side (B) more important → A is the more-important one
// SAATY_LABELS[idx] is '1/9'..'1/2','1','2'..'9'.
function saatyPhrase(idx, a, b) {{
  var aH = '<span class="q-name q-a">' + a + '</span>';
  var bH = '<span class="q-name q-b">' + b + '</span>';
  var lbl = SAATY_LABELS[idx];
  if (lbl === '1') {{
    return 'Criterion ' + aH + ' is ' + SAATY_PHRASES['1'] + ' Criterion ' + bH;
  }}
  if (lbl.indexOf('/') !== -1) {{
    // 1/k → B is k times more important than A
    var k = lbl.split('/')[1];
    return 'Criterion ' + bH + ' is ' + SAATY_PHRASES[k] + ' Criterion ' + aH;
  }}
  // plain integer k → A is k times more important than B
  return 'Criterion ' + aH + ' is ' + SAATY_PHRASES[lbl] + ' Criterion ' + bH;
}}
const SAATY_VALUES = [9,8,7,6,5,4,3,2,1,1/2,1/3,1/4,1/5,1/6,1/7,1/8,1/9];

// ── Base .smt (everything except the comparison sections filled by user) ────────
const SMT_BASE = __SMT_BASE_PLACEHOLDER__;

// ── Donegan & Dodd Random Index table (mirrors ahp.py exactly) ─────────────────
const RI_DD = {{
  3:0.4914, 4:0.8286, 5:1.0591, 6:1.1797, 7:1.2519,
  8:1.3171, 9:1.3733, 10:1.4055, 11:1.4213, 12:1.4497,
  13:1.4643, 14:1.4822, 15:1.4969, 16:1.5078, 17:1.5153,
  18:1.5262, 19:1.5313, 20:1.5371, 25:1.5619, 30:1.5772,
  40:1.5976, 50:1.6102, 60:1.6178, 70:1.6237, 80:1.6277,
  90:1.6213, 100:1.6339
}};

function getRIdd(n) {{
  if (RI_DD[n] !== undefined) return RI_DD[n];
  // linear interpolation between nearest keys
  var keys = Object.keys(RI_DD).map(Number).sort((a,b)=>a-b);
  var lo = keys.filter(k=>k<n).pop();
  var hi = keys.filter(k=>k>n)[0];
  if (lo===undefined||hi===undefined) return null;
  return RI_DD[lo] + (RI_DD[hi]-RI_DD[lo])*(n-lo)/(hi-lo);
}}

// ── Matrix math helpers ────────────────────────────────────────────────────────
function matMul(A, B, n) {{
  var C = Array.from({{length:n}},()=>new Array(n).fill(0));
  for(var i=0;i<n;i++) for(var j=0;j<n;j++) for(var k=0;k<n;k++)
    C[i][j] += A[i][k]*B[k][j];
  return C;
}}

function priorityVector(M, n, iters) {{
  // Repeated squaring until convergence (mirrors _compute_priority_vector)
  var A = M.map(r=>r.slice());
  var prev = new Array(n).fill(0);
  for(var it=0;it<iters;it++) {{
    A = matMul(A,A,n);
    var rowSums = A.map(r=>r.reduce((s,v)=>s+v,0));
    var total   = rowSums.reduce((s,v)=>s+v,0);
    var pv      = rowSums.map(v=>v/total);
    // check convergence (4 decimal places)
    var converged = pv.every((v,i)=>Math.abs(v-prev[i])<0.00005);
    if(converged) return pv;
    prev = pv;
  }}
  return prev;
}}

function lambdaMax(M, w, n) {{
  // λ_max = mean of (M·w)_i / w_i
  var lams = [];
  for(var i=0;i<n;i++) {{
    var dot = 0;
    for(var j=0;j<n;j++) dot += M[i][j]*w[j];
    if(w[i]>1e-10) lams.push(dot/w[i]);
  }}
  return lams.reduce((s,v)=>s+v,0)/lams.length;
}}

// ── CR calculation for one block ───────────────────────────────────────────────
function calcCR(blockId) {{
  // IMPORTANT: scope to input.pairwise-range only. A bare [data-block] selector
  // also matches the <tr> rows and comment <textarea>s (which share data-block),
  // whose .value is undefined → NaN → corrupts the matrix → CR always 0.
  var sliders = document.querySelectorAll('input.pairwise-range[data-block="'+blockId+'"]');
  if(!sliders.length) return;

  // Collect elements and build pair→value map
  var elements = [];
  var pairVals = {{}};
  sliders.forEach(function(s) {{
    var a=s.dataset.a, b=s.dataset.b;
    var v = SAATY_VALUES[parseInt(s.value)];
    if(!elements.includes(a)) elements.push(a);
    if(!elements.includes(b)) elements.push(b);
    pairVals[a+'|||'+b] = v;
    pairVals[b+'|||'+a] = 1/v;
  }});

  var n = elements.length;

  // n<3 → always consistent
  if(n < 3) {{
    setCRDisplay(blockId, null, n);
    return;
  }}

  // Build n×n matrix
  var M = Array.from({{length:n}},(_,i)=>
    Array.from({{length:n}},(_,j)=> i===j ? 1 :
      (pairVals[elements[i]+'|||'+elements[j]] || 1)));

  var w  = priorityVector(M, n, 20);
  var lm = lambdaMax(M, w, n);
  var ci = (lm - n) / (n - 1);
  var ri = getRIdd(n);
  if(!ri) {{ setCRDisplay(blockId, null, n); return; }}
  var cr = Math.abs(ci / ri);

  setCRDisplay(blockId, cr, n);
}}

// Cache of the latest CR result per block, used by the floating indicator.
var CR_CACHE = {{}};

function setCRDisplay(blockId, cr, n) {{
  CR_CACHE[blockId] = {{cr: cr, n: n}};

  var valEl   = document.getElementById('crv_'+blockId);
  var badgeEl = document.getElementById('crb_'+blockId);
  var hintEl  = document.getElementById('crh_'+blockId);
  if(valEl) {{
    if(cr === null || n < 3) {{
      valEl.textContent   = 'N/A';
      badgeEl.textContent = '';
      badgeEl.className   = 'cr-badge';
      hintEl.textContent  = n < 3 ? '(matrices of size <3 are always consistent)' : '';
    }} else {{
      valEl.textContent = cr.toFixed(4);
      badgeEl.className = 'cr-badge';
      if(cr <= 0.10) {{
        badgeEl.classList.add('ok');
        badgeEl.textContent = '✓ Consistent  (CR ≤ 0.10)';
        hintEl.textContent  = '';
      }} else {{
        badgeEl.classList.add('bad');
        badgeEl.textContent = '✗ Inconsistent  (CR > 0.10)';
        hintEl.textContent  = 'Please revise — Saaty requires CR ≤ 0.10.';
      }}
    }}
  }}

  // If this is the block currently shown in the floating indicator, refresh it.
  if(blockId === CURRENT_FLOATING_BLOCK) {{
    updateFloatingCR(blockId);
  }}
}}

// ── Floating CR indicator ────────────────────────────────────────────────────
var CURRENT_FLOATING_BLOCK = null;

function blockLabelFromId(blockId) {{
  // Find the block's header text for display in the floating indicator.
  var el = document.getElementById('block_'+blockId);
  if(el) {{
    var hdr = el.querySelector('.block-header');
    if(hdr) return hdr.textContent;
  }}
  return blockId;
}}

function updateFloatingCR(blockId) {{
  var fcr   = document.getElementById('floating-cr');
  var fval  = document.getElementById('fcr-value');
  var fblk  = document.getElementById('fcr-block');
  var fbadge= document.getElementById('fcr-badge');
  if(!fcr || !CR_CACHE[blockId]) return;

  CURRENT_FLOATING_BLOCK = blockId;
  var data = CR_CACHE[blockId];
  fblk.textContent = blockLabelFromId(blockId);
  fcr.classList.remove('ok','bad');
  fbadge.classList.remove('ok','bad');

  if(data.cr === null || data.n < 3) {{
    fval.textContent = 'N/A';
    fbadge.textContent = '';
  }} else {{
    fval.textContent = data.cr.toFixed(3);
    if(data.cr <= 0.10) {{
      fcr.classList.add('ok'); fbadge.classList.add('ok'); fbadge.textContent='✓';
    }} else {{
      fcr.classList.add('bad'); fbadge.classList.add('bad'); fbadge.textContent='✗';
    }}
  }}
}}

// Show the floating indicator for whichever comparison block is most in view.
function refreshFloatingForVisibleBlock() {{
  var activePanel = document.querySelector('.tab-panel.active');
  var fcr = document.getElementById('floating-cr');
  if(!activePanel || !fcr) return;

  // Only show on comparison tabs (those that contain comparison blocks)
  var blocks = activePanel.querySelectorAll('.comparison-block');
  if(!blocks.length) {{ fcr.style.display = 'none'; return; }}

  // Pick the block whose vertical centre is closest to the viewport centre.
  var viewMid = window.innerHeight / 2;
  var best = null, bestDist = Infinity;
  blocks.forEach(function(b) {{
    var r = b.getBoundingClientRect();
    if(r.bottom < 0 || r.top > window.innerHeight) return; // off-screen
    var mid = (r.top + r.bottom) / 2;
    var d = Math.abs(mid - viewMid);
    if(d < bestDist) {{ bestDist = d; best = b; }}
  }});

  if(!best) {{ fcr.style.display = 'none'; return; }}
  var blockId = best.id.replace(/^block_/, '');
  fcr.style.display = 'flex';
  updateFloatingCR(blockId);
}}

window.addEventListener('scroll', refreshFloatingForVisibleBlock, {{passive:true}});
window.addEventListener('resize', refreshFloatingForVisibleBlock, {{passive:true}});

// ── Wire sliders → live CR update ─────────────────────────────────────────────
// Use both 'input' and 'change' for compatibility with pywebview/CEF
document.querySelectorAll('.pairwise-range').forEach(function(s) {{
  ['input', 'change'].forEach(function(evtType) {{
    s.addEventListener(evtType, function() {{
      var idx = parseInt(this.value);
      var lbl = document.getElementById('lbl_'+this.id);
      if(lbl) lbl.innerHTML = saatyPhrase(idx, this.dataset.a, this.dataset.b);
      // Show the current Saaty value of the slider.
      var sv = document.getElementById('scale_'+this.id);
      if(sv) sv.textContent = SAATY_LABELS[idx];
      calcCR(this.dataset.block);
      updateProgress();
    }});
  }});
}});

// ── Initial CR computation for all blocks ──────────────────────────────────────
(function() {{
  var blocks = new Set();
  document.querySelectorAll('.pairwise-range').forEach(function(s){{
    blocks.add(s.dataset.block);
  }});
  blocks.forEach(calcCR);
  // Initialise the floating indicator for the current view.
  if (typeof refreshFloatingForVisibleBlock === 'function') {{
    refreshFloatingForVisibleBlock();
  }}
}})();

// ── Progress counter ───────────────────────────────────────────────────────────
function updateProgress() {{
  var all     = document.querySelectorAll('.pairwise-range').length;
  var changed = 0;
  document.querySelectorAll('.pairwise-range').forEach(function(s){{
    if(parseInt(s.value) !== 8) changed++;
  }});
  document.getElementById('progress-pill').textContent = changed+' / '+all+' answered';
}}
updateProgress();

// ── Safe ID helper (mirrors Python _safe()) ──────────────────────────────────
function safeId(s) {{
  // Normalise accented characters (é→e, ñ→n, etc.) then strip special chars
  var norm = s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
  return norm.replace(/ /g,'_').replace(/&/g,'').replace(/[/]/g,'_')
             .replace(/'/g,'').replace(/"/g,'')
             .replace(/[(]/g,'').replace(/[)]/g,'').replace(/,/g,'');
}}

// ── Comment toggle ────────────────────────────────────────────────────────────
function toggleComment(boxId) {{
  var box = document.getElementById(boxId);
  var btn = document.getElementById(boxId.replace('cmt_','cbtn_'));
  if (!box) return;
  var visible = box.style.display !== 'none';
  box.style.display = visible ? 'none' : 'block';
  if (!visible) {{ var ta = box.querySelector('textarea'); if (ta) ta.focus(); }}
}}
document.addEventListener('input', function(e) {{
  if (!e.target.classList.contains('comment-input')) return;
  var btn = document.getElementById('cbtn_' + e.target.dataset.pairId);
  if (btn) btn.classList.toggle('has-comment', e.target.value.trim().length > 0);
}});

// ── Download comments as .txt ─────────────────────────────────────────────────
function downloadComments() {{
  var byBlock = {{}};
  document.querySelectorAll('.comment-input').forEach(function(ta) {{
    var val = ta.value.trim();
    if (!val) return;
    var block = ta.dataset.blockLabel || ta.dataset.block;
    if (!byBlock[block]) byBlock[block] = [];
    byBlock[block].push({{a: ta.dataset.a, b: ta.dataset.b, comment: val}});
  }});
  if (Object.keys(byBlock).length === 0) {{ alert('No comments to export.'); return; }}
  var now = new Date();
  var lines = ['IDOM-SMART Expert Survey — Comments', 'Date: ' + now.toISOString().slice(0,10),
               '='.repeat(60), ''];
  Object.keys(byBlock).forEach(function(block) {{
    lines.push('SECTION: ' + block);
    lines.push('-'.repeat(60));
    byBlock[block].forEach(function(e) {{
      lines.push('  Comparison : ' + e.a + '  vs.  ' + e.b);
      e.comment.split('\\n').forEach(function(ln, i) {{
        lines.push((i===0 ? '  Comment    : ' : '              ') + ln);
      }});
      lines.push('');
    }});
    lines.push('');
  }});
  var blob = new Blob([lines.join('\\n')], {{type:'text/plain;charset=utf-8'}});
  var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'survey_comments.txt'; a.click(); URL.revokeObjectURL(a.href);
}}

// ── Download as .smt ──────────────────────────────────────────────────────────
function downloadResults() {{
  // Deep-clone the base .smt
  var out = JSON.parse(JSON.stringify(SMT_BASE));

  // Collect slider values grouped by block
  var blockData = {{}};
  document.querySelectorAll('.pairwise-range').forEach(function(s) {{
    var block = s.dataset.block;
    var a = s.dataset.a, b = s.dataset.b;
    var val = SAATY_VALUES[parseInt(s.value)];
    if(!blockData[block]) blockData[block] = {{}};
    blockData[block]["('"+a+"', '"+b+"')"] = val;
  }});

  // Rebuild Criteria Comparison from scratch using the slider data-parent,
  // so the exported .smt matches the CURRENT criteria tree (not any stale
  // saved comparisons that may be in SMT_BASE). Each cc_/sc_ slider carries
  // its parent name in data-parent; we group pairs by that parent.
  var ccOut  = {{}};
  var rscOut = out['Alternative Rating']['Rating Scales Comparison'];

  document.querySelectorAll('input.pairwise-range').forEach(function(s) {{
    var block  = s.dataset.block;
    var parent = s.dataset.parent;
    var a = s.dataset.a, b = s.dataset.b;
    var val = SAATY_VALUES[parseInt(s.value)];
    var pairKey = "('"+a+"', '"+b+"')";

    if(block.startsWith('cc_') || block.startsWith('sc_')) {{
      if(!ccOut[parent]) ccOut[parent] = {{}};
      ccOut[parent][pairKey] = val;
    }} else if(block.startsWith('rs_')) {{
      // Rating scale comparisons keep their existing structure; match by safe id
      Object.keys(rscOut).forEach(function(sub) {{
        if(block === 'rs_' + safeId(sub) && rscOut[sub].hasOwnProperty(pairKey)) {{
          rscOut[sub][pairKey] = val;
        }}
      }});
    }}
  }});

  // Replace the Criteria Comparison section with the freshly-built one
  out['Criteria Comparison']['Criteria Comparison'] = ccOut;

  // Add metadata
  var now = new Date();
  out['General']['ExpertSurveyDate'] = now.toISOString().slice(0,10);

  var blob = new Blob([JSON.stringify(out, null, 4)],
                     {{type: 'application/json'}});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'survey_responses.smt';
  a.click();
  URL.revokeObjectURL(a.href);
}}
</script>
</body>
</html>'''

    # Inject smt_base as JSON — done AFTER f-string to avoid brace-escaping issues
    # encode_tuples converts tuple keys back to strings so json.dumps can handle them
    import json as _json
    smt_base_json = _json.dumps(encode_tuples(smt_data), separators=(',', ':'))
    html = html.replace('__SMT_BASE_PLACEHOLDER__', smt_base_json)

    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
    return html
