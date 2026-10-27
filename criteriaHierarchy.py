#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/criteriaHierarchy.py
import html as _html
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .titleAndHelp import TitleAndHelp
from .constants import tab_titles

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jun 09, 2025'
__VERSION__ = '1.3.0'
__LAST_MODIFIED__ = 'Tuesday Jun 09, 2025'

TAB = 5
TAB_TITLE = tab_titles[TAB]

# ── Canvas constants ───────────────────────────────────────────────────────────
_A4_W      = 1123   # A4 landscape @ 96 dpi (297 mm)
_MARGIN_X  = 24
_MARGIN_TOP = 18
_CANVAS_W  = _A4_W  # SVG always A4 wide

# Box sizes
_P_W  = 112   # parent  width
_P_H  = 46    # parent  min-height
_C_W  = 88    # child   width
_C_H  = 36    # child   min-height
_RS_W = 88    # scale item width (same as child)
_RS_H = 22    # scale item min-height

# Gaps
_GAP_SIB    = 10    # horizontal between sibling cols
_GAP_ROW    = 40    # vertical between criterion rows (goal-bus to next bus)
_GAP_GOAL_B = 20    # goal-bot  → first row bus
_GAP_BUS_P  = 20    # bus       → parent top
_GAP_P_CHB  = 14    # parent-bot → child bus
_GAP_CHB_CH = 8     # child bus → child top
_GAP_CH_RS  = 10    # child-bot → first RS item
_RS_GAP     = 4     # vertical between RS items
_GAP_LEGEND = 28    # last-content-bot → legend

# Colours
_COL_GOAL_F = '#F5E6B8'; _COL_GOAL_S = '#C9A830'; _COL_GOAL_T = '#5a2a00'
_COL_P_F    = '#F2C98A'; _COL_P_S    = '#C47A20'; _COL_P_T    = '#4a1f00'
_COL_CH_F   = '#FFFFFF'; _COL_CH_S   = '#BBBBBB'; _COL_CH_T   = '#1a1a1a'
_COL_CHS_F  = '#2E86C1'; _COL_CHS_S  = '#1A5276'; _COL_CHS_T  = '#FFFFFF'
_COL_RS_F   = '#D5F5E3'; _COL_RS_S   = '#1E8449'; _COL_RS_T   = '#145A32'

_SW      = '1.5'
_SW_CH   = '1'
_SW_RS   = '0.8'
_LC      = '#999999'   # line colour (neutral)
_LC_RS   = '#1E8449'   # line colour (RS connector)


# ── Text helpers ───────────────────────────────────────────────────────────────

