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


# --- spec 017: pronunciation column ----------------------------------------------


def test_slashed_field_is_pronunciation_not_alternate():
    item = _simple("receive, 收到, /rɪˈsiːv/, accept").items[0]
    assert item.ipa == "rɪˈsiːv"
    assert item.alternates == ["accept"]


def test_pronunciation_in_any_later_position_and_brackets():
    item = _simple("receive, 收到, accept, [rɪˈsiːv]").items[0]
    assert (item.ipa, item.alternates) == ("rɪˈsiːv", ["accept"])


def test_pronunciation_with_tabs():
    item = _simple("look up\t查找\t/lʊk ˈʌp/\tsearch").items[0]
    assert (item.ipa, item.alternates) == ("lʊk ˈʌp", ["search"])


def test_second_pronunciation_ignored_with_message():
    parsed = _simple("receive, 收到, /rɪˈsiːv/, /rəˈsiːv/")
    assert parsed.items[0].ipa == "rɪˈsiːv"
    assert parsed.skipped == ["line 1: more than one pronunciation — kept the first"]


def test_invalid_pronunciation_keeps_word():
    parsed = _simple("bad, 坏, /123/")
    assert len(parsed.items) == 1
    assert parsed.items[0].ipa is None
    assert parsed.skipped == ['line 1: "/123/" is not a pronunciation']


def test_markdown_invalid_ipa_keeps_word_with_message():
    parsed = parse_upload("a.md", b"---\nenglish: x\nipa: 42\nchinese: y\n---\n")
    assert len(parsed.items) == 1
    assert parsed.items[0].ipa is None
    assert parsed.skipped[0].startswith("block 1:")
    assert "is not a pronunciation" in parsed.skipped[0]


def test_no_pronunciation_is_invented():
    item = _simple("receive, 收到, accept").items[0]
    assert item.ipa is None


# --- spec 018: parse_upload(require_chinese=False) -> DraftWord ------------

from src.services.word_lists import DraftWord


def _drafts(text: str, name: str = "z-words.txt"):
    return parse_upload(name, text.encode("utf-8"), require_chinese=False)


def test_bare_english_lines_become_drafts():
    parsed = _drafts("zealous\ntyre\n")
    assert parsed.skipped == []
    assert parsed.items == [
        DraftWord("zealous", None, None, [], "line 1"),
        DraftWord("tyre", None, None, [], "line 2"),
    ]


def test_supplied_fields_are_kept_on_drafts():
    parsed = _drafts("receive, 收到；接受, /rɪˈsiːv/, accept")
    draft = parsed.items[0]
    assert draft.chinese == "收到；接受"
    assert draft.ipa == "rɪˈsiːv"
    assert draft.alternates == ["accept"]


def test_pronunciation_in_field_two_is_not_chinese():
    draft = _drafts("receive, /rɪˈsiːv/").items[0]
    assert draft.chinese is None
    assert draft.ipa == "rɪˈsiːv"


def test_draft_english_is_only_trimmed():
    assert _drafts("  Hello!  ").items[0].english == "Hello!"


def test_draft_line_without_english_is_still_skipped():
    parsed = _drafts(", 收到\nzealous\n")
    assert [d.english for d in parsed.items] == ["zealous"]
    assert parsed.skipped == ["line 1: no English word"]


def test_draft_header_row_skipped():
    parsed = _drafts("English, Chinese\nzealous\n")
    assert [d.english for d in parsed.items] == ["zealous"]


def test_markdown_block_without_chinese_becomes_draft():
    text = "---\nenglish: zealous\n---\n\n---\nchinese: 收到\n---\n"
    parsed = _drafts(text, "z.md")
    assert parsed.items == [DraftWord("zealous", None, None, [], "block 1")]
    assert parsed.skipped == ["block 2: missing 'english'"]


def test_markdown_draft_bad_alternates_skipped():
    parsed = _drafts("---\nenglish: zealous\nalternates: keen\n---\n", "z.md")
    assert parsed.items == []
    assert parsed.skipped == ["block 1: alternates must be a list of words"]


def test_markdown_draft_ignores_group_and_keeps_fields():
    text = "---\nenglish: receive\nipa: /rɪˈsiːv/\nalternates: [accept]\nchinese: 收到\ngroup: x\n---\n"
    draft = _drafts(text, "z.md").items[0]
    assert draft == DraftWord("receive", "收到", "rɪˈsiːv", ["accept"], "block 1")


def test_draft_word_limit_still_applies():
    with pytest.raises(UploadFormatError):
        _drafts("w\n" * 5001)


def test_default_still_requires_chinese():
    parsed = _simple("zealous\nreceive, 收到\n")
    assert [i.english for i in parsed.items] == ["receive"]
    assert parsed.skipped == ["line 1: no Chinese meaning"]


# --- spec 018: a .md file of plain lines is read as a simple list -------------


def test_markdown_without_blocks_reads_lines():
    parsed = _drafts("qualify\nquality\nquantity\n", "words.md")
    assert [d.english for d in parsed.items] == ["qualify", "quality", "quantity"]
    assert parsed.items[0].position == "line 1"
    assert parsed.skipped == []


def test_markdown_lines_drop_headings_and_list_markers():
    text = "# Unit 3\n\n- qualify\n* quality, 质量\n1. quantity\n+ tend to\n"
    parsed = _drafts(text, "words.md")
    assert [d.english for d in parsed.items] == ["qualify", "quality", "quantity", "tend to"]
    assert parsed.items[1].chinese == "质量"


def test_markdown_with_blocks_is_unchanged():
    text = "---\nenglish: receive\nchinese: 收到\n---\n\nqualify\n"
    parsed = _drafts(text, "words.md")
    assert [d.english for d in parsed.items] == ["receive"]


def test_legacy_markdown_upload_still_needs_blocks():
    assert parse_upload("w.md", b"qualify\nquality\n").items == []


# --- spec 019: part of speech in uploads --------------------------------------


def test_simple_list_pos_field_any_position():
    zealous = _drafts("zealous, adj., 热心的").items[0]
    assert (zealous.pos, zealous.chinese) == (["adj."], "热心的")
    rent = _drafts("rent, 租金；出租, n. v.").items[0]
    assert (rent.pos, rent.chinese) == (["n.", "v."], "租金；出租")
    give_up = _drafts("give up, 放弃, phr. v., /ˌɡɪv ˈʌp/").items[0]
    assert (give_up.pos, give_up.ipa, give_up.alternates) == (["phr. v."], "ˌɡɪv ˈʌp", [])


def test_bare_letter_stays_an_alternate():
    tyre = _drafts("tyre, 轮胎, n").items[0]
    assert (tyre.alternates, tyre.pos) == (["n"], [])


def test_second_pos_field_is_reported():
    parsed = _drafts("rent, 租金, n., v.")
    assert parsed.items[0].pos == ["n."]
    assert parsed.skipped == ["line 1: more than one part of speech — kept the first"]


def test_legacy_upload_meaning_skips_pos_field():
    item = _simple("receive, v., 收到").items[0]
    assert (item.chinese, item.pos) == ("收到", ["v."])


def test_markdown_draft_pos():
    draft = _drafts("---\nenglish: zealous\npos: adjective\n---\n", "z.md").items[0]
    assert draft.pos == ["adj."]
    parsed = _drafts("---\nenglish: zealous\npos: verbish\n---\n", "z.md")
    assert parsed.items[0].pos == []
    assert parsed.skipped == ['block 1: pos "verbish" is not a part of speech']
