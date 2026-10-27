# Two preview renderers

Heino Reader can paint markdown with two different engines. Switch at runtime via
**View → Web Engine Preview** or at startup with `--renderer qt|web`
(default `qt`).

|  | Qt text renderer (default) | Web Engine preview (optional) |
| --- | --- | --- |
| Engine | `QTextDocument` | QtWebEngine (Chromium) |
| Start | instant, no Chromium process | slower, starts Chromium |
| HTML/CSS | small subset: borders and padding only on table cells, block backgrounds repeat per line | full fidelity |
| Install size | `pyside6-essentials`, ~260 MB | plus `pyside6-addons`, ~440 MB more |

## The Qt renderer

Uses `QTextEdit` and Qt's rich text engine. Starts without spawning a browser
process and ships with the default install — ideal for reading notes quickly. It
is limited by Qt's small CSS subset: table cell borders and padding work, block
backgrounds repeat per line instead of forming one panel.

The whole editor stack (source pane, syntax highlighter, line-number gutter) is
created lazily on the first click on **Edit mode**, so the viewer itself stays
lean.

## The Web Engine preview

The better but slower renderer: tables, borders and backgrounds follow the CSS
exactly. It needs the optional [PySide6-Addons](https://pypi.org/project/PySide6-Addons/)
package:

```sh
pip install "heino-reader[web]"          # or: uv tool install "heino-reader[web]"
scripts/install.sh --web                 # for the local XDG install
```

`pyside6-addons` costs 439 MB installed, which is why it is opt-in. Without it
the menu entry stays greyed out, the app falls back to the Qt renderer and says
so on stderr — no crash, no hidden download.
