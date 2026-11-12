"""Convert the percent-format analysis scripts (# %% cells) into executed Jupyter notebooks.

The .py scripts are the tested source of truth; the notebooks are generated from them so both always agree.
Run:  python scripts/build_notebooks.py   (needs nbformat, nbclient, ipykernel)
"""
import re
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MAP = {"02_cleaning_validation.py": "02_cleaning_validation.ipynb", "03_eda.py": "03_eda_statistics.ipynb",
       "04_advanced_analytics.py": "04_advanced_analytics.ipynb", "05_export_powerbi.py": "05_export_powerbi.ipynb"}


def to_notebook(path):
    cells, buf, kind = [], [], None

    def flush():
        if kind is None or not "".join(buf).strip():
            return
        body = "".join(buf).strip("\n")
        if kind == "md":
            body = "\n".join(re.sub(r"^# ?", "", ln) for ln in body.splitlines())
            cells.append(nbformat.v4.new_markdown_cell(body))
        else:
            cells.append(nbformat.v4.new_code_cell(body))

    for line in path.read_text().splitlines(keepends=True):
        if line.startswith("# %%"):
            flush(); buf = []
            kind = "md" if "[markdown]" in line else "code"
        else:
            buf.append(line)
    flush()
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


if __name__ == "__main__":
    (ROOT / "notebooks").mkdir(exist_ok=True)
    for src, dst in MAP.items():
        nb = to_notebook(SCRIPTS / src)
        NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(SCRIPTS)}}).execute()
        nbformat.write(nb, ROOT / "notebooks" / dst)
        print("built + executed:", dst, f"({len(nb.cells)} cells)")
