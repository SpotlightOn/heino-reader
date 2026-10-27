# Usage

## Opening files

```sh
heino-reader                        # start screen with a short guide
heino-reader notes.md               # open a file
heino-reader --renderer web notes.md   # force the Web Engine renderer
```

`uv run python -m HeinoReader notes.md` works as well (the Python package name
cannot contain a hyphen). You can also drag a markdown file onto the window or
open one via **File → Open…**.

Only text formats are opened. Images, archives and other binaries — plus files
larger than 10 MB — are refused with a message instead of being loaded as text.
The same check applies to the Open dialog, the command line and drag & drop.

## The window

- **Top toolbar:** decrease/increase font size, toggle edit mode, close the
  window — plus a zoom indicator such as `130%` in the right corner.
- **Menu bar:** **File → Open… / Save / Save As… / Close**,
  **View → …**, **Help → About**. Saving is available in edit mode only.
- **Text column:** content is inset, capped at 760 px and centred, so lines stay
  readable no matter how wide the window is.
- **Start screen:** app icon and a short guide (open, edit, zoom, remote images,
  the Web Engine switch).

## Edit mode

Click the pencil in the toolbar or press the **Edit mode** toggle again to leave
it. The window splits: markdown source on the left, live preview on the right.

- Entering edit mode widens the window up to 1200 px, clamped to the usable
  screen width; leaving it restores the previous size and position.
- A second toolbar row appears only while editing: bold, italic, underline,
  strikethrough, inline code, heading dropdown, block quote, bullet list,
  numbered list.
- Every formatting command is a toggle: applied to text that already carries the
  marker, it removes it again. Each command is a single undo step.
- **Undo** and **Redo** start the second toolbar row (or `Ctrl+Z`,
  `Ctrl+Shift+Z`, `Ctrl+Y`); both are greyed out while there is nothing to
  undo or redo. The preview is read-only, so it has no history of its own.
- The block commands (quote, both lists, headings) also work on an empty line:
  the marker is inserted and the cursor lands behind it, so the next keystroke
  is already inside the block. A list started that way continues the one above
  it — indentation, bullet character and numbering included.
- The source pane is a real code editor: markdown syntax highlighting, Tab /
  Shift+Tab indent whole lines, and a bar marks block quotes.
- Enter continues the block you are in: `> ` stays a quote, `- `, `* ` and
  `+ ` open the next bullet, `1. ` counts up and keeps its `.` or `)`
  delimiter. Nested markers and indentation are preserved. Enter on an item
  that is still empty ends the list or quote instead of adding an empty item.
- **View → Line Numbers** shows an optional gutter. The editor works without it.

## Insert dialogs

| Menu entry | Shortcut | Result |
| --- | --- | --- |
| Link… | `Ctrl+K` | wraps the selection as `[label](url)` |
| Image… | `Ctrl+Shift+I` | file chooser, path stored relative to the document |
| Table… | `Ctrl+Shift+T` | asks for rows/columns, inserts a skeleton with the first header cell selected |

## Keyboard shortcuts

Viewing:

| Shortcut | Action |
| --- | --- |
| `Ctrl++` / `Ctrl+-` | Zoom in / out |
| `Ctrl+0` | Reset zoom to 100 % |
| `Ctrl+O` | Open a file |
| `Ctrl+S` | Save (edit mode) |
| `Ctrl+Shift+S` | Save as… (edit mode) |
| `Ctrl+W` | Close the file |
| `Ctrl+Q` | Quit |

Editing (edit mode only):

| Shortcut | Action |
| --- | --- |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Redo |

Formatting (edit mode only):

| Shortcut | Action | Markdown |
| --- | --- | --- |
| `Ctrl+B` | Bold | `**…**` |
| `Ctrl+I` | Italic | `*…*` |
| `Ctrl+U` | Underline | `<u>…</u>` |
| `Ctrl+Shift+X` | Strikethrough | `~~…~~` |
| `Ctrl+E` | Inline code | `` `…` `` |
| `Ctrl+1` … `Ctrl+6` | Heading level 1–6 | `#` … `######` |
| `Ctrl+Shift+0` | Plain paragraph | (clears the heading) |
| `Ctrl+Shift+Q` | Block quote | `> ` |
| `Ctrl+Shift+L` | Bullet list | `- ` |
| `Ctrl+Shift+N` | Numbered list | `1. ` |

## Images, links and live reload

- Links open with the system default application (`xdg-open`).
- Relative image and link paths resolve against the markdown file's directory;
  code blocks stay untouched.
- Images scale down to the available width, aspect ratio preserved, and refit on
  window resize.
- Remote (`http(s)`) images are downloaded asynchronously and cached.
  **View → Load Remote Images** turns network access off; disabled or failed
  images show a visible placeholder.
- An open file is reloaded automatically when it changes on disk.

## Theme

The preview theme is a plain stylesheet: `src/HeinoReader/preview.css`. Both
backends use it, so it keeps standard CSS (`em`, `line-height`, `max-width`);
the Qt backend derives its typography from the body rule and hands the size to
Qt in points, which keeps the text DPI aware. Toolbar icons are bundled Material
Symbols Outlined SVGs, rendered in the palette text color so they stay readable
in light and dark themes; if a file is missing, the app falls back to the
desktop theme icons.
