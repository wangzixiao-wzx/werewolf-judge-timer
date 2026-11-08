#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从版型库快照生成「法官计时器」单文件 index.html。

数据内嵌进 HTML，不依赖任何外部请求：把生成的 index.html 单独拷到任何设备，
双击即可离线使用；发布到 GitHub Pages 也只是托管同一个文件。

用法：
    python build_timer.py                 # 默认读 ../werewolf-boards/boards.json
    python build_timer.py --src 其它.json
    python build_timer.py --check        # 只校验数据源，不写文件

版型库更新后：先 python ../werewolf-boards/export_boards.py，再跑本脚本，最后发布。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SRC = ROOT.parent / "werewolf-boards" / "boards.json"
TEMPLATE = ROOT / "index.template.html"
OUT = ROOT / "index.html"
PLACEHOLDER = "/*__TIMER_DATA__*/"

# 公开快照里不该出现的东西（内部字段名 / 对局日期串 / 玩家数据字段）
FORBIDDEN = re.compile(r"doc_files|doc_roles|final_faction_id|game_player|20\d{6}")


def build(src: Path, check: bool = False):
    if not src.exists():
        raise SystemExit("找不到版型库快照：" + str(src))
    data = json.loads(src.read_text(encoding="utf-8"))
    meta = data["meta"]

    boards = []
    for b in data["boards"]:
        boards.append({
            "id": b["id"],
            "name": b["name"],
            "seats": b["seats"],
            "category": b["category"],
            "games": b["games"],
            "note": b["note"],
            "cards": [[c["role"], c["faction_id"], c["count"]] for c in b["cards"]],
            "rules": [[r["key"], r["value"]] for r in b["rules"]],
        })

    payload = {
        "generated": meta["generated"],
        "rules": meta["rule_count"],
        "boards": boards,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if FORBIDDEN.search(raw):
        raise SystemExit("数据快照含内部字段或日期串，拒绝生成：" +
                         str(FORBIDDEN.search(raw).group()))
    if len(boards) != meta["board_count"]:
        raise SystemExit("板子数量不一致")
    if sum(len(b["rules"]) for b in boards) != meta["rule_count"]:
        raise SystemExit("规则条数不一致")

    # 内嵌在 <script> 里，必须防止规则文本中的 </script> 提前闭合标签
    js = "window.TIMER_DATA = " + raw.replace("</", "<\\/") + ";"

    tpl = TEMPLATE.read_text(encoding="utf-8")
    if tpl.count(PLACEHOLDER) != 1:
        raise SystemExit("模板占位符缺失或重复：" + PLACEHOLDER)
    html = tpl.replace(PLACEHOLDER, js)
    if re.search(r'(?:src|href)\s*=\s*["\']https?://', html):
        raise SystemExit("页面含外链资源，不满足离线要求")
    if "</script>" in js:
        raise SystemExit("内嵌数据未正确转义")

    print("校验通过：%d 板 / %d 条规则 / 快照 %s" %
          (len(boards), meta["rule_count"], meta["generated"]))
    print("  身份卡 %d 条｜数据 %.1f KB｜单文件 %.1f KB" %
          (sum(len(b["cards"]) for b in boards),
           len(js.encode("utf-8")) / 1024, len(html.encode("utf-8")) / 1024))
    if check:
        print("--check：未写文件")
        return
    OUT.write_text(html, encoding="utf-8")
    print("已生成 " + str(OUT))


def main():
    ap = argparse.ArgumentParser(description="生成离线法官计时器单文件")
    ap.add_argument("--src", default=str(DEFAULT_SRC), help="版型库 boards.json 路径")
    ap.add_argument("--check", action="store_true", help="只校验不写文件")
    a = ap.parse_args()
    build(Path(a.src), a.check)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
