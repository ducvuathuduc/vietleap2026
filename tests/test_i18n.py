"""Feature 003 — bilingual string table (engine/vlkit/i18n.py) and bilingual caveats (results.json caveats_vi).
Reviewed static strings only: no machine translation, and the two languages carry the same numbers."""
import re
import string

import pandas as pd
import pytest

VI_DIACRITICS = set("àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ")
NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _has_diacritic(s: str) -> bool:
    return bool(set(s.lower()) & VI_DIACRITICS)


def _placeholders(s: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


def _words(s: str) -> list[str]:
    return re.findall(r"[^\W\d_]{2,}", re.sub(r"\{[^}]*\}", " ", s))


def numbers(text: str, lang: str) -> list[float]:
    """Numbers in display text, parsed per language: EN 1,234.5 · VI 1.234,5."""
    out = []
    for tok in NUM.findall(text):
        if lang == "vi":
            tok = tok.replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?|\d+(,\d+)?", tok) else tok
        else:
            tok = tok.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", tok) else tok
        try:
            out.append(float(tok))
        except ValueError:
            continue
    return sorted(out)


def test_tables_have_identical_keys_and_no_empty_values():
    from vlkit.i18n import LANGS, STRINGS
    assert set(STRINGS) == set(LANGS) == {"en", "vi"}
    assert set(STRINGS["en"]) == set(STRINGS["vi"])
    for lang in LANGS:
        empty = [k for k, v in STRINGS[lang].items() if not v.strip()]
        assert not empty, f"{lang}: empty values {empty}"


def test_placeholders_match_across_languages():
    from vlkit.i18n import STRINGS
    for key, en in STRINGS["en"].items():
        assert _placeholders(en) == _placeholders(STRINGS["vi"][key]), key


def test_vi_sentences_carry_diacritics_and_technical_names_are_shared():
    from vlkit.i18n import STRINGS, TECHNICAL
    assert TECHNICAL <= set(STRINGS["en"])
    for key, en in STRINGS["en"].items():
        vi = STRINGS["vi"][key]
        if key in TECHNICAL:
            assert vi == en, f"{key}: technical names are not translated"
        elif len(_words(en)) >= 3:
            assert _has_diacritic(vi), f"{key}: VI value looks untranslated: {vi!r}"


def test_static_numbers_identical_across_languages():
    """Translations never change a number (e.g. 3×IQR, 5-fold, 0.05 ↔ 0,05)."""
    from vlkit.i18n import STRINGS
    for key, en in STRINGS["en"].items():
        assert numbers(en, "en") == numbers(STRINGS["vi"][key], "vi"), key


def test_t_formats_and_rejects_unknown_language():
    from vlkit import i18n
    assert i18n.t("vi", "kicker_question") != i18n.t("en", "kicker_question")
    assert "Ha Noi" in i18n.t("en", "target_line", target="Ha Noi")
    with pytest.raises(ValueError):
        i18n.t("fr", "kicker_question")
    assert i18n.langs_for("both") == ("en", "vi") and i18n.langs_for("vi") == ("vi",) and i18n.langs_for("en") == ("en",)
    with pytest.raises(ValueError):
        i18n.langs_for("de")


def test_text_field_falls_back_to_english_and_warns_once(capsys):
    from vlkit import i18n
    assert i18n.text_field({"title_en": "A", "title_vi": "B"}, "title", "vi") == "B"
    assert i18n.text_field({"title_en": "A"}, "title", "vi") == "A"
    assert i18n.text_field({"title_en": "A"}, "title", "vi") == "A"
    assert capsys.readouterr().out.count("missing VI text: title") == 1


def test_fmt_p_and_counts_per_language():
    from vlkit import fmt
    assert fmt.p(0.0004) == "p<0.001" and fmt.p(0.0004, "vi") == "p<0,001"
    assert fmt.p(0.0123) == "p=0.012" and fmt.p(0.0123, "vi") == "p=0,012"
    assert fmt.count(1234567) == "1,234,567" and fmt.count(1234567, "vi") == "1.234.567"
    assert fmt.count(None) == "—" and fmt.count("x", "vi") == "—"
    assert fmt.dec(84.9) == "84.9" and fmt.dec(84.9, "vi") == "84,9" and fmt.dec(None, "vi") == "—"


# ----------------------------------------------------------------------------- caveats (T303/T304)

def _issue_profile(n=100, miss=0.45, outliers=3.2):
    return {"issues": [{"severity": "medium", "column": "dien_tich", "issue": f"{miss:.0%} missing values",
                        "issue_vi": f"thiếu {miss:.0%} giá trị"}], "outlier_rows_pct": outliers}


@pytest.mark.parametrize("domain", ["property", "public_finance", "firm", "generic"])
def test_caveats_vi_parallel(domain):
    from vlkit import domains
    from vlkit.profile import caveats
    cav = caveats(_issue_profile(), domains.CAVEATS[domain], None, 150)
    assert set(cav) == {"en", "vi"}
    assert len(cav["en"]) == len(cav["vi"]) >= 4
    assert "causal" in cav["en"][0].lower() and "nhân quả" in cav["vi"][0].lower()
    for en, vi in zip(cav["en"], cav["vi"]):
        assert numbers(en, "en") == numbers(vi, "vi"), (en, vi)
        assert _has_diacritic(vi), vi


def test_domain_caveats_are_bilingual_pairs():
    from vlkit import domains
    for dom, items in domains.CAVEATS.items():
        for c in items:
            assert set(c) == {"en", "vi"} and c["en"].strip() and _has_diacritic(c["vi"]), (dom, c)


def test_profile_issues_carry_vi_text():
    from vlkit.profile import profile
    df = pd.DataFrame({"dien_tich": [None] * 7 + [-1.5, 30.0, 45.0], "k": ["a"] * 10})
    prof = profile(df, {"dien_tich": "numeric", "k": "constant"}, {}, {})
    assert prof["issues"]
    for i in prof["issues"]:
        assert i["issue_vi"] and _has_diacritic(i["issue_vi"])
        assert numbers(i["issue"], "en") == numbers(i["issue_vi"], "vi")


def test_pipeline_writes_caveats_vi(tmp_path):
    from test_pipeline_smoke import _messy_property_csv

    from vlkit import pipeline
    res = pipeline.run(_messy_property_csv(tmp_path / "bds.csv"), out_root=tmp_path, name="cav", reports=False)
    assert len(res["caveats_vi"]) == len(res["caveats"])
    for en, vi in zip(res["caveats"], res["caveats_vi"]):
        assert numbers(en, "en") == numbers(vi, "vi")
