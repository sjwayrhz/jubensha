"""剧本结构化：把校对后的全文按简单规则拆成标题/简介/人数/人物/线索。

v1 启发式规则，细节二期再精修。所有正则只做尽力提取，提不到就留空，
不猜、不编。
"""
import logging
import re

log = logging.getLogger("jubensha.structure")

_SECTION_KEYWORDS = ("人物", "角色")
_CLUE_KEYWORDS = ("线索",)
_INTRO_KEYWORDS = ("简介", "故事背景", "故事梗概", "前言")
_END_KEYWORDS = _SECTION_KEYWORDS + _CLUE_KEYWORDS + _INTRO_KEYWORDS + ("真相", "复盘", "结局")


def _lines(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _find_section(lines, keywords):
    """返回首个包含关键词的标题行下标，找不到返回 -1。"""
    for i, ln in enumerate(lines):
        short = ln[:20]
        if any(k in short for k in keywords) and len(ln) <= 30:
            return i
    return -1


def _looks_like_header(ln):
    """疑似标题行：短行含关键词，或第X幕/章/节格式。"""
    if re.match(r"^第?[一二三四五六七八九十\d]+[幕章节]", ln):
        return True
    return len(ln) <= 8 and any(k in ln for k in _END_KEYWORDS)


def _section_end(lines, start):
    for j in range(start + 1, len(lines)):
        if _looks_like_header(lines[j]):
            return j
    return len(lines)


def _clean_desc(s):
    return s.lstrip("：:").strip()


def structure_script(raw_text):
    """拆分全文，返回 dict：title/description/player_min/player_max/
    characters[{name, description}]/clues[{title, content}]。"""
    lines = _lines(raw_text)
    out = {
        "title": lines[0] if lines else "",
        "description": "",
        "player_min": 0,
        "player_max": 0,
        "characters": [],
        "clues": [],
    }
    if not lines:
        return out

    head = "\n".join(lines[:30])
    m = re.search(r"(\d+)\s*[-~～]\s*(\d+)\s*人", head)
    if m:
        out["player_min"], out["player_max"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(\d+)\s*人", head)
        if m:
            out["player_min"] = out["player_max"] = int(m.group(1))

    intro_idx = _find_section(lines, _INTRO_KEYWORDS)
    if intro_idx >= 0:
        end = _section_end(lines, intro_idx)
        out["description"] = "\n".join(lines[intro_idx + 1:end])[:2000]

    char_idx = _find_section(lines, _SECTION_KEYWORDS)
    if char_idx >= 0:
        end = _section_end(lines, char_idx)
        order = 0
        for ln in lines[char_idx + 1:end]:
            name, desc = None, ""
            m = re.match(r"^【(.{1,12})】\s*(.*)$", ln)
            if m:
                name, desc = m.group(1).strip(), _clean_desc(m.group(2))
            else:
                m = re.match(r"^(.{1,12})[：:]\s*(.{4,})$", ln)
                if m:
                    name, desc = m.group(1).strip(), _clean_desc(m.group(2))
            if name and not any(c["name"] == name for c in out["characters"]):
                out["characters"].append(
                    {"name": name, "description": desc, "sort_order": order}
                )
                order += 1

    clue_idx = _find_section(lines, _CLUE_KEYWORDS)
    if clue_idx >= 0:
        end = _section_end(lines, clue_idx)
        order = 0
        for ln in lines[clue_idx + 1:end]:
            title, content = None, ""
            m = re.match(r"^【(.{1,30})】\s*(.*)$", ln)
            if m:
                title, content = m.group(1).strip(), _clean_desc(m.group(2))
            else:
                m = re.match(r"^线索\s*(\d*)\s*[：:]\s*(.+)$", ln)
                if m:
                    n = m.group(1)
                    title = "线索%s" % n if n else "线索"
                    content = m.group(2).strip()
                else:
                    m = re.match(r"^\d+[.、]\s*(.{2,})$", ln)
                    if m:
                        title, content = "线索%d" % (order + 1), m.group(1).strip()
            if content:
                out["clues"].append(
                    {"title": title, "content": content, "sort_order": order}
                )
                order += 1

    log.info("结构化完成：%d 个人物，%d 条线索", len(out["characters"]), len(out["clues"]))
    return out
