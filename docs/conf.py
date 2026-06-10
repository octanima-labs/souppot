from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "souppot"
copyright = "2026, souppot contributors"
author = "souppot contributors"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"

html_theme = "pydata_sphinx_theme"
html_title = "souppot"
html_sidebars = {
    "**": [],
}
html_theme_options = {
    "show_toc_level": 2,
}

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_typehints_format = "short"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "bs4": ("https://www.crummy.com/software/BeautifulSoup/bs4/doc/", None),
}
