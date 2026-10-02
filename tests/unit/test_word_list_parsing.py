"""Unit tests for parse_upload (spec 016, contracts/upload-formats.md)."""

import pytest

from src.services.word_lists import UploadFormatError, parse_upload


def _simple(text: str, name: str = "unit1.csv"):
    return parse_upload(name, text.encode("utf-8"))


# --- routing & decoding ----------------------------------------------------


@pytest.mark.parametrize("name", ["a.CSV", "a.txt", "a.tsv", "A.Txt"])
def test_simple_extensions(name):
    assert _simple("receive, 收到", name).items[0].english == "receive"


@pytest.mark.parametrize("name", ["a.md", "a.MARKDOWN"])
def test_markdown_extensions(name):
    parsed = parse_upload(name, "---\nenglish: receive\nchinese: 收到\n---\n".encode())
    assert parsed.items[0].chinese == "收到"


def test_unsupported_extension():
    with pytest.raises(UploadFormatError) as exc:
        parse_upload("x.xlsx", b"whatever")
    assert str(exc.value) == 'Unsupported file type ".xlsx". Upload a .csv, .txt or .md file.'


def test_missing_extension_is_rejected():
    with pytest.raises(UploadFormatError):
        parse_upload("words", b"receive, x")


def test_utf8_bom_is_stripped():
    parsed = parse_upload("a.csv", b"\xef\xbb\xbf" + "receive, 收到".encode())
    assert parsed.items[0].english == "receive"


def test_gb18030_fallback():
    parsed = parse_upload("a.csv", "receive, 收到".encode("gb18030"))
    assert parsed.items[0].chinese == "收到"


def test_undecodable_bytes():
    with pytest.raises(UploadFormatError) as exc:
        parse_upload("a.csv", b"\xff\xfe\xfa\x80\x81")
    assert "Save it as UTF-8" in str(exc.value)


# --- simple list -------------------------------------------------------------


def test_ascii_comma():
    item = _simple("receive, 收到").items[0]
    assert (item.english, item.chinese, item.alternates) == ("receive", "收到", [])


def test_full_width_comma():
    item = _simple("give up，放弃").items[0]
    assert (item.english, item.chinese) == ("give up", "放弃")


def test_tabs():
    item = _simple("look up\t查找\tsearch").items[0]
    assert (item.english, item.chinese, item.alternates) == ("look up", "查找", ["search"])


def test_extra_fields_are_alternates_and_semicolon_meanings_kept():
    item = _simple("receive, 收到；接受, accept, get").items[0]
    assert item.chinese == "收到；接受"
    assert item.alternates == ["accept", "get"]


def test_quoted_field():
    item = _simple('"set off, start", 出发').items[0]
    assert item.english == "set off, start"


def test_empty_extra_fields_ignored():
    assert _simple("receive, 收到, ,").items[0].alternates == []


def test_blank_and_comment_lines_ignored():
    parsed = _simple("\n# my list\n\nreceive, 收到\n   \n")
    assert len(parsed.items) == 1
    assert parsed.skipped == []


@pytest.mark.parametrize("header", ["English, Chinese", "word,meaning", "英文，中文", "单词\t意思"])
def test_header_row_skipped(header):
    parsed = _simple(f"{header}\nreceive, 收到\n")
    assert [i.english for i in parsed.items] == ["receive"]
    assert parsed.skipped == []


def test_skip_messages_use_file_line_numbers():
    parsed = _simple("English, Chinese\nreceive, 收到\nbroken line\n, 放弃\n")
    assert len(parsed.items) == 1
    assert parsed.skipped == ["line 3: no Chinese meaning", "line 4: no English word"]


def test_no_valid_words_returns_empty_items():
    parsed = _simple("\n\n# nothing\n")
    assert parsed.items == []


def test_word_limit():
    with pytest.raises(UploadFormatError) as exc:
        _simple("".join(f"w{i}, 词\n" for i in range(5001)))
    assert str(exc.value) == "That list has 5001 words; the limit is 5,000."
    assert len(_simple("".join(f"w{i}, 词\n" for i in range(5000))).items) == 5000


# --- markdown ----------------------------------------------------------------


def test_markdown_skips_invalid_block_with_number_and_drops_group():
    text = "---\nenglish: tablet\nchinese: 平板\ngroup: t-words\n---\n\n---\nenglish: tailor\n---\n"
    parsed = parse_upload("T_words.md", text.encode())
    assert [i.english for i in parsed.items] == ["tablet"]
    assert parsed.items[0].group is None
    assert len(parsed.skipped) == 1
    assert parsed.skipped[0].startswith("block 2:")


def test_markdown_yaml_bool_words_stay_text():
    parsed = parse_upload("a.md", "---\nenglish: on\nchinese: 在上面\n---\n".encode())
    assert parsed.items[0].english == "on"
