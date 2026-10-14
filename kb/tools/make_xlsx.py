"""Generate the two workbooks from the YAML knowledge base (the YAML files stay the single source of truth).

FairRyde_KB_v0.1.xlsx          the knowledge base, regenerated on every build; it holds no labels.
FairRyde_Annotation_v0.1.xlsx  the annotation workbook (ONT.5). Created once; the build refuses to overwrite it when any
                               HUMAN cell is filled or when it is open in Excel (ONT.11.3: never overwrite human edits),
                               and backs it up before replacing an untouched copy.

Every string written to either workbook passes through the DISP-002 pseudonymization dictionary (ONT.11), and build_kb.py
scans both files afterwards for names, plates and other identifiers (counts only).
"""
from __future__ import annotations

import re
import shutil
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import explain
import privacy_scan
import stats as statsmod
from engine_noshow import evidence_index

FONT = "Arial"
F_BASE = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=FONT, size=14, bold=True)
F_SUB = Font(name=FONT, size=11, bold=True, color="1F4E78")
F_NOTE = Font(name=FONT, size=9, italic=True, color="595959")
FILL_HEAD = PatternFill("solid", fgColor="1F4E78")
FILL_CAT = PatternFill("solid", fgColor="DDEBF7")
FILL_HUMAN = PatternFill("solid", fgColor="FFF2CC")
FILL_AUTO = PatternFill("solid", fgColor="EDEDED")
FILL_AI = PatternFill("solid", fgColor="DDEBF7")
FILL_EXAMPLE = PatternFill("solid", fgColor="E2EFDA")
FILL_OK = PatternFill("solid", fgColor="E2EFDA")
FILL_BAD = PatternFill("solid", fgColor="FCE4D6")
CRED_FILLS = {"A": FILL_OK, "B": PatternFill("solid", fgColor="FFF2CC"), "C": FILL_BAD, "D": PatternFill("solid", fgColor="F8CBAD")}
GROUP_FILLS = {"INPUT": "8EA9DB", "ANSWER": "F4B084", "BASIS": "A9D08E", "RELATION": "B4A7D6", "PROCESS": "BFBFBF"}
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

ANN_SHEET = "标注表"
DATA_FIRST, DATA_LAST = 6, 305     # annotation data rows; row 5 is the example row
DT_COLS = {"booked_at", "matched_at", "scheduled_time", "driver_arrival_time", "driver_wait_start", "cancellation_time", "filed_at"}


# ---------------------------------------------------------------------------------------------- helpers
def _s(v):
    """Cell-safe value: lists joined with '; ', dicts flattened, dates as ISO text, None as ''."""
    if v is None:
        return ""
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (list, tuple)):
        return "; ".join(str(_s(x)) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_s(x)}" for k, x in v.items())
    return v


def table(ws, row, headers, rows, widths=None, wrap=True, fills=None, cols=None):
    """Write a header row and data rows starting at `row`. Returns the next free row.
    cols: optional list of sheet column numbers for each logical column (to line blocks up with wide columns)."""
    cols = cols or list(range(1, len(headers) + 1))
    for k, h in enumerate(headers):
        c = ws.cell(row=row, column=cols[k], value=h)
        c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, CENTER, BORDER
    for i, r in enumerate(rows, 1):
        for k, v in enumerate(r):
            val = _s(v)
            c = ws.cell(row=row + i, column=cols[k], value=val)
            if isinstance(val, str) and val.startswith("="):
                c.data_type = "s"          # documentation text, not a formula
            c.font, c.border = F_BASE, BORDER
            if wrap:
                c.alignment = WRAP
            if fills and fills.get(i):
                c.fill = fills[i]
    if widths:
        for j, w in enumerate(widths, 1):
            if w:
                ws.column_dimensions[get_column_letter(j)].width = w
    return row + len(rows) + 2


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    if sub:
        ws["A2"] = sub
        ws["A2"].font = F_NOTE
    return 4


def heading(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = F_SUB
    return row + 1


def para(ws, row, text, width_cols=8, height=None, font=None):
    c = ws.cell(row=row, column=1, value=text)
    c.font = font or F_BASE
    c.alignment = WRAP
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width_cols)
    if height:
        ws.row_dimensions[row].height = height
    return row + 1


def finish(ws, freeze="A2", filter_ref=None):
    if freeze:
        ws.freeze_panes = freeze
    if filter_ref:
        ws.auto_filter.ref = filter_ref
    ws.sheet_view.zoomScale = 100


def _text_width(s: str) -> int:
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _autofit_rows(ws, min_row=1, max_row=None, line_h=13.5, max_h=360):
    """Explicit row heights from text length and column width, so wrapped text is visible in Excel too."""
    import math
    widths = {k: (v.width or 9) for k, v in ws.column_dimensions.items()}
    merged_w = {}
    for mr in ws.merged_cells.ranges:
        merged_w[(mr.min_row, mr.min_col)] = sum(widths.get(get_column_letter(c), 9) for c in range(mr.min_col, mr.max_col + 1))
    for row in ws.iter_rows(min_row=min_row, max_row=max_row or ws.max_row):
        lines = 1
        for c in row:
            if c.value is None or c.data_type == "f":
                continue
            colw = merged_w.get((c.row, c.column), widths.get(c.column_letter, 9))
            n = sum(max(1, math.ceil(_text_width(part) * 1.2 / max(colw - 1, 1))) for part in str(c.value).split("\n"))
            lines = max(lines, n)
        if lines > 1:
            ws.row_dimensions[row[0].row].height = min(max_h, lines * line_h + 2)


