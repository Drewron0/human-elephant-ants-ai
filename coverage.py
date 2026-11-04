import ast
import os
import glob
import re
import sys
from collections import defaultdict

TARGET_FILES = [
    "main.py",
    "gui.py",
    "ui_theme.py",
    "game_logic.py",
    "ai_engine.py",
    "puzzle_logic.py",
    "storage.py",
    "network.py",
    "run_benchmark.py",
    "verify_stages.py",
    "views/benchmark_view.py",
    "views/config_view.py",
    "views/game_view.py",
    "views/leaderboard_view.py",
    "views/menu_view.py",
    "views/puzzle_game_view.py",
    "views/puzzle_select_view.py",
    "views/stage_editor_view.py",
    "views/tutorial_view.py",
]

def extract_symbols(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src, filename=filepath)
    symbols = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.append({
                        "file": filepath,
                        "type": "constant",
                        "name": target.id,
                        "qualname": target.id,
                        "line": node.lineno
                    })
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                symbols.append({
                    "file": filepath,
                    "type": "constant",
                    "name": node.target.id,
                    "qualname": node.target.id,
                    "line": node.lineno
                })
        elif isinstance(node, ast.FunctionDef):
            symbols.append({
                "file": filepath,
                "type": "function",
                "name": node.name,
                "qualname": node.name,
                "line": node.lineno
            })
        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "file": filepath,
                "type": "class",
                "name": node.name,
                "qualname": node.name,
                "line": node.lineno
            })
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    symbols.append({
                        "file": filepath,
                        "type": "method",
                        "name": item.name,
                        "qualname": f"{node.name}.{item.name}",
                        "line": item.lineno
                    })

    return symbols

def load_tutorial_htmls(tutorial_dir="tutorial_book"):
    html_files = glob.glob(os.path.join(tutorial_dir, "*.html"))
    content_by_file = {}
    combined_content = ""
    for hf in html_files:
        with open(hf, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            content_by_file[hf] = text
            combined_content += "\n" + text
    return html_files, content_by_file, combined_content

def check_coverage(tutorial_dir="tutorial_book", verbose=True):
    all_symbols = []
    for tf in TARGET_FILES:
        all_symbols.extend(extract_symbols(tf))

    html_files, content_by_file, combined_content = load_tutorial_htmls(tutorial_dir)

    covered = []
    uncovered = []

    symbol_locations = defaultdict(list)

    for sym in all_symbols:
        name = sym["name"]
        qualname = sym["qualname"]
        
        pattern = re.compile(r'\b' + re.escape(name) + r'\b')
        
        found_in = []
        for hf, text in content_by_file.items():
            if pattern.search(text):
                found_in.append(os.path.basename(hf))
        
        if found_in:
            covered.append(sym)
            symbol_locations[qualname] = found_in
        else:
            uncovered.append(sym)

    total = len(all_symbols)
    cov_count = len(covered)
    uncov_count = len(uncovered)
    pct = (cov_count / total * 100) if total > 0 else 0

    if verbose:
        print("=" * 60)
        print("CHESS-SUT TUTORIAL CODEBASE COVERAGE REPORT")
        print("=" * 60)
        print(f"Total Target Files    : {len(TARGET_FILES)}")
        print(f"Total HTML Chapters   : {len(html_files)}")
        print(f"Total Codebase Symbols: {total}")
        print(f"Covered Symbols       : {cov_count} ({pct:.1f}%)")
        print(f"Uncovered Symbols     : {uncov_count}")
        print("=" * 60)

        if uncov_count > 0:
            print("\nUNCOVERED SYMBOLS BY FILE:")
            by_file = defaultdict(list)
            for s in uncovered:
                by_file[s["file"]].append(f"{s['qualname']} (L{s['line']}, {s['type']})")
            for fpath, syms in sorted(by_file.items()):
                print(f"\n[{fpath}] ({len(syms)} uncovered):")
                for s in syms:
                    print(f"  - {s}")
        else:
            print("\nALL SYMBOLS ARE 100% COVERED! COVERAGE GATE PASSED.")

    return {
        "total": total,
        "covered": cov_count,
        "uncovered": uncov_count,
        "percentage": pct,
        "uncovered_symbols": uncovered,
        "symbol_locations": symbol_locations
    }

if __name__ == "__main__":
    report = check_coverage()
    if report["uncovered"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
