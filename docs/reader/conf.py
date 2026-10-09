"""Public documentation rendered with the stock Sphinx/Furo toolchain."""

project = "Robotics runtime"
extensions = ["myst_parser", "sphinx_llms_txt"]
source_suffix = {".md": "markdown"}
root_doc = "index"
myst_heading_anchors = 6
myst_enable_extensions = ["colon_fence"]
nitpicky = True

html_theme = "furo"
html_title = project
html_baseurl = "https://mmkolpakov.github.io/robotics-runtime/"
html_copy_source = True
html_show_sourcelink = True
html_show_copyright = False
html_sourcelink_suffix = ""
html_extra_path = [
    "../../build/docs/source/documentation-sources.zip",
    "../../build/docs/source/source-manifest.json",
    "../../build/docs/source/text",
]

llms_txt_title = project
llms_txt_summary = (
    "Development source documentation for robotics contracts, evidence evaluation, "
    "and the composition host. Published packages and frozen qualification "
    "examples retain their own release and commit identities."
)
llms_txt_code_files = [
    "+:docs/architecture/workspace.dsl",
    "+:docs/architecture/run-sequence.mmd",
    "+:docs/architecture/run-state.mmd",
]


def setup(app):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from build import setup_references

    setup_references(app)
    from pygments.lexers.special import TextLexer

    app.add_lexer("mermaid", TextLexer)