def _page_setup(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _font_pass(wb):
    """Arial everywhere (keep bold, italic, size, color)."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                f = c.font
                if f is None or f.name != FONT:
                    c.font = Font(name=FONT, size=f.size or 10, bold=f.bold, italic=f.italic, color=f.color)


def _pseudo_pass(wb, terms):
    """ONT.11 safety net: replace dictionary terms (names, name tokens, plate) in every string cell and comment."""
    ordered = sorted(terms, key=lambda x: -len(x[0]))
    pats = [(re.compile(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])", re.I), code) for t, code, _ in ordered]
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.data_type != "f":
                    v = c.value
                    for p, code in pats:
                        v = p.sub(code, v)
                    if v != c.value:
                        c.value, n = v, n + 1
    return n


def _finalize(wb, skip_autofit=()):
    _font_pass(wb)
    for ws in wb.worksheets:
        if ws.sheet_state == "hidden":
            continue
        _page_setup(ws)
        if ws.title in skip_autofit:
            _autofit_rows(ws, 1, 5)          # legend and headers of the annotation table (row 1 is merged)
        else:
            _autofit_rows(ws, 3)             # rows 1 and 2 hold the title and subtitle, which overflow to the right


# ============================================================================================== KB workbook
def s_readme(wb, kb, st, runs, rep, tests, ann_status, dt_enum, out_scan=None):
    ws = wb.active
    ws.title = "00_说明"
    r = title(ws, "FairRyde 知识库 v0.1（Taxonomy · Ontology · Rules）",
              f"按 ChordX 知识库协议 ONT.1 到 ONT.11 编写；生成日期 {kb.y['rules']['meta']['updated']}；状态 draft，待曹老师审核")
    org = runs["organizer_case"]
    t, tier = org["trace"], org["tier"]
    n_ok = sum(x["ok"] for x in tests)
    lines = [
        ("这是什么", "Ryde 赛道 FairRyde 的知识库：三层（Taxonomy 是哪一类；Ontology 有哪些实体、角色、关系和事件；Rules 什么条件下得出什么结论），加上协议要求的数据清单、操作指引、参考数据表、标注方案和验证方案。"),
        ("两个文件", "FairRyde_KB_v0.1.xlsx（本文件）：知识库，每次运行 build_kb.py 重新生成，不放任何标注。FairRyde_Annotation_v0.1.xlsx：标注工作簿，脚本只建一次；只要有人填过人工列，或文件正在 Excel 或 LibreOffice 里打开，脚本就不会覆盖它（ONT.11.3）。"
                     f"本次运行：{ann_status['message']}"),
        ("唯一真源", "kb/ 目录下的 YAML 文件。本工作簿由 build_kb.py 从 YAML 生成，改内容请改 YAML 再重新生成，不要直接改这里。"),
        ("校验结果", f"规则 {st['n_rules']} 条；逐字引文 {st['n_quotes_verified']} 条与原文一致，不符 {st['n_quotes_bad']} 条；"
                 f"DISP-002 的 {st['n_leaves']} 个字段全部映射到本体；决策表 {dt_enum['combinations']} 种输入组合每种恰好命中一行；"
                 f"引擎自测 {n_ok}/{len(tests)} 通过；"
                 + (f"生成文件的隐私泄漏扫描命中 {out_scan['total']} 处；" if out_scan is not None else "生成文件的隐私泄漏扫描见 check_report.md；")
                 + f"错误 {st['n_errors']} 个，警告 {st['n_warns']} 个。"),
        ("DISP-002 推演", f"组织方参数档（案件自带政策对象）下结果 {t.outcome}，与组织方期望一致；决策表 {t.dt_row} 行；置信度 {t.confidence['C']}；"
                        f"自治等级 {tier['tier']}（{ {'AUTO': '自动执行', 'APPROVE': '人工一键批准', 'HUMAN': '人工裁决'}.get(tier['tier'], '') }）"
                        + ("，原因：" + "；".join(tier["triggers"]) if tier["triggers"] else "") + "。详见 15 页。"),
        ("可信度", "A：组织方数据或文字、现行 Ryde 用户条款、12 个月内编辑过且不处在已知矛盾一方的 Ryde 帮助中心条款；B：更早或有矛盾的 Ryde 文字、需解释的法规、官方指引；C：同业做法（通用假设）；D：FairRyde 自定（通用假设，需确认）。"),
        ("模式", "HARD：可以写成代码；READ：必须回头读原文判断；HARD+READ：代码核心加需读原文的部分。"),
        ("自治等级", "AUTO 自动执行；APPROVE AI 给暂定裁决、人一键批准；HUMAN 人来裁决（安全、涉刑、账户处罚，以及规则决定不了、结果为 ESCALATE_HUMAN 的案件）。与可信度 A 到 D 是两套不同的东西。"),
    ]
    r = table(ws, r, ["项目", "说明"], lines, widths=[16, 120])
    r = heading(ws, r, "各页内容")
    pages = [
        ("01_协议对照", "逐条对照 ChordX 协议：之前做了什么、现在做到哪、在哪个文件、还缺什么"),
        ("02_决策目标与范围", "ONT.4 Step 1 决策目标、能力问题、最小够用范围、待办、与运行节点的对应（ONT.7）"),
        ("03_数据清单", "ONT.3：要收集的数据、谁提供、格式、属于哪层、敏感度、缺了怎么办"),
        ("04_Taxonomy", "全部受控词表（争议类型用 Ryde 帮助中心的原词，带来源文章）"),
        ("05_实体与属性", "Ontology 实体，每个属性对应 DISP-002 的哪个字段；事实认定类型和取值"),
        ("06_角色与关系", "角色不是实体（ONT.4 Step 2、ONT.8）；实体之间的关系"),
        ("07_事件与状态", "谁对谁做了什么、改变了什么状态；状态机（每个状态可达、终止状态）；新建还是更新"),
        ("08_DISP-002映射", "组织方样例每个字段映射到本体，值能否落进词表（样例值已脱敏）"),
        ("09_Rules", "全部规则：来源原文、可信度、HARD/READ、参数、产出"),
        ("10_决策表", "乘客缺席取消费的决策表：前提、输入、每行结果和可信度"),
        ("11_参考数据", "参数档和参考表：值、来源、文件日期、读取日期、可信度、合理区间"),
        ("12_操作指引", "每类争议的操作步骤（ONT.10b），每步一个原语"),
        ("13_审批权限", "自治等级 AUTO / APPROVE / HUMAN、人工批准条件、升级门"),
        ("14_来源登记", "所有被引用的文件，Ryde 文章带编辑日期"),
        ("15_DISP-002三层视图", "同一份单据在三层里的样子（ONT.2），推演过程、敏感性测试、读法测试、给双方的解释"),
        ("16_引擎自测", f"{len(tests)} 个单因素变体，检验规则卡与参考引擎一致（不是标准答案）"),
        ("17_标注方案", "标注表的列设计、验证方案、实体覆盖（标注本身在 FairRyde_Annotation_v0.1.xlsx）"),
        ("18_待决问题", f"待决定事项 D1 到 D{len(kb.y['open_items']['decisions'])}、给曹老师和组织方的问题"),
    ]
    table(ws, r, ["页", "内容"], pages, widths=[22, 120])
    finish(ws, freeze=None)


def s_gap(wb, kb, st):
    ws = wb.create_sheet("01_协议对照")
    r = title(ws, "对照 ChordX 知识库协议：做了什么、还缺什么", "之前 = 10 月 4 日初步研究；现在 = 知识库 v0.1（经独立审查后修正）")
    rows = [(x["clause"], x["requirement"], x["before"], statsmod.fill(x["now"], st), x["where"], x["status"], x["remaining"])
            for x in kb.y["protocol_gap"]["rows"]]
    table(ws, r, ["条款", "协议要求", "之前", "现在", "位置", "状态", "还缺"], rows, widths=[11, 30, 42, 60, 30, 9, 26])
    for i, x in enumerate(rows, 1):
        ws.cell(row=r + i, column=6).fill = FILL_OK if x[5] == "已做" else FILL_BAD
    finish(ws, freeze=f"C{r+1}", filter_ref=f"A{r}:G{r+len(rows)}")


def s_scope(wb, kb, runs):
    ws = wb.create_sheet("02_决策目标与范围")
    sc = kb.y["scope"]
    r = title(ws, "决策目标与范围（ONT.4 Step 1、Step 6；ONT.7；ONT.10）")
    dg = sc["decision_goal"]
    r = heading(ws, r, "决策目标")
    r = para(ws, r, dg["zh"], 6, 75)
    r = para(ws, r, dg["statement"], 6, 90, F_NOTE)
    r = table(ws, r + 1, ["项目", "内容"], [
        ("决策方", dg["decision_owner"]), ("使用者", dg["users"]),
        ("FairRyde 永远不决定", dg["never_decided_by_fairryde"]), ("成功标准", dg["success_criteria"]),
    ], widths=[22, 110])
    r = heading(ws, r, "赛题原文要求（手册第 5 节，逐字核对）")
    r = table(ws, r, ["原文", "来源"], [(x["quote"], x["source"]) for x in dg["track_requirements"]], widths=[100, 16])
    run = runs["organizer_case"]
    org = run["trace"]
    answers = {
        0: f"{org.claim_type}", 1: f"{kb.disp002['trip_data']['trip_id']}，{org.relation}", 2: org.profile,
        3: f"{org.findings['F-WAIT-ANCHOR']['value'][11:19]} 开始，等了 {int(org.findings['F-WAIT-ELAPSED']['value'])} 秒",
        4: f"到达有效 {org.findings['F-ARRIVAL-VALID']['value']}；在场 {org.findings['F-PRESENCE']['value']}",
        5: f"{org.findings['F-CONTACT']['value']}（司机 {org.contact_detail['driver_calls']} 通电话、{org.contact_detail['driver_messages']} 条消息）",
        6: org.findings["F-RIDER-EVIDENCE"]["value"], 7: f"相距 {org.findings['F-PIN-VENUE']['value']:,} m",
        8: f"{org.outcome}；收款方 {org.remedy.get('fee_payee')}；金额 S${org.findings['F-CHARGE-AMOUNT']['value']['charged']:.2f}",
        9: f"自治等级 {run['tier']['tier']}", 10: "见 15 页的解释草稿",
    }
    r = heading(ws, r, "能力问题（三层必须能在 DISP-002 上回答，ONT.1 用真实样本验证）")
    r = table(ws, r, ["问题", "由谁回答", "DISP-002 的答案"],
              [(q["q"], q["answered_by"], answers.get(i, "")) for i, q in enumerate(sc["competency_questions"])], widths=[50, 50, 50])
    s = sc["scope_v0_1"]
    r = heading(ws, r, "v0.1 范围（最小够用）")
    r = table(ws, r, ["范围", "类型"], [
        ("自动裁决 ADJUDICATE", s["adjudicate"]), ("需人工批准 ADJUDICATE_WITH_APPROVAL", s["adjudicate_with_approval"]),
        ("只分流 TRIAGE_TO_HUMAN", s["triage_to_human"]), ("非争议转客服 ROUTE_TO_SUPPORT", s["route_to_support"]),
        ("手册四类对应", s["handbook_mapping"]), ("为什么选这些", s["why_these"]), ("停止条件", s["stop_rule"]),
    ], widths=[34, 110])
    r = heading(ws, r, "待办（刻意不放进 v0.1）")
    r = table(ws, r, ["#", "内容"], [(i + 1, x) for i, x in enumerate(sc["backlog"])])
    r = heading(ws, r, "起点路线与离线 / 运行分开（ONT.10.1、ONT.10.4）")
    r = table(ws, r, ["项目", "内容"], [("条件", sc["start_route"]["condition"]), ("路线", sc["start_route"]["route"]),
                                     ("第一阶段日志", sc["start_route"]["phase_1_logging"]), ("评测集隔离", sc["start_route"]["eval_separation"]),
                                     ("知识库的位置", sc["offline_vs_runtime"]["knowledge_base_is"]),
                                     ("离线流程", sc["offline_vs_runtime"]["offline_flow"]), ("运行流程", sc["offline_vs_runtime"]["runtime_flow"])])
    r = heading(ws, r, "知识库与运行节点的对应（ONT.7，节点字母待 chordx_core.md 核对）")
    r = para(ws, r, sc["runtime_mapping"]["note"], 4, 45, F_NOTE)
    table(ws, r, ["运行节点", "ChordX 节点", "读取的知识", "产出"],
          [(x["node"], x["chordx_node"], x["reads"], x["writes"]) for x in sc["runtime_mapping"]["rows"]], widths=[34, 30, 60, 40])
    finish(ws, freeze=None)


def s_inventory(wb, kb):
    ws = wb.create_sheet("03_数据清单")
    r = title(ws, "数据清单（ONT.3）", kb.y["inventory"]["meta"]["sensitivity_note"])
    rows = [(i + 1, x["item"], x["provider"], x["format"], x["layer"], x["sensitivity"], x["status"], x["if_missing"])
            for i, x in enumerate(kb.y["inventory"]["items"])]
    table(ws, r, ["#", "项目", "谁提供", "格式", "属于哪层", "敏感度（暂定）", "状态", "缺了怎么办"], rows, widths=[4, 44, 18, 18, 30, 16, 16, 44])
    finish(ws, freeze=f"B{r+1}", filter_ref=f"A{r}:H{r+len(rows)}")


def s_taxonomy(wb, kb):
    ws = wb.create_sheet("04_Taxonomy")
    meta = kb.y["taxonomy"]["meta"]
    r = title(ws, "Taxonomy：受控词表（它属于哪一类？）", meta["authority"])
    r = para(ws, r, "放层标准：" + meta["placement_test"], 10, 45, F_NOTE)
    r = para(ws, r, "编辑规则：" + " ".join(meta["editing_rules"]), 10, 60, F_NOTE)
    rows, fills = [], {}
    for v in kb.y["taxonomy"]["vocabularies"]:
        vid = v["id"]
        closed = f"封闭词表：{v.get('closed_reason')}" if v.get("closed") else ""
        first = True
        for code, x in kb.vocab[vid].items():
            notes = [f"{k}: {_s(x[k])}" for k in ("note", "aliases", "observed_in_DISP002", "tier", "outcome", "handbook", "actor", "context")
                     if k in x and x[k] not in (None, "")]
            if closed and first:
                notes.append(closed)
            first = False
            terms = list(x.get("term_sources", []) or [])
            if x.get("term_source"):
                terms.append(x["term_source"])
            rows.append((vid, v.get("zh", ""), code, x.get("_parent") or "", x.get("level", ""), x.get("label", ""), x.get("zh", ""),
                         x.get("definition", ""), x.get("excludes", ""), x.get("scope", ""), x.get("rule_family", ""),
                         x.get("playbook", ""), x.get("organizer_code", "") or "", terms, "; ".join(notes)))
            if x.get("level") == "category":
                fills[len(rows)] = FILL_CAT
    table(ws, r, ["词表", "词表中文", "代码", "上级", "层级", "标签", "中文", "定义", "不包括", "范围", "规则族", "操作指引", "组织方代码", "来源用语（Ryde 原词与文章）", "备注"],
          rows, widths=[13, 12, 24, 8, 8, 30, 22, 40, 30, 22, 7, 16, 14, 50, 30], fills=fills)
    finish(ws, freeze=f"D{r+1}", filter_ref=f"A{r}:O{r+len(rows)}")


def s_entities(wb, kb):
    ws = wb.create_sheet("05_实体与属性")
    meta = kb.y["ontology"]["meta"]
    r = title(ws, "Ontology：实体与属性（有哪些东西？）", meta["authority"])
    r = para(ws, r, "放层标准：" + meta["placement_test"], 10, 40, F_NOTE)
    rows, fills = [], {}
    for e in kb.y["ontology"]["entities"]:
        rows.append((e["id"], e["name"], e.get("zh", ""), e.get("kind", ""), e.get("definition", e.get("source", "")),
                     e.get("identity", e.get("id_pattern", "")), "", "", "", "", "", "", e.get("rules_use", e.get("caution", ""))))
        fills[len(rows)] = FILL_CAT
        for a in e.get("attributes", []) or []:
            rows.append(("", "", "", "", "", "", a["name"], a.get("type", ""), a.get("source_field", ""), a.get("required", ""),
                         "PII" if a.get("pii") else "", "数据缺口" if a.get("data_gap") else ("派生" if a.get("derived") else ""), a.get("note", "")))
    table(ws, r, ["实体", "名称", "中文", "类别", "定义 / 来源", "标识", "属性", "类型", "DISP-002 字段", "必填", "敏感", "缺口", "备注"],
          rows, widths=[15, 16, 10, 12, 40, 18, 20, 24, 34, 6, 6, 9, 50], fills=fills)
    r2 = heading(ws, len(rows) + r + 3, "事实认定类型（Finding）：取值是决策表的输入，脚本核对两边一致")
    table(ws, r2, ["代码", "含义", "取值", "单位", "由哪条规则产出"],
          [(f["code"], f["label"], f.get("values", ""), f.get("unit", ""), f["produced_by"]) for f in kb.y["ontology"]["finding_types"]])
    finish(ws, freeze=f"B{r+1}")


def s_roles(wb, kb):
    ws = wb.create_sheet("06_角色与关系")
    r = title(ws, "角色与关系（角色不是实体：同一个账户在不同行程、工单里角色不同）", "本体里的每个角色都在 TX-ROLE 词表里（脚本检查）")
    rows = [(x["code"], x.get("played_by", ""), x.get("in", ""), x.get("source_quote", x.get("source", "")), x.get("example_DISP002", ""), x.get("note", ""))
            for x in kb.y["ontology"]["roles"]]
    r = table(ws, r, ["角色", "由谁扮演", "在什么里", "来源（原文）", "DISP-002 示例", "备注"], rows, widths=[26, 26, 22, 70, 30, 50])
    r = heading(ws, r, "角色说明")
    r = table(ws, r, ["#", "说明"], [(i + 1, x) for i, x in enumerate(kb.y["ontology"]["role_notes"])])
    r = heading(ws, r, "关系")
    table(ws, r, ["主体", "关系", "客体", "基数", "来源 / 说明"],
          [(x["subject"], x["predicate"], x["object"], x.get("cardinality", ""), "; ".join(_s(x.get(k)) for k in ("source", "qualifier", "note") if x.get(k)))
           for x in kb.y["ontology"]["relations"]])
    finish(ws, freeze=None)


def s_events(wb, kb, rep):
    ws = wb.create_sheet("07_事件与状态")
    r = title(ws, "事件与状态（谁对谁做了什么、引起什么状态变化；新事件还是更新，ONT.4 Step 3）", "本体事件与 TX-EVENT 一一对应（脚本检查）")
    obs = {c: x.get("observed_in_DISP002") for c, x in kb.vocab["TX-EVENT"].items()}
    rows = [(x["code"], x.get("actor", ""), x.get("target", ""), x.get("changes", ""), "更新" if x.get("is_update") else "", obs.get(x["code"]), x.get("note", ""))
            for x in kb.y["ontology"]["events"]]
    r = table(ws, r, ["事件", "行为方", "对象", "状态变化", "是否更新", "DISP-002 出现", "备注"], rows, widths=[26, 20, 22, 60, 9, 12, 60])
    r = heading(ws, r, "状态机（脚本检查：每个状态都有事件能到达；没有出口的状态正好是声明的终止状态）")
    smsum = rep.tables.get("state_machines", {})
    r = table(ws, r, ["状态机", "状态", "可达 / 总数", "终止状态"],
              [(k, v, f"{smsum.get(k, {}).get('reachable', '')} / {smsum.get(k, {}).get('states', '')}", smsum.get(k, {}).get("terminal", "") or "无（每个状态都能再变化）")
               for k, v in kb.y["ontology"]["state_machines"].items()])
    r = heading(ws, r, "新建还是更新（Matching，规则 MAT-02）")
    table(ws, r, ["#", "规则"], [(i + 1, x) for i, x in enumerate(kb.y["ontology"]["new_vs_update"])])
    finish(ws, freeze=None)


def s_mapping(wb, kb, rep):
    ws = wb.create_sheet("08_DISP-002映射")
    r = title(ws, "DISP-002 每个字段映射到本体（ONT.1：用真实样本验证）",
              f"{len(rep.tables['disp002_mapping'])} 条映射覆盖全部 {rep.tables['disp002_leaf_count']} 个叶子字段；有词表的字段逐个值检查能否落进词表；样例值里的姓名和车牌已替换成代码（ONT.11）")
    rows = [(m["path"], m["maps_to"], m["vocab"], m["sample"], m["n_values"], m["resolved"], m["status"], m["note"]) for m in rep.tables["disp002_mapping"]]
    table(ws, r, ["DISP-002 路径", "映射到", "词表", "示例值", "值个数", "落词表结果", "状态", "备注"], rows, widths=[38, 46, 16, 40, 7, 44, 10, 16])
    finish(ws, freeze=f"B{r+1}", filter_ref=f"A{r}:H{r+len(rows)}")


def s_rules(wb, kb, rep):
    ws = wb.create_sheet("09_Rules")
    meta = kb.y["rules"]["meta"]
    r = title(ws, "Rules：规则（什么条件下得出什么结论？）每条规则都有来源原文、可信度、HARD/READ", meta["authority"])
    r = para(ws, r, "可信度：" + " ".join(f"{k}: {v}" for k, v in kb.y["rules"]["credibility_scale"].items()), 12, 75, F_NOTE)
    r = para(ws, r, "可信度原则：" + kb.y["rules"]["credibility_principle"], 12, 45, F_NOTE)
    r = para(ws, r, "决定性规则的定义（用于自治等级）：" + kb.y["rules"]["decisive_definition"], 12, 60, F_NOTE)
    qmap = {}
    for q in rep.quotes:
        qmap.setdefault(q["rule"], []).append(q)
    status_zh = {"VERIFIED": "逐字核对通过", "PARAPHRASE": "转述（无逐字原文）", "NO_QUOTE (design assumption)": "设计假设（无原文）",
                 "KEY_STATEMENT_ONLY": "仅在摘录中找到", "NOT_FOUND": "未找到", "NO_LOCAL_COPY": "无本地副本"}
    rows = []
    for rid in kb.rule_order:
        x = kb.rules[rid]
        srcs, checks = [], []
        for q in qmap.get(rid, []):
            d = kb.sources.get(q["doc"], {})
            head = f"{q['i']}) [{q['type']}] {q['doc']}" + (f" '{d.get('title', '')}'" if q["doc"].startswith("RYDE-") and q["doc"] != "RYDE-TOU" else "")
            head += f" ({q['doc_date']})" if q["doc_date"] else ""
            head += f" {q['clause']}" if q["clause"] else ""
            head += f" [{q['profile']}]" if q["profile"] else ""
            srcs.append(head + (f": \"{q['quote']}\"" if q["quote"] else "") + (f" ({q['note']})" if q["note"] else ""))
            checks.append(f"{q['i']}) {status_zh.get(q['status'], q['status'])}")
        rows.append((rid, x["family"], x["type"], x["name"], x.get("zh", ""), x["statement"], x.get("applies_to"), x.get("params", []),
                     "; ".join(filter(None, [_s(x.get("produces", [])), _s(x.get("produces_finding"))])), "\n".join(srcs), "\n".join(checks),
                     x["credibility"], x.get("credibility_note", ""), x["mode"], x["status"], x.get("decision_table", "")))
    table(ws, r, ["规则", "族", "类型", "名称", "中文说明", "规则（英文原句）", "适用类型", "参数", "产出（理由代码 / 事实）", "来源与原文", "原文核对", "可信度", "可信度说明", "模式", "状态", "决策表"],
          rows, widths=[10, 6, 11, 26, 40, 50, 18, 22, 26, 80, 16, 7, 40, 10, 7, 12])
    for i in range(1, len(rows) + 1):
        c = ws.cell(row=r + i, column=12)
        c.alignment, c.fill = CENTER, CRED_FILLS[rows[i - 1][11]]
    finish(ws, freeze=f"E{r+1}", filter_ref=f"A{r}:P{r+len(rows)}")


def s_dt(wb, kb, rep):
    ws = wb.create_sheet("10_决策表")
    dt = kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]
    summ = rep.tables["decision_tables"]["DT-CW-NOSHOW"]
    r = title(ws, f"决策表 DT-CW-NOSHOW：{dt['name']}（命中策略 {dt['hit_policy']}）",
              f"{summ['combinations']} 种输入组合，缺口 {summ['gaps']}，重叠 {summ['overlaps']}；rules = 结论所依赖的全部规则，行的可信度 = 其中最弱的一条（脚本检查）；also = 同时触发但不改变结果的规则")
    r = para(ws, r, "前提：" + dt["precondition"], 13, 30, F_NOTE)
    r = para(ws, r, "可信度说明：" + dt["credibility_note"], 13, 45, F_NOTE)
    names = list(dt["inputs"])
    rows, fills = [], {}
    for row in dt["rows"]:
        rows.append([row["row"]] + [_s(row["when"].get(n, "任意")) for n in names]
                    + [row["outcome"], row["reason"], row.get("flags", []), row.get("rules", []), row.get("also", []), row.get("credibility"),
                       summ["hits_per_row"][row["row"]], row.get("plain", "")])
    r0 = r
    r = table(ws, r, ["行"] + names + ["结果", "理由", "标记", "依赖的规则", "同时触发", "可信度", "命中组合数", "解释用语（plain）"], rows,
              widths=[6, 14, 14, 12, 14, 16, 26, 18, 30, 26, 8, 10, 60])
    for i, row in enumerate(dt["rows"], 1):
        c = ws.cell(row=r0 + i, column=len(names) + 7)
        c.fill, c.alignment = CRED_FILLS[row["credibility"]], CENTER
    r = heading(ws, r, "输入从哪来（取值与本体的事实认定类型一致）")
    r = table(ws, r, ["输入", "来源", "取值"], [(k, v, dt["inputs"][k]) for k, v in dt["input_sources"].items()], cols=[2, 9, 13])
    para(ws, r, "表后步骤：" + dt["after_table"], 10, 45, F_NOTE)
    finish(ws, freeze=None)


def s_ref(wb, kb):
    ws = wb.create_sheet("11_参考数据")
    meta = kb.y["reference_data"]["meta"]
    r = title(ws, "参考数据表（ONT.10b）：值、来源、日期、可信度、合理区间", meta["not_live_integration"])
    r = para(ws, r, meta["how_profiles_work"], 12, 30, F_NOTE)
    prof_notes = [(name, p.get("applies_when", ""), p.get("effective_from", ""),
                   (p.get("built_from_case", p.get("effective_note", "")) + (f" 回退参数档：{p['fallback_profile']}" if p.get("fallback_profile") else "")))
                  for name, p in kb.y["reference_data"]["profiles"].items()]
    r = table(ws, r, ["参数档", "适用条件", "生效日期", "说明"], prof_notes, widths=[18, 50, 14, 80])
    rows = []
    for prof, params in kb.profiles.items():
        for k, v in params.items():
            rows.append((prof, k, v.get("value"), v.get("unit", ""), v.get("source_type", ""), v.get("source", ""), v.get("source_date", ""),
                         v.get("retrieved", ""), v.get("credibility", ""), v.get("plausible_range", ""), v.get("note", v.get("conflict", ""))))
        for k, v in (kb.y["reference_data"]["profiles"][prof].get("case_example_DISP002") or {}).items():
            rows.append((f"{prof}（逐案读取；此处为 DISP-002 示例）", k, v.get("value"), v.get("unit", ""), v.get("source_type", ""), v.get("source", ""),
                         v.get("source_date", ""), v.get("retrieved", ""), v.get("credibility", ""), "", "代码不读这里的值：每个案件从自己的政策对象读取，缺的按 META-01 用 Ryde 默认值"))
    for k, v in kb.shared.items():
        rows.append(("shared", k, v.get("value"), v.get("unit", ""), v.get("source_type", ""), v.get("source", ""), v.get("source_date", ""),
                     v.get("retrieved", ""), v.get("credibility", ""), v.get("plausible_range", ""), ("只加标记; " if v.get("flag_only") else "") + str(_s(v.get("note", "")))))
    r = table(ws, r, ["参数档", "参数", "值", "单位", "来源类型", "来源", "文件日期", "读取日期", "可信度", "合理区间", "备注"], rows,
              widths=[18, 28, 16, 7, 13, 60, 11, 11, 7, 12, 60])
    r = heading(ws, r, "参考表")
    trows = [(name, t.get("source", ""), t.get("source_date", ""), t.get("retrieved", ""), t.get("credibility", ""),
              t.get("rows") or t.get("value") or "", t.get("note", t.get("status", ""))) for name, t in kb.tables.items()]
    table(ws, r, ["表", "来源", "文件日期", "读取日期", "可信度", "内容", "备注"], trows)
    finish(ws, freeze=None)


def s_playbooks(wb, kb):
    ws = wb.create_sheet("12_操作指引")
    meta = kb.y["playbooks"]["meta"]
    r = title(ws, "操作指引（ONT.10b）：把怎么做写成数据；每步汇报 done / missing / not_applicable，done 必须引用实际读到的证据")
    r = table(ws, r, ["回答模式", "含义"], [(k, v) for k, v in meta["answer_modes"].items()], widths=[18, 100])
    r = table(ws, r, ["步骤原语", "含义"], [(k, v) for k, v in meta["step_primitives"].items()])
    rows, fills = [], {}
    for pb in kb.y["playbooks"]["playbooks"]:
        rows.append((pb["id"], pb.get("display_name_zh", ""), pb.get("when"), pb.get("answer_mode"), pb.get("status"), "", "",
                     "来源: " + str(_s(pb.get("sources"))),
                     "所需证据: " + str(_s(pb.get("required_evidence"))) + ("；可选: " + str(_s(pb.get("optional_evidence"))) if pb.get("optional_evidence") else "")))
        fills[len(rows)] = FILL_CAT
        for st in pb["steps"]:
            rows.append(("", "", "", "", "", st["n"], st["do"], st.get("rule", st.get("table", "")), st.get("note", "")))
    table(ws, r, ["指引", "中文名", "触发条件", "回答模式", "状态", "步", "原语", "规则 / 表", "说明"], rows, widths=[18, 26, 26, 15, 7, 5, 12, 34, 80], fills=fills)
    finish(ws, freeze=None)


def s_auth(wb, kb):
    ws = wb.create_sheet("13_审批权限")
    r = title(ws, "审批权限矩阵（自治等级 AUTO / APPROVE / HUMAN、人工批准条件、升级门）",
              "Ryde 的审批权限表没有公开，这一页全部是 FairRyde 的设计（可信度 B 到 D），需要组织方或 Ryde 确认")
    tau = kb.pval("TAU", "organizer_case")
    lim = kb.pval("AUTO_LIMIT_SGD", "organizer_case")
    tiers = [("AUTO 自动执行", f"AUTH-01 全部满足：没有决定性的需读原文规则、C/D 级参数或 C/D 级决策表行；金额不超过 S${lim:.0f}；置信度不低于 τ={tau}；不触发人工批准条件和升级门；不是申诉",
              "抽检；双方都可申请人工复核"),
             ("APPROVE 人工批准", "FairRyde 已给出裁决，且 AUTH-02 任一触发或 AUTH-04 中等级为 APPROVE 的升级门（G1、G3、G5、G6、G7）触发；或类型范围是 ADJUDICATE_WITH_APPROVAL（改目的地费、未接到乘客、清洁费）",
              "AI 给出暂定裁决和一页摘要，人确认、修改或驳回，写入 HumanReview 日志；10% 独立审计（复核人先自己判，再看 AI 建议）；确认率异常偏高时审计"),
             ("HUMAN 人工裁决", "AUTH-03：安全、可能涉刑、任何账户处罚；AUTH-04 中等级为 HUMAN 的升级门（G2、G4、G8）；AUTH-06：结果为 ESCALATE_HUMAN（事实有争议、乘客强反证、无成文规则），没有可批准的 AI 裁决", "AI 只分类、保全证据、写中立摘要和规则决定不了的那一点，不认定过错")]
    r = table(ws, r, ["等级", "条件", "执行方式"], tiers, cols=[1, 3, 4])
    rows = [(rid, kb.rules[rid]["name"], kb.rules[rid].get("zh", ""), kb.rules[rid]["statement"], kb.rules[rid]["credibility"])
            for rid in kb.rule_order if kb.rules[rid]["family"] == "AUTH"]
    r = heading(ws, r, "审批相关规则原文")
    r = table(ws, r, ["规则", "名称", "中文", "规则（英文）", "可信度"], rows, widths=[10, 30, 60, 80, 7])
    gates = [("G1", "A/B 级来源互相矛盾超出容差", "离线参考引擎检查"), ("G2", "规则冲突", "运行时"),
             ("G3", "看历史的 Judge 或欺诈检查与不看历史的结论不同：保留不看历史的裁决作为暂定裁决（APPROVE），把分歧展示给复核人，不改变结果", "运行时检测；处理方式见 AUTH-04 和离线检查"), ("G4", "出现安全内容", "离线参考引擎检查"),
             ("G5", "置信度低于 τ", "离线参考引擎检查（A、R 两项按 1.0 计）"), ("G6", "金额超过自动上限", "离线参考引擎检查"),
             ("G7", "引用或数字校验重试一次仍失败", "运行时（离线解释草稿已做数字核对 EXP-03）"), ("G8", "Judge 多次运行之间或与规则引擎不一致", "运行时")]
    r = heading(ws, r, "升级门（AUTH-04，任一触发即转人工并附暂定裁决）")
    gt = kb.rules["AUTH-04"].get("gate_tiers", {})
    gates = [(g, c, w, gt.get(g, "")) for g, c, w in gates]
    r = table(ws, r, ["门", "条件", "在哪里检查", "等级（AUTH-04 gate_tiers）"], gates)
    r = heading(ws, r, "FairRyde 永远不做的事")
    table(ws, r, ["#", "内容"], [(i + 1, x) for i, x in enumerate(kb.y["scope"]["decision_goal"]["never_decided_by_fairryde"])])
    finish(ws, freeze=None)


def s_sources(wb, kb, rep):
    ws = wb.create_sheet("14_来源登记")
    r = title(ws, "来源登记：每条规则引用的文件", "Ryde 帮助中心文章按 Ryde 用户条款第 1、2 条属于 Ryde Policies，是合同的一部分；编辑日期在 2025-10-05 及以后、且引用的条款不处在已知矛盾一方的，可评 A")
    cited = {}
    for q in rep.quotes:
        cited.setdefault(q["doc"], set()).add(q["rule"])
    for pb in kb.y["playbooks"]["playbooks"]:
        for s in pb.get("sources", []):
            cited.setdefault(s, set())
    rows = []
    for d in kb.y["sources"]["documents"]:
        rows.append((d["id"], d["title"], d.get("publisher", ""), d["type"], d.get("date", ""), d.get("credibility_default", ""), d.get("url", ""),
                     d.get("verify_against", "") or "无（转述或仅作参考）", sorted(cited.get(d["id"], [])), d.get("note", "")))
    for doc in sorted(k for k in cited if k.startswith("RYDE-") and k != "RYDE-TOU"):
        d = kb.sources[doc]
        rows.append((doc, d["title"], "Ryde Technologies Pte Ltd", "RYDE_POLICY", d["date"], d["credibility_default"], d["url"], "sources/ryde_policy_corpus.json",
                     sorted(cited.get(doc, [])), f"{d['audience']}；{d.get('section') or ''}"))
    table(ws, r, ["文件", "标题", "发布方", "类型", "日期（文章为编辑日期）", "默认可信度", "链接", "核对用的本地副本", "引用它的规则", "备注"], rows,
          widths=[22, 50, 20, 14, 14, 9, 50, 30, 30, 40])
    finish(ws, freeze=f"B{r+1}", filter_ref=f"A{r}:J{r+len(rows)}")


def s_disp002(wb, kb, runs):
    ws = wb.create_sheet("15_DISP-002三层视图")
    run = runs["organizer_case"]
    t, tier, sens = run["trace"], run["tier"], run["sensitivity"]
    d = kb.disp002
    r = title(ws, "同一份单据在三层里的样子：DISP-002（ONT.2）", "参数档 organizer_case（逐案读取案件自带的政策对象，META-01）；参考引擎没有调用 LLM，置信度的 A、R 两项按 1.0 计")
    r = heading(ws, r, "第一层 Taxonomy：它属于哪一类")
    tax = [
        ("争议类型", "TX-CASE", d["dispute_ticket"]["dispute_type"], f"{t.claim_type}（类别 CW Cancellation and Waiting Fee）"),
        ("申诉方", "TX-ROLE", d["dispute_ticket"]["filed_by"], "RIDER，在工单里是 CLAIMANT"),
        ("被争议的收费", "TX-CHARGE", f"cancellation_fee {d['trip_data']['cancellation_fee']}", "CANCELLATION_FEE"),
        ("诉求", "TX-REMEDY-REQUESTED", "I want the charge reversed immediately.", "FEE_WAIVER"),
        ("支付方式", "TX-PAYMETHOD", d["rider_profile"]["payment_method"], "E_WALLET"),
        ("下单类型", "TX-BOOKING", "未记录", f"UNKNOWN，推断 {t.findings['F-BOOKING-TYPE']['value']}（标记 BOOKING_TYPE_INFERRED）"),
        ("服务类型", "TX-SERVICE", "未记录", "UNKNOWN（按 CW-R00 视为在政策范围内）"),
        ("取消原因", "TX-CANCELREASON", d["trip_data"]["cancellation_reason"], "rider_no_show"),
        ("事件类型", "TX-EVENT", sorted({a["event_type"] for a in d["app_events"]}), "全部在受控词表里"),
        ("GPS 状态", "TX-GPSSTATUS", sorted({g["status"] for g in d["gps_telemetry"]}), "全部在受控词表里"),
        ("沟通类型", "TX-COMMTYPE", sorted({c["type"] for c in d["chat_logs"]}), "全部在受控词表里"),
        ("严重度", "TX-SEVERITY", "S$5.00，无安全内容", "S3 低额款项"),
        ("工单关联", "TX-RELATION", "同一行程没有其他工单", t.relation),
        ("裁决结果", "TX-OUTCOME", "", t.outcome),
        ("理由代码", "TX-REASON", "", t.reasons),
        ("标记", "TX-FLAG", "", t.flags),
        ("自治等级", "TX-TIER-AUTONOMY", "", tier["tier"]),
    ]
    r = table(ws, r, ["维度", "词表", "DISP-002 原值", "代码"], tax)
    r = heading(ws, r, "第二层 Ontology：有哪些实体、各自扮演什么角色、发生了什么")
    pv = t.findings["F-PIN-VENUE"]["value"]
    venue = next((v for v in kb.tables["VENUES"]["rows"] if v["name"] == d["trip_data"]["pickup_location"]["name"]), None)
    ont = [
        ("Account", "R-7823", "RIDER（行程）；CLAIMANT（工单）；PAYER（取消费）", "姓名替换为 RIDER-NAME-1；历史 4 次申诉、3 次驳回；欺诈标记 1"),
        ("Account", "D-2398", "DRIVER；RESPONDENT；PAYEE", "姓名替换为 DRIVER-NAME-1；3,201 次行程；评分 4.9"),
        ("Vehicle", "Honda HR-V", "由 D-2398 驾驶", "车牌是敏感信息，替换为 PLATE-1"),
        ("Platform (Ryde)", "Ryde", "PLATFORM_LINKER；PLATFORM_COLLECTION_AGENT；PLATFORM_REFUND_DECIDER", "聊天里的 system 发送方；所有 app 事件的记录方"),
        ("Trip", d["trip_data"]["trip_id"], "", "状态：REQUESTED 08:30:00 → MATCHED 08:30:15 → EN_ROUTE 08:30:20 → ARRIVED 08:43:00 → WAITING_FREE 08:43:10 → WAITING_CHARGEABLE 08:48:10 → CANCELLED_NO_SHOW 08:51:00"),
        ("Place（上车点）", d["trip_data"]["pickup_location"]["name"], "", f"pin ({d['trip_data']['pickup_location']['lat']}, {d['trip_data']['pickup_location']['lng']})；"
         + (f"OneMap 地址 ({venue['lat']:.5f}, {venue['lng']:.5f})；相距 {pv:,} m" if venue else "")),
        ("Place（下车点）", d["trip_data"]["dropoff_location"]["name"], "", f"pin ({d['trip_data']['dropoff_location']['lat']}, {d['trip_data']['dropoff_location']['lng']})"),
        ("TripEvent", f"{len(d['app_events'])} 个", "", f"E-APP-01 到 E-APP-{len(d['app_events']):02d}"),
        ("GPSPing", f"{len(d['gps_telemetry'])} 个（只有司机端）", "", f"E-GPS-01 到 E-GPS-{len(d['gps_telemetry']):02d}；乘客端没有 GPS（数据缺口）"),
        ("Communication", f"{len(d['chat_logs'])} 条", "", "E-CHT-01 到 E-CHT-06；司机 4 条消息、1 通电话；乘客 0；系统 1"),
        ("Charge", "CANCELLATION_FEE S$5.00", "付款方 RIDER；收款方 DRIVER", "e-wallet；08:51:00 收取；状态 APPLIED → DISPUTED"),
        ("PolicyDocument / PolicyClause", "案件自带政策对象", "", "免费等待 5 分钟；no-show 阈值 8 分钟；S$5.00；归司机（E-POL-01）"),
        ("DisputeTicket", "DISP-002", "", "OPEN；09:20:00 由乘客提交（行程后 29 分钟）"),
        ("Claim", "C1（主项）", "", "CW-NOSHOW；争议 S$5.00 取消费；诉求 FEE_WAIVER"),
        ("EvidenceItem", f"{len(evidence_index(d, kb))} 个", "", "E-TKT-01、E-PRF-R、E-PRF-D、E-TRP-01、E-GPS-*、E-CHT-*、E-APP-*、E-POL-01；E-GEO-01 是 OneMap 参考查询，不算证据"),
        ("Finding", f"{len([k for k in t.findings if not k.startswith('_')])} 个", "", "见下面第三层每一步"),
        ("Ruling", t.outcome, "", f"理由 {', '.join(t.reasons)}；自治等级 {tier['tier']}；置信度 {t.confidence['C']}"),
    ]
    r = table(ws, r, ["实体", "实例", "角色", "关键属性"], ont)
    r = heading(ws, r, "第三层 Rules：按操作指引逐步推演（每步引用的证据编号）")
    cred = {rid: kb.rules[rid]["credibility"] for rid in kb.rules}
    mode = {rid: kb.rules[rid]["mode"] for rid in kb.rules}
    rows = []
    for s in t.steps:
        ids = [i for i in re.findall(r"\b[A-Z]{2,4}-[A-Z]?\d+[A-Z]?\b", s["rule"]) if i in kb.rules]
        rows.append((f"{s['playbook']} #{s['n']}", s["rule"],
                     (f"可信度 {'/'.join(cred[i] for i in ids)}；模式 {'/'.join(mode[i] for i in ids)}；" if ids else "") + s["status"],
                     s["result"], s["evidence"]))
    r = table(ws, r, ["指引与步骤", "规则", "可信度 · 模式 · 状态", "结果", "证据"], rows)
    r = heading(ws, r, "敏感性测试（决定性定义第 2 条：把路径上每个 C/D 级参数推到合理区间两端，看结果变不变，或是否落到 C、D 级的决策表行）")
    r = table(ws, r, ["参数", "当前值 · 区间 · 可信度", "低端", "高端", "用到它的路径规则", "决定性"],
              [(s["param"], f"{s['value']} · {s['range']} · {s['credibility']}", s["low"], s["high"], s["rules_using"],
                "是（结果改变）" if s["outcome_changes"] else ("是（落到低可信度的行）" if s["weaker_row"] else "否")) for s in sens])
    ws.column_dimensions["F"].width = max(ws.column_dimensions["F"].width or 0, 22)
    r = heading(ws, r, "读法测试（决定性定义第 1 条：需读原文的判断换一种读法，结果变不变）")
    r = table(ws, r, ["规则", "当前读法", "另一种读法", "另一种读法下的结果", "结果改变"],
              [(x["rule"], x["reading"], x["other_reading"], x["outcome_other"], x["changes"]) for x in run["readings"]] or [("无", "", "", "", "")])
    r = heading(ws, r, "置信度与自治等级")
    r = table(ws, r, ["项目", "值"], [("置信度分项", {k: v for k, v in t.confidence.items() if k in ("A", "M", "E", "R", "C")}),
                                     ("假设", t.confidence["assumed"]), ("必需证据是否齐全", t.confidence["evidence_present"]),
                                     ("软标记（每个扣 E 0.1）", t.confidence["soft_flags"] or "无"),
                                     ("决定性", [f"{a}: {b}" for a, b in tier["decisive"]] or "无"), ("人工批准条件", tier["triggers"] or "无"),
                                     ("升级门", tier["gates"] or "无"), ("只在运行时检查的门", tier["runtime_only_gates"]), ("自治等级", tier["tier"])], cols=[1, 4])
    ex = explain.noshow(kb, run)
    r = heading(ws, r, "给双方的解释草稿（EXP-01 到 EXP-03：每个数字都登记并核对；不用姓名）")
    r = table(ws, r, ["对象", "解释"], [("乘客", ex["rider"]), ("司机", ex["driver"]), ("登记的数字", ex["numbers_used"]),
                                     ("数字核对（EXP-03）", "全部数字都对得上" if not ex["exp03_unmatched"] else f"对不上：{ex['exp03_unmatched']}")], cols=[1, 4])
    r2 = runs["ryde_2026"]
    r = heading(ws, r, "换成 ryde_2026 参数档试算（仅演示参数是数据而不是代码；组织方案例实际用组织方参数档）")
    table(ws, r, ["项目", "值"], [("结果", f"{r2['trace'].outcome}（{r2['trace'].dt_row}）"),
                                 ("已等 / 阈值", f"{int(r2['trace'].findings['F-WAIT-ELAPSED']['value'])} s / {int(r2['trace'].params_used['NO_SHOW_THRESHOLD_S']['value'])} s（严格大于）"),
                                 ("收费核对", r2["trace"].findings["F-CHARGE-AMOUNT"]["value"]), ("标记", r2["trace"].flags),
                                 ("置信度", r2["trace"].confidence["C"]), ("自治等级", r2["tier"]["tier"]), ("人工批准条件", r2["tier"]["triggers"])], cols=[1, 4])
    for col, w in zip("ABCDEF", (24, 30, 34, 70, 40, 12)):
        ws.column_dimensions[col].width = w
    finish(ws, freeze=None)


def s_selftest(wb, kb, results):
    ws = wb.create_sheet("16_引擎自测")
    r = title(ws, "引擎自测：DISP-002 的单因素变体（检验规则卡与参考引擎是否一致）",
              "这些不是标准答案：期望值是按规则卡手工写的，用来测代码；正式标准答案必须由人标注（ONT.5、ONT.6）。V06 是干净基线，V11、V14、V16、V18、V19、V22、V23 在它上面只改一个因素")
    rows = [(x["id"], x["variant"], x["expected"], {k: v for k, v in x["got"].items() if v is not None}, x["flags"], x["decisive"], x["triggers"],
             x["gates"], "通过" if x["ok"] else "失败: " + "; ".join(x["problems"])) for x in results]
    fills = {i + 1: (FILL_OK if x["ok"] else FILL_BAD) for i, x in enumerate(results)}
    r = table(ws, r, ["变体", "改了什么", "期望", "实际", "标记", "决定性", "人工批准条件", "升级门", "结果"], rows,
              widths=[7, 40, 36, 44, 44, 18, 50, 16, 10], fills=fills)
    rows_hit = sorted({x["got"]["row"] for x in results if x["got"]["row"]}, key=lambda s: int(s[1:]))
    tiers = sorted({x["got"]["tier"] for x in results})
    para(ws, r, f"覆盖：决策表行 {', '.join(rows_hit)}；自治等级 {', '.join(tiers)}；另有改判（MAT-04 超期、META-02 生效日期、CW-R00 RydeTAXI）和重新分类（V10）。", 8, 30, F_NOTE)
    finish(ws, freeze=None)


def s_annotation_design(wb, kb, rep):
    ws = wb.create_sheet("17_标注方案")
    ann = kb.y["annotation_schema"]
    r = title(ws, "标注方案（ONT.5）与验证方案（ONT.6）", "标注本身在 FairRyde_Annotation_v0.1.xlsx；这一页只是设计说明，由脚本从 annotation_schema.yaml 生成")
    for col, w in zip("ABCDEFGH", (18, 28, 10, 30, 6, 8, 50, 40)):
        ws.column_dimensions[col].width = w
    for k, v in (("原则", ann["meta"]["principle"]), ("文件规则", ann["meta"]["file_policy"]), ("示例行", ann["meta"]["example_note"]),
                 ("盲标模式", ann["meta"]["blind_mode"]), ("协议要求的难例", ann["meta"]["protocol_hard_cases"]),
                 ("填写方式", "; ".join(f"{a} = {b}" for a, b in ann["fill_modes"].items()))):
        r = para(ws, r, f"{k}：{v}", 8)
    r = heading(ws, r + 1, "每一列")
    rows = []
    for g, grp in ann["groups"].items():
        for c in grp["columns"]:
            vocab = c.get("vocab") or ("取值: " + str(_s(c.get("values"))) if c.get("values") else "")
            rows.append((f"{g}（{grp.get('zh', g)}）", c["name"], c["fill"], vocab, "多值" if c.get("multi") else "", "隐藏" if c.get("hide_in_blind") else "",
                         c.get("note", c.get("formula", "")), c.get("example", "")))
    r = table(ws, r, ["列组", "列名", "填写方式", "词表 / 取值", "多值", "盲标", "说明", "示例（虚构案件 EXAMPLE-01）"], rows)
    vp = ann["validation_plan"]
    r = heading(ws, r, "验证方案（ONT.6）")
    r = table(ws, r, ["项目", "内容"], [("标准答案来源", vp["gold_sources"]), ("难例配额", vp["hard_case_quotas"]), ("覆盖检查", vp["coverage_checks"]),
                                     ("循环论证控制", vp["circularity_controls"]), ("复核监控", vp["review_monitoring"]), ("指标", vp["metrics"])])
    r = heading(ws, r, "实体覆盖（ONT.6：每个实体类型至少在一个案件文件里出现；脚本在案件文件上检查）")
    table(ws, r, ["实体", "名称", "类别", "出现于", "状态"], [(x["entity"], x["name"], x["kind"], x["covered_by"], x["status"]) for x in rep.tables["entity_coverage"]])
    finish(ws, freeze=None)


def s_open(wb, kb):
    ws = wb.create_sheet("18_待决问题")
    oi = kb.y["open_items"]
    r = title(ws, "待决问题", "D1 到 D16 沿用 10 月 4 日报告的编号；D17 起为本次新增；自治等级已改名 AUTO / APPROVE / HUMAN")
    rows = [(x["id"], x["topic"], x["default_v0_1"], _s(x.get("changed")), x.get("decide", "")) for x in oi["decisions"]]
    r = table(ws, r, ["编号", "事项", "v0.1 默认做法", "是否有变化", "谁来定"], rows, widths=[7, 34, 80, 40, 26])
    r = heading(ws, r, "给曹老师的问题")
    r = table(ws, r, ["#", "问题"], [(i + 1, q) for i, q in enumerate(oi["questions_for_cao"])])
    r = heading(ws, r, "给组织方的问题（可直接贴到赛道群）")
    table(ws, r, ["编号", "问题"], [(q["id"], q["q"]) for q in oi["questions_for_organizer"]])
    finish(ws, freeze=None)


def build_kb_workbook(kb, rep, runs, dt_enum, priv, tests, path, ann_status, out_scan=None):
    st = statsmod.compute(kb, rep, priv)
    wb = Workbook()
    s_readme(wb, kb, st, runs, rep, tests, ann_status, dt_enum, out_scan)
    s_gap(wb, kb, st)
    s_scope(wb, kb, runs)
    s_inventory(wb, kb)
    s_taxonomy(wb, kb)
    s_entities(wb, kb)
    s_roles(wb, kb)
    s_events(wb, kb, rep)
    s_mapping(wb, kb, rep)
    s_rules(wb, kb, rep)
    s_dt(wb, kb, rep)
    s_ref(wb, kb)
    s_playbooks(wb, kb)
    s_auth(wb, kb)
    s_sources(wb, kb, rep)
    s_disp002(wb, kb, runs)
    s_selftest(wb, kb, tests)
    s_annotation_design(wb, kb, rep)
    s_open(wb, kb)
    replaced = _pseudo_pass(wb, privacy_scan.dictionary(kb.disp002))
    _finalize(wb)
    wb.save(path)
    return {"path": str(path), "pseudonymized_cells": replaced}


# ============================================================================================== annotation workbook
def _ann_columns(kb):
    return [(g, grp.get("zh", g), c) for g, grp in kb.y["annotation_schema"]["groups"].items() for c in grp["columns"]]


def _lists_sheet(wb, kb):
    ws = wb.create_sheet("lists")
    lists = {}

    def put(name, values):
        col = len(lists) + 1
        ws.cell(row=1, column=col, value=name).font = F_BOLD
        for i, v in enumerate(values, 2):
            ws.cell(row=i, column=col, value=v)
        letter = get_column_letter(col)
        lists[name] = f"lists!${letter}$2:${letter}${len(values) + 1}"
    put("TX-CASE", list(kb.case_leaves))
    for vid in ("TX-OUTCOME", "TX-REASON", "TX-ROLE", "TX-REMEDY-FORM", "TX-RELATION", "TX-TIER-AUTONOMY", "TX-FLAG", "TX-SERVICE", "TX-BOOKING",
                "TX-PAYMETHOD", "TX-CANCELREASON", "TX-CHARGE"):
        put(vid, list(kb.vocab[vid]))
    put("rule ids", kb.rule_order)
    put("source ids", [d["id"] for d in kb.y["sources"]["documents"]] + sorted(q for q in kb.sources if q.startswith("RYDE-") and q != "RYDE-TOU"))
    for g, _, c in _ann_columns(kb):
        if c.get("values"):
            put(c["name"], [str(v) for v in c["values"]])
    ws.sheet_state = "hidden"
    return lists


def _auto_inputs(kb, case):
    """Mechanical extraction of the INPUT columns from a pseudonymized organizer-format case (fill mode AUTO)."""
    t, tk = case["trip_data"], case["dispute_ticket"]
    ev = {a["event_type"]: a for a in case["app_events"]}
    T = lambda s: datetime.fromisoformat(s).replace(tzinfo=None) if s else None
    pol = case.get("cancellation_policy") or {}
    end = datetime.fromisoformat(t["cancellation_time"])
    arr = datetime.fromisoformat(t["driver_arrival_time"]) if t.get("driver_arrival_time") else None
    if pol and t.get("driver_wait_start"):                      # same anchor rule as the wait_elapsed_s formula (CW-F02, CW-F02B)
        start = datetime.fromisoformat(t["driver_wait_start"])
    elif (t.get("booking_type") or "").upper() == "ADVANCE" and t.get("scheduled_time"):
        start = max(x for x in (arr, datetime.fromisoformat(t["scheduled_time"])) if x)
    else:
        start = arr or end
    assigned_at = min([datetime.fromisoformat(a["timestamp"]) for a in case["app_events"] if a["event_type"] == "driver_assigned"]
                      or [datetime.fromisoformat(a["timestamp"]) for a in case["app_events"] if a["event_type"] == "booking_confirmed"] or [start])
    from_assignment = lambda ts: assigned_at <= datetime.fromisoformat(ts) <= end      # CW-F06 with D30: placements before arrival count
    thr = pol["no_show_threshold_min"] * 60 if "no_show_threshold_min" in pol else kb.pval("NO_SHOW_THRESHOLD_S", "ryde_2026")
    fee = pol.get("cancellation_fee_after_wait", kb.pval("NO_SHOW_FEE_SGD", "ryde_2026"))
    return {
        "case_id": tk["dispute_id"], "case_source": "ORGANIZER", "split": "ORGANIZER_PUBLIC", "seed_family": f"SEED-{tk['dispute_id']}",
        "policy_profile": "organizer_case" if pol else "ryde_2026",
        "filed_by": kb.resolve("TX-ROLE", tk["filed_by"]), "dispute_type_raw": tk["dispute_type"], "description": tk["description"],
        "service_type": kb.resolve("TX-SERVICE", t.get("service_type")) or "UNKNOWN",
        "booking_type_recorded": kb.resolve("TX-BOOKING", t.get("booking_type")) or "UNKNOWN",
        "payment_method": kb.resolve("TX-PAYMETHOD", case["rider_profile"].get("payment_method")),
        "booked_at": T(ev.get("booking_confirmed", {}).get("timestamp")), "matched_at": T(ev.get("driver_assigned", {}).get("timestamp")),
        "scheduled_time": T(t.get("scheduled_time")), "driver_arrival_time": T(t.get("driver_arrival_time")),
        "driver_wait_start": T(t.get("driver_wait_start")), "cancellation_time": T(t.get("cancellation_time")), "filed_at": T(tk.get("filed_at")),
        "cancellation_reason": t.get("cancellation_reason"), "contested_charge_type": "CANCELLATION_FEE", "contested_amount_sgd": t.get("cancellation_fee"),
        "pickup_name": t["pickup_location"]["name"],
        "driver_calls": sum(1 for c in case["chat_logs"] if c["sender"] == "driver" and c["type"] == "call"),
        "driver_messages": sum(1 for c in case["chat_logs"] if c["sender"] == "driver" and c["type"] == "message"),
        "rider_contacts": sum(1 for c in case["chat_logs"] if c["sender"] == "rider" and from_assignment(c["timestamp"])),
        "wait_pings": sum(1 for g in case["gps_telemetry"] if start <= datetime.fromisoformat(g["timestamp"]) <= end),
        "policy_threshold_s": thr, "policy_fee_sgd": fee,
        "rider_side_evidence": ("system_records" if (any(from_assignment(g["timestamp"]) for g in (case.get("rider_gps_telemetry") or []))
                                                     or any(c["sender"] == "rider" and from_assignment(c["timestamp"]) for c in case["chat_logs"])
                                                     or any(re.search(r"fail|not delivered|undelivered", a["details"], re.I) for a in case["app_events"] if a["event_type"] == "rider_notified"))
                                else ("statement_only" if tk.get("description") else "none")),
        "seed_case_id": tk["dispute_id"], "varied_factor": "none (seed)", "guideline_version": "G-0.1", "rulebook_version": "KB-0.1.0",
        "labeling_mode": "STANDARD",      # organizer cases are public to the team, so they cannot be labeled blind
    }


def a_instructions(wb, kb):
    ws = wb.active
    ws.title = "说明"
    ann = kb.y["annotation_schema"]
    cols = _ann_columns(kb)
    blind = [c["name"] for _, _, c in cols if c.get("hide_in_blind")]
    r = title(ws, "FairRyde 标注工作簿 v0.1（给标注人看，ONT.5：说明写进表里）", ann["meta"]["principle"])
    rules_ = [
        ("铁律 1", "标准答案（ANSWER、BASIS 两组列）只能由人填写，不能抄 FairRyde 或任何模型的输出。"),
        ("铁律 2", f"INDEPENDENT_BLIND 模式下先折叠（隐藏）INPUT 组最后 {len(blind)} 列：{', '.join(blind)}。它们是 AI 草稿或提前算好的决策表输入，会锚定判断。点表头上方的减号即可折叠。"),
        ("铁律 3", "进评测的案件不能拿去当 few-shot 示例，也不能放进判例库（ONT.10.3）。"),
        ("铁律 4", "脚本不会覆盖已经填过人工列的本文件；改表结构请先备份，再让脚本生成新文件后按内容（不是行号）迁移。"),
        ("怎么填", "能用下拉就用下拉；下拉里没有的值可以自己输入（会弹警告，确认即可），但优先用 OTHER 加自填列。"),
        ("多值", "一格多个值用英文分号加空格分隔，例如 BOUNDARY_MARGIN; PIN_VENUE_MISMATCH。"),
        ("主项 / 次项 / 其他", "primary 列只填一个最主要的；secondary 列填其余的；都放不下就写进 other 自填列。"),
        ("不确定时", "仍按你认为最可能的结果填写，annotator_confidence 填 1，在 rationale 写清楚卡在哪里；这类案件交曹老师仲裁。只有规则确实决定不了时（事实有争议、乘客强反证、无成文规则），结果才填 ESCALATE_HUMAN。"),
        ("自治等级", "AUTO 自动执行；APPROVE 有裁决、需人确认或修改；HUMAN 安全类，或结果为 ESCALATE_HUMAN（没有可批准的裁决，AUTH-06）。结果填 ESCALATE_HUMAN 时自治等级必须填 HUMAN；escalate 列在 APPROVE 或 HUMAN 时填 Y，AUTO 时填 N。"),
        ("颜色", "黄色 = 人填；灰色 = 自动抄录或公式，不要改；浅蓝 = AI 可起草的辅助列；绿色第 5 行 = 示例（虚构案件，只示范格式，不计入统计）。"),
        ("难例类型", "MISSING_INFO 关键信息缺失；NEGATIVE 无需处理的负样本；VAGUE 措辞含糊；STATE_UPDATE 需要状态更新（协议要求的四类），另有 BOUNDARY 边界值、CONFLICT 冲突、BAD_FAITH 恶意、ADVERSARIAL 注入攻击、CLEAR 清晰案例。"),
        ("证据编号", "E-TKT-01 工单；E-PRF-R / E-PRF-D 乘客 / 司机档案；E-TRP-01(.字段) 行程记录；E-GPS-nn 司机定位；E-RGPS-nn 乘客定位；E-CHT-nn 聊天与通话；E-APP-nn app 事件；E-POL-01 案件自带政策；E-GEO-nn OneMap 查询（参考，不算证据）。"),
        ("示例来源", ann["meta"]["example_note"]),
        ("脱敏", "案件文字里的姓名、车牌已换成代码（RIDER-NAME-1、DRIVER-NAME-1、PLATE-1）；对照表只放在负责人本机（kb/private/），不进仓库。"),
    ]
    for col, w in zip("ABCDEFGH", (18, 28, 10, 30, 6, 8, 50, 40)):
        ws.column_dimensions[col].width = w
    for k, v in rules_:
        r = para(ws, r, f"{k}：{v}", 8)
    r = heading(ws, r + 1, "每一列的说明")
    rows = []
    for g, gz, c in cols:
        vocab = c.get("vocab") or ("取值: " + str(_s(c.get("values"))) if c.get("values") else "")
        rows.append((f"{g}（{gz}）", c["name"], c["fill"], vocab, "多值" if c.get("multi") else "", "隐藏" if c.get("hide_in_blind") else "",
                     c.get("note", c.get("formula", "")), c.get("example", "")))
    r = table(ws, r, ["列组", "列名", "填写方式", "词表 / 取值", "多值", "盲标", "说明", "示例（虚构案件 EXAMPLE-01）"], rows)
    vp = ann["validation_plan"]
    r = heading(ws, r, "验证方案摘要（ONT.6，全文见知识库工作簿 17_标注方案）")
    r = table(ws, r, ["项目", "内容"], [("标准答案来源", vp["gold_sources"]), ("难例配额", vp["hard_case_quotas"]), ("循环论证控制", vp["circularity_controls"])], cols=[1, 7])
    finish(ws, freeze=None)


def a_table(wb, kb, lists, cases):
    cols = _ann_columns(kb)
    ws = wb.create_sheet(ANN_SHEET)
    ncol = len(cols)
    blind = [j for j, (_, _, c) in enumerate(cols, 1) if c.get("hide_in_blind")]
    ws.cell(row=1, column=1, value="图例：黄色 = 人填；灰色 = 自动或公式（不要改）；浅蓝 = AI 辅助；绿色第 5 行 = 示例（虚构案件，不计入统计）。数据从第 6 行开始；多值用 '; ' 分隔。"
            f"盲标时折叠 INPUT 组最后 {len(blind)} 列。").font = F_BOLD
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(ncol, 20))
    groups = []
    for j, (g, gz, c) in enumerate(cols, 1):
        if not groups or groups[-1][0] != g:
            groups.append([g, gz, j, j])
        else:
            groups[-1][3] = j
    for g, gz, a, b in groups:
        c = ws.cell(row=2, column=a, value=f"{g} {gz}")
        c.font, c.alignment = F_HEAD, CENTER
        for j in range(a, b + 1):
            ws.cell(row=2, column=j).fill = PatternFill("solid", fgColor=GROUP_FILLS[g])
        if b > a:
            ws.merge_cells(start_row=2, start_column=a, end_row=2, end_column=b)
    colidx = {}
    for j, (g, gz, c) in enumerate(cols, 1):
        colidx[c["name"]] = j
        h = ws.cell(row=3, column=j, value=c["name"])
        h.font, h.fill, h.alignment, h.border = F_HEAD, FILL_HEAD, CENTER, BORDER
        tip = c.get("note") or c.get("formula") or ""
        if c.get("vocab"):
            tip = (tip + " | " if tip else "") + f"词表 {c['vocab']}"
        if tip:
            h.comment = Comment(str(tip)[:300], "FairRyde")
        m = ws.cell(row=4, column=j, value=c["fill"] + (" · 盲标隐藏" if c.get("hide_in_blind") else ""))
        m.font, m.alignment, m.border = F_NOTE, CENTER, BORDER
        ws.column_dimensions[get_column_letter(j)].width = 34 if c["name"] in ("description", "rationale", "chat_summary") else (22 if c.get("multi") else 16)
    if blind:
        ws.column_dimensions.group(get_column_letter(blind[0]), get_column_letter(blind[-1]), hidden=False, outline_level=1)
    L = {k: get_column_letter(v) for k, v in colidx.items()}

    def formula(name, row):
        if name == "wait_elapsed_s":
            ws_, arr, sch, end = (f"{L[k]}{row}" for k in ("driver_wait_start", "driver_arrival_time", "scheduled_time", "cancellation_time"))
            prof, book = f"{L['policy_profile']}{row}", f"{L['booking_type_recorded']}{row}"
            return (f'=IF(NOT(ISNUMBER({end})),"",IF({prof}="organizer_case",IF(ISNUMBER({ws_}),ROUND(({end}-{ws_})*86400,0),""),'
                    f'IF({book}="ADVANCE",IF(ISNUMBER({arr}),ROUND(({end}-MAX({arr},{sch}))*86400,0),""),'
                    f'IF(ISNUMBER({arr}),ROUND(({end}-{arr})*86400,0),""))))')
        if name == "wait_margin_s":
            e, t = L["wait_elapsed_s"], L["policy_threshold_s"]
            return f'=IF(AND(ISNUMBER({e}{row}),ISNUMBER({t}{row})),{e}{row}-{t}{row},"")'
        if name == "filing_delay_days":
            a, b = L["cancellation_time"], L["filed_at"]
            return f'=IF(AND(ISNUMBER({a}{row}),ISNUMBER({b}{row})),ROUND({b}{row}-{a}{row},2),"")'
        return None

    def conv(name, v):
        if name in DT_COLS and isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", v):
            return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return v
    for j, (g, gz, c) in enumerate(cols, 1):           # example row (made-up case EXAMPLE-01)
        cell = ws.cell(row=5, column=j)
        f = formula(c["name"], 5)
        cell.value = f if f else conv(c["name"], c.get("example", ""))
        cell.fill, cell.font, cell.border, cell.alignment = FILL_EXAMPLE, Font(name=FONT, size=10, italic=True), BORDER, WRAP
        if c["name"] in DT_COLS:
            cell.number_format = "yyyy-mm-dd hh:mm:ss"
    autos = [_auto_inputs(kb, case) for case in cases]
    fills = {"HUMAN": FILL_HUMAN, "AUTO": FILL_AUTO, "FORMULA": FILL_AUTO, "AI_OK": FILL_AI}
    for row in range(DATA_FIRST, DATA_LAST + 1):
        auto = autos[row - DATA_FIRST] if row - DATA_FIRST < len(autos) else {}
        for j, (g, gz, c) in enumerate(cols, 1):
            cell = ws.cell(row=row, column=j)
            f = formula(c["name"], row)
            if f:
                cell.value = f
            elif c["fill"] == "AUTO" and c["name"] in auto:
                cell.value = auto[c["name"]]
            cell.fill, cell.font, cell.border = fills[c["fill"]], F_BASE, BORDER
            if c["name"] in DT_COLS:
                cell.number_format = "yyyy-mm-dd hh:mm:ss"
            if c["name"] in ("description", "rationale", "chat_summary"):
                cell.alignment = WRAP

    def dv_for(src):
        dv = DataValidation(type="list", formula1=f"={src}", allow_blank=True, showErrorMessage=True, errorStyle="warning",
                            errorTitle="不在列表里", error="这个值不在下拉列表里。确认要自填吗？（多值请用 '; ' 分隔）")
        ws.add_data_validation(dv)
        return dv
    for j, (g, gz, c) in enumerate(cols, 1):
        vocab = str(c.get("vocab", ""))
        src = None
        if c.get("values"):
            src = lists.get(c["name"])
        elif vocab.startswith("TX-CASE"):
            src = lists["TX-CASE"]
        elif vocab.startswith("TX-") and vocab.split()[0] in lists:
            src = lists[vocab.split()[0]]
        elif vocab in ("rule ids", "source ids"):
            src = lists[vocab]
        if src and c["fill"] != "FORMULA":
            dv_for(src).add(f"{get_column_letter(j)}5:{get_column_letter(j)}{DATA_LAST}")
    ws.freeze_panes = ws.cell(row=5, column=2)
    ws.auto_filter.ref = f"A4:{get_column_letter(ncol)}{DATA_LAST}"
    return L


def a_coverage(wb, kb, L):
    ws = wb.create_sheet("覆盖检查")
    rng = lambda name: f"'{ANN_SHEET}'!${L[name]}${DATA_FIRST}:${L[name]}${DATA_LAST}"

    def head(r, hs):
        for j, h in enumerate(hs, 1):
            c = ws.cell(row=r, column=j, value=h)
            c.font, c.fill, c.alignment = F_HEAD, FILL_HEAD, CENTER
    r = title(ws, "覆盖检查（ONT.6：每条规则至少一个样本触发，结果类规则至少一次起决定作用；每个类型、决策表行、标记都要有样本）",
              f"全部是公式，统计 {ANN_SHEET} 第 {DATA_FIRST} 到 {DATA_LAST} 行（不含示例行）；标注越多数字越完整")
    r = heading(ws, r, "总体")
    ws.cell(row=r, column=1, value="已标注案件数（outcome 非空）")
    ws.cell(row=r, column=2, value=f"=COUNTA({rng('outcome')})")
    ws.cell(row=r + 1, column=1, value="已录入案件数（case_id 非空）")
    ws.cell(row=r + 1, column=2, value=f"=COUNTA({rng('case_id')})")
    r += 3
    r = heading(ws, r, "难例配额")
    quotas = kb.y["annotation_schema"]["validation_plan"]["hard_case_quotas"]
    head(r, ["难例类型", "最少", "已有", "状态", "说明"])
    for i, (k, v) in enumerate(quotas.items(), 1):
        row = r + i
        ws.cell(row=row, column=1, value=k)
        ws.cell(row=row, column=2, value=int(re.search(r"\d+", str(v)).group()))
        ws.cell(row=row, column=3, value=f'=COUNTIF({rng("difficulty")},A{row})')
        ws.cell(row=row, column=4, value=f'=IF(C{row}>=B{row},"够","差 "&(B{row}-C{row}))')
        ws.cell(row=row, column=5, value=str(v))
    r = r + len(quotas) + 2
    r = heading(ws, r, "每个争议类型（主项）")
    head(r, ["类型", "范围", "主项案件数", "要求", "状态"])
    for i, (code, x) in enumerate(kb.case_leaves.items(), 1):
        row = r + i
        ws.cell(row=row, column=1, value=code)
        ws.cell(row=row, column=2, value=x.get("scope"))
        ws.cell(row=row, column=3, value=f'=COUNTIF({rng("primary_type")},A{row})')
        ws.cell(row=row, column=4, value=2 if x.get("scope") in ("ADJUDICATE", "ADJUDICATE_WITH_APPROVAL") else 1)
        ws.cell(row=row, column=5, value=f'=IF(C{row}>=D{row},"够","差 "&(D{row}-C{row}))')
    r = r + len(kb.case_leaves) + 2
    r = heading(ws, r, "每条规则（决定性 = decisive_rule_primary；被引用 = 决定性或 supporting_rules 里出现）")
    head(r, ["规则", "类型", "决定性次数", "被引用次数", "要求", "状态"])
    for i, rid in enumerate(kb.rule_order, 1):
        row = r + i
        outcome_rule = kb.rules[rid]["type"] == "outcome"
        ws.cell(row=row, column=1, value=rid)
        ws.cell(row=row, column=2, value=kb.rules[rid]["type"])
        ws.cell(row=row, column=3, value=f'=COUNTIF({rng("decisive_rule_primary")},A{row})')
        ws.cell(row=row, column=4, value=f'=C{row}+SUMPRODUCT(--ISNUMBER(SEARCH("; "&A{row}&"; ","; "&{rng("supporting_rules")}&"; ")))')
        ws.cell(row=row, column=5, value="决定性至少 1 次" if outcome_rule else "被引用至少 1 次")
        ws.cell(row=row, column=6, value=(f'=IF(C{row}>=1,"够","缺")' if outcome_rule else f'=IF(D{row}>=1,"够","缺")'))
    r = r + len(kb.rule_order) + 2
    dt_rows = kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"]
    r = heading(ws, r, "决策表 DT-CW-NOSHOW 每一行")
    head(r, ["行", "案件数", "状态"])
    for i, row_ in enumerate(dt_rows, 1):
        row = r + i
        ws.cell(row=row, column=1, value=row_["row"])
        ws.cell(row=row, column=2, value=f'=COUNTIF({rng("decision_table_row")},A{row})')
        ws.cell(row=row, column=3, value=f'=IF(B{row}>=1,"够","缺")')
    r = r + len(dt_rows) + 2
    r = heading(ws, r, "每个标记（required_flags 里出现）")
    head(r, ["标记", "案件数", "状态"])
    for i, f in enumerate(kb.vocab["TX-FLAG"], 1):
        row = r + i
        ws.cell(row=row, column=1, value=f)
        ws.cell(row=row, column=2, value=f'=SUMPRODUCT(--ISNUMBER(SEARCH("; "&A{row}&"; ","; "&{rng("required_flags")}&"; ")))')
        ws.cell(row=row, column=3, value=f'=IF(A{row}="OTHER","不要求",IF(B{row}>=1,"够","缺"))')
    r = r + len(kb.vocab["TX-FLAG"]) + 2
    r = heading(ws, r, "每个结果")
    head(r, ["结果", "案件数"])
    for i, o in enumerate(kb.vocab["TX-OUTCOME"], 1):
        row = r + i
        ws.cell(row=row, column=1, value=o)
        ws.cell(row=row, column=2, value=f'=COUNTIF({rng("outcome")},A{row})')
    r = r + len(kb.vocab["TX-OUTCOME"]) + 2
    r = heading(ws, r, "每个自治等级")
    head(r, ["等级", "案件数"])
    for i, o in enumerate(kb.vocab["TX-TIER-AUTONOMY"], 1):
        row = r + i
        ws.cell(row=row, column=1, value=o)
        ws.cell(row=row, column=2, value=f'=COUNTIF({rng("autonomy_tier")},A{row})')
    r = r + len(kb.vocab["TX-TIER-AUTONOMY"]) + 2
    r = heading(ws, r, "一致性（目标都是 0）")
    head(r, ["检查", "行数", "状态"])
    o, tr_, es = rng("outcome"), rng("autonomy_tier"), rng("escalate")
    checks_ = [("结果是 ESCALATE_HUMAN 但自治等级不是 HUMAN（AUTH-06）", f'=SUMPRODUCT(({o}="ESCALATE_HUMAN")*({tr_}<>"HUMAN"))'),
               ("escalate 为 Y 但自治等级是 AUTO", f'=SUMPRODUCT(({es}="Y")*({tr_}="AUTO"))'),
               ("escalate 为 N 但自治等级是 APPROVE 或 HUMAN", f'=SUMPRODUCT(({es}="N")*(({tr_}="APPROVE")+({tr_}="HUMAN")))')]
    for i, (label, f) in enumerate(checks_, 1):
        row = r + i
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=f)
        ws.cell(row=row, column=3, value=f'=IF(B{row}=0,"好","需修正")')
    r = r + len(checks_) + 2
    para(ws, r, "每个实体类型至少出现一次（ONT.6）由脚本在案件文件上检查，结果见 FairRyde_KB_v0.1.xlsx 的 17_标注方案。", 6, 30, F_NOTE)
    for col, w in zip("ABCDEF", (34, 26, 16, 16, 22, 12)):
        ws.column_dimensions[col].width = w
    finish(ws, freeze=None)


def annotation_state(kb, path: Path) -> dict:
    """Count filled HUMAN cells by column header (content, not position) and compare headers with the schema."""
    locks = [path.parent / f"~${path.name}", path.parent / f".~lock.{path.name}#"]
    if any(x.exists() for x in locks):
        return {"exists": path.exists(), "locked": True, "human_cells": None, "missing": [], "extra": []}
    if not path.exists():
        return {"exists": False, "locked": False, "human_cells": 0, "missing": [], "extra": []}
    wb = load_workbook(path)
    if ANN_SHEET not in wb.sheetnames:
        return {"exists": True, "locked": False, "human_cells": None, "missing": [], "extra": [], "error": f"no sheet {ANN_SHEET}"}
    ws = wb[ANN_SHEET]
    hdr = {ws.cell(row=3, column=j).value: j for j in range(1, ws.max_column + 1) if ws.cell(row=3, column=j).value}
    schema = [c["name"] for _, _, c in _ann_columns(kb)]
    human = [c["name"] for _, _, c in _ann_columns(kb) if c["fill"] == "HUMAN"]
    n = 0
    for name in human:
        j = hdr.get(name)
        if j:
            n += sum(1 for r in range(DATA_FIRST, ws.max_row + 1) if ws.cell(row=r, column=j).value not in (None, ""))
    return {"exists": True, "locked": False, "human_cells": n, "missing": [c for c in schema if c not in hdr], "extra": [c for c in hdr if c not in schema]}


def build_annotation(kb, path: Path, cases: list[dict]) -> dict:
    """Create the annotation workbook unless people have started labeling it (ONT.11.3)."""
    path = Path(path)
    st = annotation_state(kb, path)
    if st.get("locked"):
        return {**st, "written": False, "message": f"{path.name} 正在 Excel 或 LibreOffice 里打开，没有写入（ONT.11.3）"}
    if st.get("human_cells"):
        diff = (f"；表结构与当前 schema 不同（缺 {st['missing']}，多 {st['extra']}），需要按内容迁移" if st["missing"] or st["extra"] else "")
        return {**st, "written": False, "message": f"{path.name} 已有 {st['human_cells']} 个人工填写的格子，保留原文件，没有覆盖{diff}"}
    backup = None
    if st["exists"]:
        bdir = path.parent / "backup"
        bdir.mkdir(exist_ok=True)
        backup = bdir / f"{path.stem}.{datetime.now().strftime('%Y%m%dT%H%M%S')}{path.suffix}"   # the T keeps the name from looking like an account number to the leak scan
        shutil.copy2(path, backup)
        for old in sorted(bdir.glob(f"{path.stem}.*{path.suffix}"))[:-3]:     # keep the three most recent backups
            old.unlink()
    wb = Workbook()
    a_instructions(wb, kb)
    lists = _lists_sheet(wb, kb)
    L = a_table(wb, kb, lists, cases)
    a_coverage(wb, kb, L)
    wb.move_sheet("lists", offset=len(wb.sheetnames))
    replaced = _pseudo_pass(wb, privacy_scan.dictionary(kb.disp002))
    _finalize(wb, skip_autofit=(ANN_SHEET,))
    wb.save(path)
    msg = f"{path.name} 已生成（没有人工填写过）" + (f"，旧文件备份到 backup/{backup.name}" if backup else "")
    return {**st, "written": True, "backup": str(backup) if backup else None, "pseudonymized_cells": replaced, "message": msg}