def _wrap(text: str, max_chars: int = 14) -> list:
    words = text.split(); lines, cur = [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip() if cur else w
    if cur:
        lines.append(cur)
    return lines or ['']


def _tspan(x, y, lines, fs, fw, fill, lh=14) -> str:
    total_h = len(lines) * lh
    y0 = y - total_h / 2 + lh / 2
    out = ''
    for i, ln in enumerate(lines):
        out += (
            f'<text x="{x:.1f}" y="{y0 + i*lh:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{fs}" font-weight="{fw}" '
            f'font-family="Arial,sans-serif" fill="{fill}">'
            f'{_html.escape(ln)}</text>\n'
        )
    return out


# ── Tree-data builder ──────────────────────────────────────────────────────────

def _build_tree_data(tree_dict: dict, rating_scales: dict) -> dict:
    result = {'goal': '', 'criteria': []}
    if not tree_dict:
        return result
    goal = list(tree_dict.keys())[0]
    result['goal'] = goal
    for item in tree_dict[goal].get('children', []):
        if isinstance(item, str):
            result['criteria'].append({'name': item, 'children': []})
        elif isinstance(item, dict):
            cname = list(item.keys())[0]
            ch = []
            for sub in item[cname].get('children', []):
                sname = sub if isinstance(sub, str) else list(sub.keys())[0]
                sl = rating_scales.get(sname, [])
                ch.append({'name': sname, 'has_scale': bool(sl), 'scale_items': sl})
            result['criteria'].append({'name': cname, 'children': ch})
    return result


# ── Row-packing (greedy) ───────────────────────────────────────────────────────

def _col_width(c: dict, show_sub: bool) -> int:
    """Minimum column width for criterion c."""
    n = len(c['children']) if show_sub else 0
    ch_w = n * _C_W + max(0, n - 1) * _GAP_SIB if n else 0
    return max(_P_W, ch_w)


def _pack_rows(criteria: list, show_sub: bool, available_w: int = None) -> list:
    """
    Greedy left-to-right packing.
    Returns list of rows, each row = list of criterion dicts.
    available_w is the actual pixel width available for criterion columns.
    If a single criterion is wider than available_w it goes alone on its row.
    """
    if available_w is None:
        available_w = _CANVAS_W - 2 * _MARGIN_X
    rows, cur_row, cur_w = [], [], 0
    for c in criteria:
        cw = _col_width(c, show_sub)
        gap = _GAP_SIB if cur_row else 0
        if cur_row and cur_w + gap + cw > available_w:
            rows.append(cur_row)
            cur_row, cur_w = [c], cw
        else:
            cur_row.append(c)
            cur_w += gap + cw
    if cur_row:
        rows.append(cur_row)
    return rows


def _row_content_width(row: list, show_sub: bool) -> int:
    """Total pixel width occupied by the criteria columns in a row."""
    if not row:
        return 0
    return sum(_col_width(c, show_sub) for c in row) + _GAP_SIB * (len(row) - 1)


# ── Per-row height calculator ──────────────────────────────────────────────────

def _row_metrics(row: list, show_sub: bool, show_scales: bool) -> dict:
    """
    Return height metrics for one row:
        max_p_h, max_c_h, global_max_rs, global_rs_h, row_content_h
    """
    max_p_h = _P_H
    for c in row:
        pl = _wrap(c['name'], 14)
        max_p_h = max(max_p_h, len(pl) * 14 + 10)

    max_c_h = _C_H
    if show_sub:
        for c in row:
            for ch in c['children']:
                cl = _wrap(ch['name'], 12)
                max_c_h = max(max_c_h, len(cl) * 13 + 10)

    global_max_rs = 0
    global_rs_h   = _RS_H
    if show_sub and show_scales:
        for c in row:
            for ch in c['children']:
                if ch['has_scale']:
                    global_max_rs = max(global_max_rs, len(ch['scale_items']))
                    for si in ch['scale_items']:
                        rl = _wrap(si, 12)
                        global_rs_h = max(global_rs_h, len(rl) * 12 + 6)

    # Total height consumed by this row (from bus top to last content bot)
    # bus → p_top: _GAP_BUS_P
    # p_top → p_bot: max_p_h
    # p_bot → ch_bus: _GAP_P_CHB   (only if children)
    # ch_bus → ch_top: _GAP_CHB_CH
    # ch_top → ch_bot: max_c_h
    # ch_bot → rs_end: _GAP_CH_RS + max_rs*(rs_h+_RS_GAP)
    has_ch = show_sub and any(c['children'] for c in row)
    has_rs = has_ch and show_scales and global_max_rs > 0

    h = _GAP_BUS_P + max_p_h
    if has_ch:
        h += _GAP_P_CHB + _GAP_CHB_CH + max_c_h
    if has_rs:
        rs_block = global_max_rs * global_rs_h + max(0, global_max_rs - 1) * _RS_GAP
        h += _GAP_CH_RS + rs_block

    return {
        'max_p_h': max_p_h,
        'max_c_h': max_c_h,
        'global_max_rs': global_max_rs,
        'global_rs_h': global_rs_h,
        'row_content_h': h,
        'has_ch': has_ch,
        'has_rs': has_rs,
    }


# ── SVG builder ────────────────────────────────────────────────────────────────

def _build_svg(tree_data: dict, show_sub: bool, show_scales: bool) -> tuple:
    goal     = tree_data.get('goal', 'Goal')
    criteria = tree_data.get('criteria', [])

    shapes, texts, lines_out = [], [], []

    def line(x1, y1, x2, y2, sw=_SW, col=_LC):
        lines_out.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{col}" stroke-width="{sw}"/>'
        )

    def rect(x, y, w, h, fill, stroke, rx=5, sw=_SW):
        shapes.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def dot(x, y, r=3.5, fill=_LC):
        shapes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>'
        )

    # ── Goal box ──────────────────────────────────────────────────────────────
    goal_lines = _wrap(goal, 44)
    goal_box_h = max(44, len(goal_lines) * 15 + 14)
    goal_box_w = min(_CANVAS_W - 2 * _MARGIN_X, 440)
    goal_mid   = _CANVAS_W / 2
    goal_x     = goal_mid - goal_box_w / 2
    y_goal_top = _MARGIN_TOP
    y_goal_bot = y_goal_top + goal_box_h
    goal_mid_y = y_goal_top + goal_box_h / 2

    rect(goal_x, y_goal_top, goal_box_w, goal_box_h,
         _COL_GOAL_F, _COL_GOAL_S, rx=7, sw='2')
    texts.append(_tspan(goal_mid, goal_mid_y,
                        goal_lines, 12, 'bold', _COL_GOAL_T, lh=15))

    # ── Spine geometry ────────────────────────────────────────────────────────
    LEFT_RESERVE = _MARGIN_X + 42   # room for "criteria" tag on spine
    BRACKET_W    = 20
    RIGHT_PAD    = _MARGIN_X
    SPINE_X      = LEFT_RESERVE
    ROW_START_X  = SPINE_X + BRACKET_W

    # Available width for criterion columns — used by _pack_rows to wrap rows
    available_w  = _CANVAS_W - ROW_START_X - RIGHT_PAD

    # ── Pack rows ─────────────────────────────────────────────────────────────
    rows             = _pack_rows(criteria, show_sub, available_w)
    n_rows           = len(rows)
    row_metrics_list = [_row_metrics(r, show_sub, show_scales) for r in rows]

    # ── Y positions ───────────────────────────────────────────────────────────
    y_cur   = y_goal_bot + _GAP_GOAL_B
    y_buses = []
    for rm in row_metrics_list:
        y_buses.append(y_cur)
        y_cur += rm['row_content_h'] + _GAP_ROW

    last_row_bot = y_buses[-1] + row_metrics_list[-1]['row_content_h']
    y_legend     = last_row_bot + _GAP_LEGEND
    total_h      = int(y_legend + 28)

    # ── Left spine ────────────────────────────────────────────────────────────
    # Horizontal: goal left edge → spine
    line(goal_x, goal_mid_y, SPINE_X, goal_mid_y, sw='2')
    # Vertical: goal mid-y → last row bus
    line(SPINE_X, goal_mid_y, SPINE_X, y_buses[-1], sw='2')

    # ── Render each row ───────────────────────────────────────────────────────
    for row_idx, (row, rm, y_bus) in enumerate(
            zip(rows, row_metrics_list, y_buses)):

        max_p_h       = rm['max_p_h']
        max_c_h       = rm['max_c_h']
        global_max_rs = rm['global_max_rs']
        global_rs_h   = rm['global_rs_h']
        has_ch        = rm['has_ch']
        has_rs        = rm['has_rs']

        y_p_top  = y_bus + _GAP_BUS_P
        y_p_bot  = y_p_top + max_p_h
        y_ch_bus = y_p_bot + _GAP_P_CHB
        y_ch_top = y_ch_bus + _GAP_CHB_CH
        y_ch_bot = y_ch_top + max_c_h
        y_rs_s   = y_ch_bot + _GAP_CH_RS

        # Column layout — starts at ROW_START_X
        col_widths  = [_col_width(c, show_sub) for c in row]
        p_centers   = []
        x_cur = ROW_START_X
        for cw in col_widths:
            p_centers.append(x_cur + cw / 2)
            x_cur += cw + _GAP_SIB

        # ── Bracket: spine → first criterion ─────────────────────────────
        line(SPINE_X, y_bus, p_centers[0], y_bus, sw='2')
        dot(SPINE_X, y_bus)

        # Horizontal bus across all criteria in this row
        if len(p_centers) > 1:
            line(p_centers[0], y_bus, p_centers[-1], y_bus)

        # ── "cont." label on spine for rows after the first ───────────────
        if row_idx > 0:
            # Small filled rounded rect as a tag on the spine junction
            TAG_W, TAG_H = 38, 14
            tag_x = SPINE_X - TAG_W - 4
            tag_y = y_bus - TAG_H / 2
            shapes.append(
                f'<rect x="{tag_x:.1f}" y="{tag_y:.1f}" '
                f'width="{TAG_W}" height="{TAG_H}" rx="3" '
                f'fill="{_COL_P_F}" stroke="{_COL_P_S}" stroke-width="1"/>'
            )
            texts.append(
                f'<text x="{tag_x + TAG_W/2:.1f}" y="{y_bus:.1f}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="9" font-weight="bold" '
                f'font-family="Arial,sans-serif" fill="{_COL_P_T}">'
                f'criteria</text>'
            )

        # ── Per-criterion boxes ───────────────────────────────────────────
        for i, (c, cx) in enumerate(zip(row, p_centers)):
            px = cx - _P_W / 2

            # bus → parent top
            line(cx, y_bus, cx, y_p_top)

            # Parent box — same orange style as row 1
            pl = _wrap(c['name'], 14)
            rect(px, y_p_top, _P_W, max_p_h,
                 _COL_P_F, _COL_P_S, rx=5, sw='1.5')
            texts.append(_tspan(cx, y_p_top + max_p_h / 2,
                                pl, 11, 'bold', _COL_P_T, lh=14))

            if not (show_sub and c['children']):
                continue

            # parent bot → child bus
            line(cx, y_p_bot, cx, y_ch_bus, sw=_SW_CH)

            children = c['children']
            n        = len(children)
            ch_bw    = n * _C_W + (n - 1) * _GAP_SIB
            ch_sx    = cx - ch_bw / 2
            ch_cxs   = [ch_sx + j * (_C_W + _GAP_SIB) + _C_W / 2 for j in range(n)]

            if n > 1:
                line(ch_cxs[0], y_ch_bus, ch_cxs[-1], y_ch_bus, sw=_SW_CH)

            for j, ch in enumerate(children):
                ccx = ch_cxs[j]
                line(ccx, y_ch_bus, ccx, y_ch_top, sw=_SW_CH)

                hs  = ch.get('has_scale', False)
                f_f = _COL_CHS_F if hs else _COL_CH_F
                f_s = _COL_CHS_S if hs else _COL_CH_S
                f_t = _COL_CHS_T if hs else _COL_CH_T
                rect(ccx - _C_W / 2, y_ch_top, _C_W, max_c_h,
                     f_f, f_s, rx=4, sw='1')
                cl = _wrap(ch['name'], 12)
                texts.append(_tspan(ccx, y_ch_top + max_c_h / 2,
                                    cl, 10, 'normal', f_t, lh=13))

                if not (show_scales and hs and ch['scale_items']):
                    continue

                line(ccx, y_ch_bot, ccx, y_rs_s, sw=_SW_RS, col=_LC_RS)
                for k, label in enumerate(ch['scale_items']):
                    iy = y_rs_s + k * (global_rs_h + _RS_GAP)
                    if k > 0:
                        line(ccx, iy - _RS_GAP, ccx, iy, sw=_SW_RS, col=_LC_RS)
                    rect(ccx - _RS_W / 2, iy, _RS_W, global_rs_h,
                         _COL_RS_F, _COL_RS_S, rx=3, sw='0.8')
                    rl = _wrap(label, 13)
                    texts.append(_tspan(ccx, iy + global_rs_h / 2,
                                        rl, 9, 'normal', _COL_RS_T, lh=11))

    # ── Legend ────────────────────────────────────────────────────────────────
    lx = _MARGIN_X
    ly = int(y_legend) + 10

    def leg(label, fill, stroke, tc='#444'):
        nonlocal lx
        shapes.append(
            f'<rect x="{lx}" y="{ly-10}" width="18" height="13" rx="3" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        texts.append(
            f'<text x="{lx+22}" y="{ly}" font-size="11" '
            f'font-family="Arial,sans-serif" fill="{tc}">'
            f'{_html.escape(label)}</text>'
        )
        lx += int(len(label) * 6.5) + 36

    leg('Criteria / supercriterios', _COL_P_F,   _COL_P_S)
    if show_sub:
        leg('Subcriterios',          _COL_CH_F,  _COL_CH_S)
        if show_scales:
            leg('Con Rating Scale',  _COL_CHS_F, _COL_CHS_S, _COL_CHS_T)
            leg('Valor de escala',   _COL_RS_F,  _COL_RS_S)

    body = ('\n'.join(lines_out) + '\n'
            + '\n'.join(shapes)   + '\n'
            + ''.join(texts))

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" id="ch-svg-main" '
        f'width="{_CANVAS_W}" height="{total_h}" '
        f'viewBox="0 0 {_CANVAS_W} {total_h}" '
        f'style="background:#ffffff;display:block;">\n'
        f'<rect width="{_CANVAS_W}" height="{total_h}" fill="#ffffff"/>\n'
        f'{body}\n</svg>'
    )
    return svg, _CANVAS_W, total_h

