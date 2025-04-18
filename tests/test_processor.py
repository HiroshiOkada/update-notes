import pytest
import re
from pathlib import Path
from datetime import datetime, date, timedelta # date と timedelta を追加
import shutil
import os

# テスト対象のモジュールをインポート
from update_notes.processor import (
    find_image_references,
    process_file,
    write_output_files,
    process_markdown_files # これは統合テストで使うかも
)

# --- find_image_references のテスト ---

def test_find_image_references_markdown():
    """Markdown形式の画像参照を正しく見つけられるか"""
    content = """
    これはテキストです。
    ![alt text](image1.png)
    これもテキスト。
    ![another alt](images/image2.jpg?query=param#fragment)
    外部リンクは無視: ![ext](http://example.com/image.gif)
    """
    expected = {"image1.png", "images/image2.jpg"}
    assert find_image_references(content) == expected

def test_find_image_references_wiki():
    """Wikiリンク形式の画像参照を正しく見つけられるか"""
    content = """
    テキスト ![[image3.bmp]] テキスト。
    パス付き ![[assets/image4.svg]]
    拡張子なし ![[image5]]
    """
    # 拡張子なしの場合もそのまま返すのが現在の仕様
    expected = {"image3.bmp", "assets/image4.svg", "image5"}
    assert find_image_references(content) == expected

def test_find_image_references_mixed():
    """Markdown形式とWikiリンク形式が混在している場合"""
    content = """
    ![md](markdown.png) と ![[wiki.gif]] が混在。
    ![[no_ext]]
    """
    expected = {"markdown.png", "wiki.gif", "no_ext"}
    assert find_image_references(content) == expected

def test_find_image_references_no_images():
    """画像参照がない場合"""
    content = "画像がないテキストです。"
    expected = set()
    assert find_image_references(content) == expected

# --- process_file のテスト ---

# テスト用のヘルパー関数: 一時ファイルを作成
@pytest.fixture
def create_temp_file(tmp_path):
    def _create_temp_file(filename, content):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding='utf-8')
        return file_path
    return _create_temp_file

def test_process_file_basic(create_temp_file):
    """基本的なファイル処理（見出し分割、日付ヘッダー追加）"""
    file_content = """
# 見出し1
内容1-1
内容1-2

## 見出し1.1
内容1.1-1

# 見出し2
内容2-1
![[image.png]]
"""
    file_path = create_temp_file("2024-01-01.md", file_content)
    date_str = "2024-01-01"

    sections, image_refs = process_file(file_path, date_str)

    # 画像参照の確認
    assert image_refs == {"image.png"}

    # セクション内容の確認 (日付ヘッダーと空行が追加される)
    expected_h1_content = [f"## {date_str}", "", "内容1-1", "内容1-2", "", "## 見出し1.1", "内容1.1-1", ""] # これは元のテストの定義（実際には使わない）
    # process_file は最後に空行を追加するため、元の空行と合わせて2つになる
    expected_h2_content = [f"## {date_str}", "", "内容2-1", "![[image.png]]", "", ""]

    # process_file は見出し行自体をキーにする
    assert "# 見出し1" in sections
    # assert "## 見出し1.1" not in sections # サブ見出しも独立キーになるためコメントアウト
    assert "## 見出し1.1" in sections # サブ見出しも独立したキーになることを確認
    assert "# 見出し2" in sections

    # 見出し1の内容確認 (サブ見出しは含まない)
    actual_h1_content = sections["# 見出し1"]
    # process_file は最後に空行を追加するため、元の空行と合わせて2つになる
    expected_h1_content_only = [f"## {date_str}", "", "内容1-1", "内容1-2", "", ""]
    assert actual_h1_content == expected_h1_content_only

    # サブ見出しの内容確認
    actual_h1_1_content = sections["## 見出し1.1"]
    # process_file は最後に空行を追加するため、元の空行と合わせて2つになる
    expected_h1_1_content = [f"## {date_str}", "", "内容1.1-1", "", ""]
    assert actual_h1_1_content == expected_h1_1_content

    # 見出し2の内容確認
    actual_h2_content = sections["# 見出し2"]
    assert actual_h2_content == expected_h2_content

def test_process_file_no_heading(create_temp_file):
    """最初の見出しがない場合のデフォルト処理"""
    file_content = "最初の見出しがない内容です。"
    file_path = create_temp_file("2024-01-02.md", file_content)
    date_str = "2024-01-02"

    sections, image_refs = process_file(file_path, date_str)

    assert image_refs == set()
    assert list(sections.keys()) == ["# はじめに"] # デフォルト見出し
    expected_content = [f"## {date_str}", "", "最初の見出しがない内容です。", ""]
    assert sections["# はじめに"] == expected_content

# --- write_output_files のテスト ---

