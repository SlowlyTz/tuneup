"""The settings window's files fit together: every ES module import and every
file index.html loads exists, and each module is reachable from the entry."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "hypr_screens" / "web"
IMPORT = re.compile(r'^import\s+(?:[^"\']+?\s+from\s+)?["\'](\.{1,2}/[^"\']+)["\'];', re.M)
# Plain scripts, loaded by index.html before the app.
SCRIPTS = {"bridge.js", "mock.js"}


def modules() -> list[Path]:
    return [path for path in sorted(WEB.rglob("*.js")) if path.name not in SCRIPTS]


def imports(path: Path) -> list[Path]:
    return [(path.parent / spec).resolve() for spec in IMPORT.findall(path.read_text(encoding="utf-8"))]


def test_every_import_exists():
    missing = [(str(path.relative_to(WEB)), str(target)) for path in modules() for target in imports(path) if not target.is_file()]
    assert missing == []


def test_index_loads_what_exists():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    files = re.findall(r'(?:href|src)="([^"#:]+\.(?:css|js))"', html)
    assert files and all((WEB / name).is_file() for name in files), files
    assert '<script type="module" src="app.js">' in html
    # The bridge (and the mock) must run before the app module.
    assert html.index('src="bridge.js"') < html.index('src="app.js"')


def test_every_module_is_used():
    reached, todo = set(), [(WEB / "app.js").resolve()]
    while todo:
        path = todo.pop()
        if path in reached:
            continue
        reached.add(path)
        todo.extend(imports(path))
    assert sorted(str(p.relative_to(WEB)) for p in modules() if p.resolve() not in reached) == []


def test_every_stylesheet_is_loaded():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    sheets = {path.relative_to(WEB).as_posix() for path in WEB.rglob("*.css")}
    assert sheets == set(re.findall(r'href="([^"]+\.css)"', html))
