"""The open document: reading, writing and the modified state (no widgets)."""

from __future__ import annotations

from pathlib import Path

from HeinoReader.document import Document


def test_name_falls_back_to_a_stand_in_before_the_first_save():
    assert Document("# heading").name == "This document"


def test_name_uses_the_file_name():
    document = Document("# heading")
    document.adopt(Path("notes.md"))

    assert document.name == "notes.md"


def test_reading_a_directory_reports_the_error(tmp_path, capsys):
    document = Document()

    assert document.read(tmp_path) is False

    assert "cannot read" in capsys.readouterr().err
    assert document.path is None


def test_reading_a_file_adopts_it_and_clears_the_modified_state(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Fresh\n", encoding="utf-8")
    document = Document("stale")

    assert document.read(path) is True

    assert document.path == path
    assert document.markdown == "# Fresh\n"
    assert document.is_modified is False


def test_writing_into_a_missing_folder_keeps_the_text_unsaved(tmp_path, capsys):
    document = Document("saved")
    document.markdown = "changed"

    assert document.write(tmp_path / "missing" / "notes.md") is False

    assert "cannot save" in capsys.readouterr().err
    assert document.is_modified is True


def test_writing_marks_the_text_as_saved(tmp_path):
    path = tmp_path / "notes.md"
    document = Document("text")

    assert document.write(path) is True

    assert path.read_text(encoding="utf-8") == "text"
    assert document.is_modified is False
