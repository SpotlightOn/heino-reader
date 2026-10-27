"""Small modal dialogs for inserting markdown elements.

Each ``ask_*`` function shows a dialog and returns the chosen values, or
``None`` when the user cancels. Nothing here touches the editor or the
formatting engine, so the dialogs stay independent and easy to test; the
caller decides how to insert the result.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _button_box(dialog: QDialog, *buttons: QDialogButtonBox.StandardButton):
    """Standard OK / Cancel buttons that also drive ``dialog.accept``."""
    box = QDialogButtonBox(*buttons, parent=dialog)
    dialog._button_box = box  # keep a reference for callers
    return box


def _heading(text: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


class LinkDialog(QDialog):
    """Ask for a link target (URL or relative path)."""

    def __init__(self, parent: QWidget | None = None, initial: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Link")
        self.setModal(True)

        self._url = QLineEdit(initial, self)
        self._url.setPlaceholderText("https://example.com or path/to/file.md")
        self._url.selectAll()

        form = QFormLayout()
        form.addRow("Target:", self._url)

        box = _button_box(
            self,
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(_heading("Insert Link", self))
        layout.addLayout(form)
        layout.addWidget(box)
        self._url.setFocus()

    def url(self) -> str:
        return self._url.text().strip()


class ImageDialog(QDialog):
    """Ask for an image file and its alternative text.

    The path is stored relative to the markdown file when possible, so the
    document stays portable across machines and checkouts.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        start_dir: str = "",
        alt: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Image")
        self.setModal(True)
        self._start_dir = start_dir

        self._path = QLineEdit(self)
        self._path.setPlaceholderText("path/to/image.png")

        browse_button = QPushButton("Browse…", self)
        browse_button.clicked.connect(self._browse)

        path_row = QFormLayout()
        path_row.addRow("Image:", self._path)

        self._alt = QLineEdit(alt, self)
        self._alt.setPlaceholderText("Description of the image")
        alt_row = QFormLayout()
        alt_row.addRow("Alternative text:", self._alt)

        box = _button_box(
            self,
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(_heading("Insert Image", self))
        layout.addLayout(path_row)
        layout.addWidget(browse_button)
        layout.addLayout(alt_row)
        layout.addWidget(box)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image",
            self._start_dir,
            "Images (*.png *.jpg *.jpeg *.gif *.svg *.bmp *.webp);;All files (*)",
        )
        if path:
            self._path.setText(path)

    def image_path(self) -> str:
        return self._path.text().strip()

    def alternative_text(self) -> str:
        return self._alt.text().strip()


class TableDialog(QDialog):
    """Ask for the size of a new markdown table."""

    def __init__(
        self,
        parent: QWidget | None = None,
        rows: int = 3,
        columns: int = 3,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Table")
        self.setModal(True)

        self._rows = QSpinBox(self)
        self._rows.setRange(2, 100)
        self._rows.setValue(rows)

        self._columns = QSpinBox(self)
        self._columns.setRange(1, 50)
        self._columns.setValue(columns)

        form = QFormLayout()
        form.addRow("Rows (incl. header):", self._rows)
        form.addRow("Columns:", self._columns)

        box = _button_box(
            self,
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(_heading("Insert Table", self))
        layout.addLayout(form)
        layout.addWidget(box)

    def rows(self) -> int:
        return self._rows.value()

    def columns(self) -> int:
        return self._columns.value()


# ------------------------------------------------------------------ helpers

def ask_link_url(parent: QWidget, initial: str = "") -> str | None:
    """Return the entered link target, or None when cancelled."""
    dialog = LinkDialog(parent, initial)
    return dialog.url() if dialog.exec() else None


def ask_image(
    parent: QWidget, start_dir: str = "", alt: str = ""
) -> tuple[str, str] | None:
    """Return ``(path, alt_text)``, or None when cancelled."""
    dialog = ImageDialog(parent, start_dir, alt)
    if not dialog.exec():
        return None
    path = dialog.image_path()
    return (path, dialog.alternative_text()) if path else None


def ask_table_size(
    parent: QWidget, rows: int = 3, columns: int = 3
) -> tuple[int, int] | None:
    """Return ``(rows, columns)``, or None when cancelled."""
    dialog = TableDialog(parent, rows, columns)
    return (dialog.rows(), dialog.columns()) if dialog.exec() else None
