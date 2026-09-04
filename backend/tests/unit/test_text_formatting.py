from app.services.text_formatting import strip_markdown_to_plain_text


class TestPlainTextPassesThrough:
    def test_plain_sentence_is_unchanged(self):
        text = "Water your tomatoes deeply once a week."
        assert strip_markdown_to_plain_text(text) == text

    def test_punctuation_is_preserved(self):
        text = "Is this normal? Yes! Check again in 3-4 days, then decide."
        assert strip_markdown_to_plain_text(text) == text


class TestBoldIsStripped:
    def test_double_asterisk_bold(self):
        result = strip_markdown_to_plain_text("Water deeply **once a week**, more in sandy soil.")
        assert result == "Water deeply once a week, more in sandy soil."
        assert "*" not in result

    def test_double_underscore_bold(self):
        result = strip_markdown_to_plain_text("Use __certified seed__ only.")
        assert result == "Use certified seed only."
        assert "_" not in result

    def test_multiple_bold_spans(self):
        result = strip_markdown_to_plain_text("**Frequency:** daily. **Method:** drip irrigation.")
        assert result == "Frequency: daily. Method: drip irrigation."


class TestItalicIsStripped:
    def test_single_asterisk_italic(self):
        result = strip_markdown_to_plain_text("This is *especially* important during flowering.")
        assert result == "This is especially important during flowering."

    def test_single_underscore_italic(self):
        result = strip_markdown_to_plain_text("Check for _fall armyworm_ on the leaves.")
        assert result == "Check for fall armyworm on the leaves."


class TestHeadingsBecomeReadableText:
    def test_h1_heading(self):
        result = strip_markdown_to_plain_text("# Soil Preparation\nClear the field first.")
        assert result == "Soil Preparation\nClear the field first."

    def test_h3_heading(self):
        result = strip_markdown_to_plain_text("### Fertilizer Schedule\nApply at planting.")
        assert result == "Fertilizer Schedule\nApply at planting."
        assert "#" not in result


class TestBulletsBecomeReadableLines:
    def test_asterisk_bullets(self):
        result = strip_markdown_to_plain_text("* Water in the morning\n* Avoid wetting leaves")
        assert result == "- Water in the morning\n- Avoid wetting leaves"

    def test_dash_bullets(self):
        result = strip_markdown_to_plain_text("- Weed regularly\n- Mulch around the base")
        assert result == "- Weed regularly\n- Mulch around the base"

    def test_plus_bullets(self):
        result = strip_markdown_to_plain_text("+ Inspect daily\n+ Remove infected leaves")
        assert result == "- Inspect daily\n- Remove infected leaves"

    def test_bullet_with_bold_label(self):
        result = strip_markdown_to_plain_text("* **Frequency:** every 2-3 days")
        assert result == "- Frequency: every 2-3 days"

    def test_italic_word_at_line_start_is_not_mistaken_for_a_bullet(self):
        result = strip_markdown_to_plain_text("*Urgent* — treat this week.")
        assert result == "Urgent — treat this week."


class TestNumberedListsRemainReadable:
    def test_numbered_list_with_bold_labels(self):
        text = (
            "1. **Check pests:** look under leaves.\n"
            "2. **Apply Bt:** for armyworm larvae.\n"
            "3. **Remove weeds:** they hide pests."
        )
        expected = (
            "1. Check pests: look under leaves.\n"
            "2. Apply Bt: for armyworm larvae.\n"
            "3. Remove weeds: they hide pests."
        )
        assert strip_markdown_to_plain_text(text) == expected


class TestInlineCodeIsReadable:
    def test_inline_code_keeps_content_drops_backticks(self):
        result = strip_markdown_to_plain_text("Apply `NPK 17:17:17` at planting.")
        assert result == "Apply NPK 17:17:17 at planting."
        assert "`" not in result


