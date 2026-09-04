import re

_FENCED_CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_BULLET = re.compile(r"^[ \t]*[\*\-\+][ \t]+", re.MULTILINE)
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.*?)[ \t]*#*[ \t]*$", re.MULTILINE)
_ITALIC = re.compile(r"(\*|_)(.+?)\1")
_TRAILING_LINE_WHITESPACE = re.compile(r"[ \t]+\n")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def strip_markdown_to_plain_text(text):
    if not text:
        return ""

    result = text
    result = _FENCED_CODE_BLOCK.sub(lambda m: m.group(1).strip(), result)
    result = _INLINE_CODE.sub(lambda m: m.group(1), result)
    result = _MD_LINK.sub(lambda m: m.group(1), result)
    result = _BOLD.sub(lambda m: m.group(2), result)
    result = _BULLET.sub("- ", result)
    result = _HEADING.sub(lambda m: m.group(1), result)
    result = _ITALIC.sub(lambda m: m.group(2), result)
    result = _TRAILING_LINE_WHITESPACE.sub("\n", result)
    result = _EXCESS_BLANK_LINES.sub("\n\n", result)
    return result.strip()
