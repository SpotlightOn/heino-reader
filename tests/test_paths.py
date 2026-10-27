"""Unit tests for markdown path resolution (no widgets required)."""

from pathlib import Path

from heinoreader import _resolve_relative_paths, _resolve_url

BASE = Path("/base/dir")


def resolve(markdown: str) -> str:
    return _resolve_relative_paths(markdown, BASE)


# ------------------------------------------------------------ inline refs

def test_relative_image_is_made_absolute():
    assert resolve("![alt](img/pic.png)") == "![alt](/base/dir/img/pic.png)"


def test_relative_link_is_made_absolute():
    assert resolve("See [notes](notes.md).") == "See [notes](/base/dir/notes.md)."


def test_absolute_path_stays_absolute():
    assert resolve("![alt](/other/pic.png)") == "![alt](/other/pic.png)"


def test_title_after_destination_is_kept():
    result = resolve('![alt](pics/a.png "My Title")')
    assert result == '![alt](/base/dir/pics/a.png "My Title")'


def test_angle_bracket_destination_with_spaces():
    assert resolve("![alt](<pics/my pic.png>)") == "![alt](</base/dir/pics/my pic.png>)"


# ------------------------------------------------------------- external

def test_http_url_is_untouched():
    assert resolve("![alt](http://example.com/a.png)") == "![alt](http://example.com/a.png)"


def test_https_url_is_untouched():
    assert resolve("[web](https://example.org)") == "[web](https://example.org)"


def test_data_uri_is_untouched():
    markdown = "![a](data:image/png;base64,AAAA)"
    assert resolve(markdown) == markdown


def test_mailto_is_untouched():
    assert resolve("[me](mailto:a@b.c)") == "[me](mailto:a@b.c)"


def test_anchor_is_untouched():
    assert resolve("[top](#top)") == "[top](#top)"


def test_protocol_relative_url_is_untouched():
    markdown = "![a](//example.com/a.png)"
    assert resolve(markdown) == markdown


# ---------------------------------------------------------------- code

def test_fenced_code_block_is_untouched():
    markdown = "# T\n\n```markdown\n![a](img.png)\n```\n"
    assert resolve(markdown) == markdown


def test_tilde_fenced_code_block_is_untouched():
    markdown = "~~~\n![a](img.png)\n~~~\n"
    assert resolve(markdown) == markdown


def test_inline_code_is_untouched():
    markdown = "Use `![a](img.png)` inline.\n"
    assert resolve(markdown) == markdown


def test_indented_code_block_is_untouched():
    markdown = "Text.\n\n    ![a](img.png)\n"
    assert resolve(markdown) == markdown


# ----------------------------------------------------- reference / html

def test_reference_definition_is_rewritten():
    assert resolve("[ref]: pics/a.png") == "[ref]: /base/dir/pics/a.png"


def test_reference_definition_keeps_title():
    result = resolve('[ref]: pics/a.png "Title"')
    assert result == '[ref]: /base/dir/pics/a.png "Title"'


def test_reference_definition_external_is_untouched():
    markdown = "[ref]: https://example.com/a.png"
    assert resolve(markdown) == markdown


def test_html_img_is_rewritten():
    result = resolve('<img src="pics/a.png" alt="x">')
    assert result == '<img src="/base/dir/pics/a.png" alt="x">'


def test_html_img_external_is_untouched():
    markdown = '<img src="https://example.com/a.png">'
    assert resolve(markdown) == markdown


# ----------------------------------------------------------- _resolve_url

def test_resolve_url_relative():
    assert _resolve_url("a.png", BASE) == "/base/dir/a.png"


def test_resolve_url_bracketed():
    assert _resolve_url("<a b.png>", BASE) == "</base/dir/a b.png>"


def test_resolve_url_scheme_kept():
    assert _resolve_url("file:///x/y.png", BASE) == "file:///x/y.png"