class TestFencedCodeBlocksDoNotLeakMarkdownFences:
    def test_fenced_block_content_kept_fences_removed(self):
        text = "Use this ratio:\n```\nNPK = 15:15:15\n```\nApply as directed."
        result = strip_markdown_to_plain_text(text)
        assert "```" not in result
        assert "NPK = 15:15:15" in result

    def test_fenced_block_with_language_tag(self):
        text = "```text\nWater: 2L per plant\n```"
        result = strip_markdown_to_plain_text(text)
        assert "```" not in result
        assert result == "Water: 2L per plant"


class TestMarkdownLinksPreserveUsefulLinkText:
    def test_link_keeps_text_drops_raw_url(self):
        result = strip_markdown_to_plain_text(
            "Consult a [verified agricultural expert](https://agriconnect.example/experts) before spraying."
        )
        assert result == "Consult a verified agricultural expert before spraying."
        assert "https://" not in result
        assert "(" not in result and ")" not in result


class TestBlankLineNormalization:
    def test_multiple_blank_lines_collapse_to_one(self):
        result = strip_markdown_to_plain_text("First paragraph.\n\n\n\n\nSecond paragraph.")
        assert result == "First paragraph.\n\nSecond paragraph."

    def test_single_blank_line_is_preserved(self):
        result = strip_markdown_to_plain_text("First paragraph.\n\nSecond paragraph.")
        assert result == "First paragraph.\n\nSecond paragraph."


class TestEmptyAndNoneInput:
    def test_empty_string_returns_empty_string(self):
        assert strip_markdown_to_plain_text("") == ""

    def test_whitespace_only_returns_empty_string(self):
        assert strip_markdown_to_plain_text("   \n\n  ") == ""

    def test_none_returns_empty_string(self):
        assert strip_markdown_to_plain_text(None) == ""


class TestUnicodeAndKiswahiliArePreserved:
    def test_kiswahili_bold_and_bullets(self):
        text = (
            "**Muhimu:** fuata hatua hizi:\n"
            "* Angalia wadudu kwenye majani\n"
            "* Ondoa magugu shambani"
        )
        expected = (
            "Muhimu: fuata hatua hizi:\n"
            "- Angalia wadudu kwenye majani\n"
            "- Ondoa magugu shambani"
        )
        assert strip_markdown_to_plain_text(text) == expected

    def test_emoji_and_accents_are_preserved(self):
        text = "🌱 **Karibu** AgriConnect! Café-style shading works well, très bien."
        result = strip_markdown_to_plain_text(text)
        assert "🌱" in result
        assert "Café-style" in result
        assert "très bien" in result
        assert "Karibu" in result


class TestMixedMarkdownProducesCleanOutput:
    def test_realistic_multi_crop_answer(self):
        text = (
            "For a 2-acre plot, prioritize a **maize-bean intercrop** on 1.5 acres.\n\n"
            "### Soil Preparation\n"
            "*   **Clear & Till:** Remove debris and plow 6-8 inches deep.\n"
            "*   **Layout:** Plant maize and beans together.\n\n"
            "\n\n"
            "See [AgriConnect experts](https://agriconnect.example/experts) for `NPK 15:15:15` dosing.\n"
            "\n\n\n"
            "1. Water deeply.\n"
            "2. Mulch the base."
        )
        result = strip_markdown_to_plain_text(text)

        assert "**" not in result
        assert "*" not in result
        assert "#" not in result
        assert "`" not in result
        assert "https://" not in result
        assert "\n\n\n" not in result

        assert "maize-bean intercrop" in result
        assert "Soil Preparation" in result
        assert "- Clear & Till: Remove debris and plow 6-8 inches deep." in result
        assert "AgriConnect experts" in result
        assert "NPK 15:15:15" in result
        assert "1. Water deeply." in result
        assert "2. Mulch the base." in result


class TestDeterminism:
    def test_same_input_always_produces_same_output(self):
        text = "**Bold**, *italic*, # Heading, * bullet, `code`, [link](https://x.example)"
        results = {strip_markdown_to_plain_text(text) for _ in range(5)}
        assert len(results) == 1

    def test_running_twice_on_already_clean_output_is_stable(self):
        text = "**Bold** and *italic* and # Heading"
        once = strip_markdown_to_plain_text(text)
        twice = strip_markdown_to_plain_text(once)
        assert once == twice