# ── HTML wrapper ───────────────────────────────────────────────────────────────

def _render_html(tree_data: dict, show_sub: bool,
                 show_scales: bool, uid: str) -> str:
    svg_str, svg_w, svg_h = _build_svg(tree_data, show_sub, show_scales)
    return f"""
<style>
#ch-outer-{uid}{{width:100%;overflow-x:auto;padding-bottom:6px;}}
#ch-wrap-{uid}{{display:inline-block;transform-origin:top left;transition:transform .15s;}}
.ch-tb-{uid}{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;}}
.ch-btn-{uid}{{font-size:12px;padding:5px 12px;border:1px solid #999;border-radius:4px;
  cursor:pointer;background:#f5f5f5;color:#333;font-family:Arial,sans-serif;white-space:nowrap;}}
.ch-btn-{uid}:hover{{background:#e0e0e0;}}
.ch-zl-{uid}{{font-size:12px;color:#555;font-family:Arial;min-width:42px;text-align:center;}}
</style>
<div class="ch-tb-{uid}">
  <button class="ch-btn-{uid}" onclick="chZ_{uid}(-.15)">&#x2212; Zoom</button>
  <span  class="ch-zl-{uid}"  id="ch-zl-{uid}">100%</span>
  <button class="ch-btn-{uid}" onclick="chZ_{uid}(+.15)">&#x2b; Zoom</button>
  <button class="ch-btn-{uid}" onclick="chRst_{uid}()">Reset</button>
  <button class="ch-btn-{uid}"
    style="background:#1a6b3a;color:#fff;border-color:#1a6b3a;"
    onclick="chDl_{uid}()">&#x21E9;&nbsp;Descargar JPG</button>
</div>
<div id="ch-outer-{uid}">
  <div id="ch-wrap-{uid}">{svg_str}</div>
</div>
<script>
(function(){{
  var s={1.0},W={svg_w},H={svg_h};
  window.chZ_{uid}=function(d){{
    s=Math.max(.25,Math.min(3,s+d));
    document.getElementById('ch-wrap-{uid}').style.transform='scale('+s+')';
    document.getElementById('ch-outer-{uid}').style.height=(H*s+20)+'px';
    document.getElementById('ch-zl-{uid}').textContent=Math.round(s*100)+'%';
  }};
  window.chRst_{uid}=function(){{
    s=1;
    document.getElementById('ch-wrap-{uid}').style.transform='scale(1)';
    document.getElementById('ch-outer-{uid}').style.height='';
    document.getElementById('ch-zl-{uid}').textContent='100%';
  }};
  window.chDl_{uid}=function(){{
    var svg=document.getElementById('ch-svg-main');
    var blob=new Blob([new XMLSerializer().serializeToString(svg)],
                     {{type:'image/svg+xml;charset=utf-8'}});
    var url=URL.createObjectURL(blob),img=new Image();
    img.onload=function(){{
      var sc=2,c=document.createElement('canvas');
      c.width=W*sc;c.height=H*sc;
      var ctx=c.getContext('2d');
      ctx.fillStyle='#fff';ctx.fillRect(0,0,c.width,c.height);
      ctx.drawImage(img,0,0,c.width,c.height);
      URL.revokeObjectURL(url);
      var a=document.createElement('a');
      a.download='criteria_hierarchy.jpg';
      a.href=c.toDataURL('image/jpeg',.95);a.click();
    }};
    img.src=url;
  }};
}})();
</script>
"""


