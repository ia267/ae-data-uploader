from __future__ import annotations

import json

import pytest

from ae_uploader.indexer import IndexGenerator, MultiFileIndexGenerator, save_index


def test_generate_returns_generic_index_for_unknown_extension(tmp_path):
    file_path = tmp_path / "sample.foo"
    file_path.write_bytes(b"abcdef")

    index = IndexGenerator.generate(file_path)

    assert index["file_type"] == "generic"
    assert index["file_size"] == 6
    assert index["file_name"] == "sample.foo"


def test_generate_csv_index_includes_chunks_and_columns(tmp_path):
    file_path = tmp_path / "sample.csv"
    file_path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")

    index = IndexGenerator.generate(file_path)

    assert index["file_type"] == "csv"
    assert index["columns"] == ["x", "y"]
    assert index["total_chunks"] == 1
    assert index["chunks"]["chunk_0"]["line_range"] == [1, 2]


def test_generate_master_index_groups_multiple_generic_files(tmp_path):
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    (tmp_path / "b.txt").write_text("two", encoding="utf-8")

    master_index = MultiFileIndexGenerator.generate_master_index(tmp_path)

    assert master_index["index_type"] == "master"
    assert master_index["total_files"] == 2
    assert "generic_group" in master_index["files"]


def test_generate_master_index_raises_for_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="No files found"):
        MultiFileIndexGenerator.generate_master_index(tmp_path)


def test_save_index_writes_json_file(tmp_path):
    output_file = tmp_path / "index.json"
    payload = {"version": "1.0", "items": [1, 2, 3]}

    save_index(payload, output_file)

    assert json.loads(output_file.read_text(encoding="utf-8")) == payload
