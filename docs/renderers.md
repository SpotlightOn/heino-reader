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

### Typography

`preview.css` is shared with the Web Engine backend, so its body rule keeps
CSS pixels. For the Qt backend the body size and font family are read from that
file and handed to `QTextDocument.setDefaultFont()` as a **point** size
(16 px → 12 pt) — the one thing a `QTextDocument` cannot take from a stylesheet,
because `setHtml()` parses a fragment without a `<body>` element, so a
`body { … }` rule never matches.

Points matter here: Qt scales point sizes with the screen DPI, while CSS pixel
sizes are DPI blind inside `QTextDocument`. The preview therefore looks the same
size as the rest of the desktop at 96, 144 or any other DPI, and zoom just
multiplies the point size. Heading levels come from Qt's own HTML scale
(about 2× / 1.5× / 1.2× of the body font), which scales along with it — no
`em` conversion involved.

### Line spacing

Qt does parse `line-height` into the block format, but reads the number as a
percentage of the font's *natural* line height, while CSS means it relative to
the *font size*. `line-height: 1.55` therefore becomes a corrected percentage
(~114 %), computed from Qt's own font metrics — the same `QFontMetricsF` and
`QFontInfo` calls any Qt app would use, no DPI arithmetic. Blocks whose rule
never matched (paragraphs, thanks to the missing `<body>`) get the body value
explicitly; code blocks and headings keep the value of their own rule.

One limit of the engine: `QTextBlockFormat` line heights only affect the
spacing *between* the lines of a block. A paragraph that fits on a single line
keeps the font's own height, so its box is a couple of pixels lower than in the
Web Engine backend — the gap between paragraphs comes from the CSS margins
either way, which Qt applies normally.

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
