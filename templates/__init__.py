"""Jinja2 template stubs (kept for future expansion).

ScaffoldAgent currently emits boilerplate inline for zero-dependency
operation. When Jinja2 is available, templates can be loaded from this
package via:

    import importlib.resources as resources
    text = resources.files("forgeos.templates.fastapi").joinpath("main.py.j2").read_text()
"""