@pytest.fixture
def setup_output_dir(tmp_path):
    """テスト用の出力ディレクトリを作成"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir

def test_write_output_files_new(setup_output_dir):
    """新しいファイルへの書き込み"""
    output_dir = setup_output_dir
    heading_contents = {
        "# 見出し1": ["## 2024-01-01", "", "内容1"],
        "## 見出し 2?*": ["## 2024-01-01", "", "内容2"] # ファイル名に使えない文字
    }

    write_output_files(heading_contents, output_dir)

    # ファイルが作成されたか確認
    file1_path = output_dir / "見出し1.md"
    file2_path = output_dir / "見出し 2__.md" # 禁止文字 ? と * が両方 _ に置換される

    assert file1_path.exists()
    assert file2_path.exists()

    # ファイル内容を確認
    expected_content1 = "# 見出し1\n\n## 2024-01-01\n\n内容1"
    expected_content2 = "## 見出し 2?*\n\n## 2024-01-01\n\n内容2" # 見出し自体はそのまま

    assert file1_path.read_text(encoding='utf-8') == expected_content1
    assert file2_path.read_text(encoding='utf-8') == expected_content2

def test_write_output_files_append(setup_output_dir, create_temp_file):
    """既存ファイルへの追記"""
    output_dir = setup_output_dir

    # 事前にファイルを作成しておく
    existing_filename = "見出し1.md"
    existing_content = "# 見出し1\n\n## 2023-12-31\n\n古い内容"
    existing_file_path = output_dir / existing_filename
    existing_file_path.write_text(existing_content, encoding='utf-8')

    heading_contents = {
        "# 見出し1": ["## 2024-01-01", "", "新しい内容"]
    }

    write_output_files(heading_contents, output_dir)

    # ファイル内容が追記されているか確認
    expected_content = existing_content + "\n\n## 2024-01-01\n\n新しい内容"
    assert existing_file_path.read_text(encoding='utf-8') == expected_content

# TODO: process_markdown_files の統合テストを追加する
# - ファイルの検索、処理、移動、画像コピー、出力ファイル書き込みの一連の流れを確認
# - Windows特有の処理（ファイル移動の代替、エンコーディング）も考慮できると尚良い
# --- process_markdown_files の統合テスト ---

@pytest.fixture
def setup_integration_test_dirs(tmp_path):
    """統合テスト用のディレクトリ構造を作成"""
    vault_dir = tmp_path / "test_vault_integration"
    input_dir = vault_dir / "日々の記録"
    output_dir = vault_dir / "まとめ"
    oldfiles_dir = input_dir / "oldfiles" # processor が作成する

    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True) # cli が作成するが、テストのために事前に作成

    # テスト用ファイルを作成
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1) # 未来の日付は処理されるはず

    (input_dir / f"{yesterday.strftime('%Y-%m-%d')}.md").write_text(f"# 昨日\n内容", encoding='utf-8')
    (input_dir / f"{today.strftime('%Y-%m-%d')}.md").write_text(f"# 今日\n書きかけ", encoding='utf-8')
    (input_dir / f"{tomorrow.strftime('%Y-%m-%d')}.md").write_text(f"# 未来\n予定", encoding='utf-8')
    # 不正な日付ファイル (処理されないはず)
    (input_dir / "invalid-date.md").write_text("不正なファイル", encoding='utf-8')
    # 日付形式でないファイル (処理されないはず)
    (input_dir / "not-a-date.md").write_text("日付じゃない", encoding='utf-8')


    return input_dir, output_dir, oldfiles_dir, today

def test_process_markdown_files_skips_today(setup_integration_test_dirs, capsys):
    """process_markdown_filesが今日の日付のファイルをスキップするか"""
    input_dir, output_dir, oldfiles_dir, today = setup_integration_test_dirs
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')

    # 実行
    process_markdown_files(input_dir, output_dir)

    # 標準出力のキャプチャを確認
    captured = capsys.readouterr()
    assert f"Skipping 1 file(s) from today ({today_str})" in captured.out
    assert f"Found 3 daily note files, processing 2" in captured.out # 今日を除いた2ファイル
    assert f"Processing {yesterday_str}.md" in captured.out
    assert f"Processing {tomorrow_str}.md" in captured.out
    assert f"Processing {today_str}.md" not in captured.out # 今日のファイルは処理されない

    # oldfiles ディレクトリを確認
    assert not (oldfiles_dir / f"{today_str}.md").exists() # 今日のファイルは移動されない
    assert (oldfiles_dir / f"{yesterday_str}.md").exists() # 昨日のファイルは移動される
    assert (oldfiles_dir / f"{tomorrow_str}.md").exists() # 未来のファイルは移動される

    # 出力ディレクトリを確認
    assert (output_dir / "昨日.md").exists()
    assert (output_dir / "未来.md").exists()
    assert not (output_dir / "今日.md").exists() # 今日のファイルは出力されない

    # 元の入力ディレクトリに今日のファイルが残っているか確認
    assert (input_dir / f"{today_str}.md").exists()