# ── Widget ─────────────────────────────────────────────────────────────────────

class CriteriaHierarchy:
    def __init__(self, logger):
        self.logger = logger
        self.logger.log('info',
            f'Tab {TAB} - {TAB_TITLE}: Initializing CriteriaHierarchy')

        self._tree_data     = {'goal': '', 'criteria': []}
        self._rating_scales = {}
        self._uid           = 'ch1'

        self.title = TitleAndHelp(
            'Hierarchy of criteria and subcriteria',
            'docs/help_criteriaEditor.html'
        )
        self.toggle_subcriteria = widgets.ToggleButton(
            value=True, description='Show subcriteria',
            icon='sitemap', button_style='danger',
            layout=widgets.Layout(width='165px', height='34px'),
        )
        self.toggle_scales = widgets.ToggleButton(
            value=True, description='Show rating scales',
            icon='table', button_style='success',
            layout=widgets.Layout(width='175px', height='34px'),
        )
        self.toggle_subcriteria.observe(self._on_toggle, names='value')
        self.toggle_scales.observe(self._on_toggle, names='value')

        self._controls = widgets.HBox(
            [self.toggle_subcriteria, self.toggle_scales],
            layout=widgets.Layout(margin='8px 0 6px 0', gap='8px')
        )
        self.out      = widgets.Output()
        self.errorOut = widgets.Output()
        self.allWidgets = widgets.VBox([
            self.title.allWidgets, self._controls,
            self.out, self.errorOut,
        ])

    def update(self, tree_dict: dict, alternative_rating_dict: dict = None):
        self.logger.log('info', 'CriteriaHierarchy: updating')
        rating_scales: dict = {}
        if alternative_rating_dict:
            for name, vals in alternative_rating_dict.get(
                    'Rating Scales Creation', {}).items():
                rating_scales[name] = [v for v in vals if isinstance(v, str)]
        self._rating_scales = rating_scales
        self._tree_data = _build_tree_data(tree_dict, rating_scales)
        self._render()

    def get_all_outputs(self):
        return {}

    def _on_toggle(self, _change):
        self._render()

    def _render(self):
        show_sub    = self.toggle_subcriteria.value
        show_scales = self.toggle_scales.value and show_sub
        self.toggle_scales.disabled = not show_sub
        with self.out:
            clear_output(wait=True)
            if not self._tree_data.get('criteria'):
                display(HTML(
                    '<p style="color:#888;font-size:13px;margin:16px 0;">'
                    'No hay criterios definidos todavía. '
                    'Define la jerarquía en la pestaña <b>Criteria</b>.</p>'
                ))
            else:
                display(HTML(_render_html(
                    self._tree_data, show_sub, show_scales, self._uid)))
