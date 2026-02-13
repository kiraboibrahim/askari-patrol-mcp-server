import pytest
from common.whatsapp import convert_markdown_to_whatsapp


class TestBasicFormatting:
    """Test basic inline formatting conversions."""

    def test_bold_conversion(self):
        """Test **bold** converts to *bold*"""
        md = "This is **bold text**"
        result = convert_markdown_to_whatsapp(md)
        assert "*bold text*" in result
        assert "**" not in result

    def test_italic_conversion(self):
        """Test *italic* converts to _italic_"""
        md = "This is *italic text*"
        result = convert_markdown_to_whatsapp(md)
        assert "_italic text_" in result

    def test_bold_italic_conversion(self):
        """Test ***bold italic*** converts to *_bold italic_*"""
        md = "This is ***bold and italic***"
        result = convert_markdown_to_whatsapp(md)
        assert "*_bold and italic_*" in result or "_*bold and italic*_" in result

    def test_strikethrough_conversion(self):
        """Test ~~strikethrough~~ converts to ~strikethrough~"""
        md = "This is ~~strikethrough~~"
        result = convert_markdown_to_whatsapp(md)
        assert "~strikethrough~" in result
        assert "~~" not in result

    def test_inline_code_preserved(self):
        """Test `code` is preserved as-is"""
        md = "This is `inline code`"
        result = convert_markdown_to_whatsapp(md)
        assert "`inline code`" in result

    def test_combined_inline_formatting(self):
        """Test multiple formatting types in one line"""
        md = "**bold** and *italic* and ~~strike~~ and `code`"
        result = convert_markdown_to_whatsapp(md)
        assert "*bold*" in result
        assert "_italic_" in result
        assert "~strike~" in result
        assert "`code`" in result


class TestHeadings:
    """Test heading conversions."""

    def test_h1_heading_uppercase_bold(self):
        """Test # H1 converts to *H1* in uppercase"""
        md = "# Hello World"
        result = convert_markdown_to_whatsapp(md)
        assert "*HELLO WORLD*" in result or "*Hello World*" in result

    def test_h2_heading_bold(self):
        """Test ## H2 converts to *H2*"""
        md = "## Second Level"
        result = convert_markdown_to_whatsapp(md)
        assert "*Second Level*" in result or "*SECOND LEVEL*" in result

    def test_h3_heading_bold(self):
        """Test ### H3 converts to *H3*"""
        md = "### Third Level"
        result = convert_markdown_to_whatsapp(md)
        assert "*Third Level*" in result

    def test_multiple_headings(self):
        """Test document with multiple heading levels"""
        md = """
# Main Title
## Subtitle
### Section
"""
        result = convert_markdown_to_whatsapp(md)
        # All should be bold
        assert result.count("*") >= 6  # At least 3 headings with * on each side

    def test_heading_with_formatting(self):
        """Test heading containing inline formatting"""
        md = "## Important **Point**"
        result = convert_markdown_to_whatsapp(md)
        assert "*Important" in result
        assert "Point*" in result


class TestLists:
    """Test list conversions."""

    def test_unordered_list_basic(self):
        """Test unordered list converts to bullet points"""
        md = """
- Item 1
- Item 2
- Item 3
"""
        result = convert_markdown_to_whatsapp(md)
        assert "• Item 1" in result
        assert "• Item 2" in result
        assert "• Item 3" in result

    def test_ordered_list_basic(self):
        """Test ordered list preserves numbering"""
        md = """
1. First
2. Second
3. Third
"""
        result = convert_markdown_to_whatsapp(md)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    def test_nested_unordered_list(self):
        """Test nested unordered lists with indentation"""
        md = """
- Parent 1
  - Child 1
  - Child 2
- Parent 2
"""
        result = convert_markdown_to_whatsapp(md)
        assert "• Parent 1" in result
        assert "• Child 1" in result or "  • Child 1" in result
        assert "• Parent 2" in result

    def test_nested_ordered_list(self):
        """Test nested ordered lists"""
        md = """
1. First level
   1. Second level
   2. Second level
2. First level
"""
        result = convert_markdown_to_whatsapp(md)
        assert "1. First level" in result
        assert "2. First level" in result

    def test_list_with_formatting(self):
        """Test list items with inline formatting"""
        md = """
- **Bold item**
- *Italic item*
- `Code item`
"""
        result = convert_markdown_to_whatsapp(md)
        assert "• *Bold item*" in result
        assert "• _Italic item_" in result
        assert "• `Code item`" in result

    def test_mixed_lists(self):
        """Test document with both ordered and unordered lists"""
        md = """
Unordered:
- Apple
- Banana

Ordered:
1. First
2. Second
"""
        result = convert_markdown_to_whatsapp(md)
        assert "• Apple" in result
        assert "1. First" in result


class TestCodeBlocks:
    """Test code block conversions."""

    def test_fenced_code_block_no_language(self):
        """Test ``` code block without language"""
        md = """
```
def hello():
    print("world")
```
"""
        result = convert_markdown_to_whatsapp(md)
        assert "```" in result
        assert "def hello():" in result
        assert 'print("world")' in result

    def test_fenced_code_block_with_language(self):
        """Test ```python code block with language"""
        md = """
```python
def hello():
    return "world"
```
"""
        result = convert_markdown_to_whatsapp(md)
        assert "```python" in result or "```" in result
        assert "def hello():" in result

    def test_code_block_preserves_indentation(self):
        """Test code block preserves indentation"""
        md = """
```
if True:
    nested()
        deep()
```
"""
        result = convert_markdown_to_whatsapp(md)
        assert "    nested()" in result or "nested()" in result

    def test_multiple_code_blocks(self):
        """Test document with multiple code blocks"""
        md = """
First block:
```
code1
```

Second block:
```
code2
```
"""
        result = convert_markdown_to_whatsapp(md)
        assert "code1" in result
        assert "code2" in result
        assert result.count("```") >= 4  # At least 2 blocks


class TestBlockquotes:
    """Test blockquote conversions."""

    def test_simple_blockquote(self):
        """Test > quote converts with > prefix"""
        md = "> This is a quote"
        result = convert_markdown_to_whatsapp(md)
        assert "> This is a quote" in result

    def test_multiline_blockquote(self):
        """Test multi-line blockquote"""
        md = """
> First line
> Second line
> Third line
"""
        result = convert_markdown_to_whatsapp(md)
        assert "> First line" in result
        assert "> Second line" in result
        assert "> Third line" in result

    def test_blockquote_with_formatting(self):
        """Test blockquote containing formatting"""
        md = "> This is **important** and *emphasized*"
        result = convert_markdown_to_whatsapp(md)
        assert ">" in result
        assert "*important*" in result
        assert "_emphasized_" in result

    def test_nested_blockquote(self):
        """Test nested blockquotes"""
        md = """
> Level 1
>> Level 2
"""
        result = convert_markdown_to_whatsapp(md)
        assert "> Level 1" in result


class TestLinks:
    """Test link conversions."""

    def test_inline_link(self):
        """Test [text](url) format"""
        md = "[Click here](https://example.com)"
        result = convert_markdown_to_whatsapp(md)
        assert "Click here" in result
        assert "https://example.com" in result
        assert "[" not in result or "(" in result  # Either converted or preserved

    def test_link_same_as_text(self):
        """Test link where text equals URL"""
        md = "[https://example.com](https://example.com)"
        result = convert_markdown_to_whatsapp(md)
        assert "https://example.com" in result
        # Should not duplicate the URL

    def test_autolink(self):
        """Test automatic link detection"""
        md = "Visit https://example.com for info"
        result = convert_markdown_to_whatsapp(md)
        assert "https://example.com" in result

    def test_multiple_links(self):
        """Test multiple links in text"""
        md = "Check [Site A](https://a.com) and [Site B](https://b.com)"
        result = convert_markdown_to_whatsapp(md)
        assert "Site A" in result
        assert "Site B" in result
        assert "https://a.com" in result
        assert "https://b.com" in result


class TestImages:
    """Test image conversions."""

    def test_image_with_alt_text(self):
        """Test ![alt](url) format"""
        md = "![Logo](https://example.com/logo.png)"
        result = convert_markdown_to_whatsapp(md)
        assert "Logo" in result or "Image" in result
        assert "https://example.com/logo.png" in result

    def test_image_without_alt_text(self):
        """Test image with empty alt text"""
        md = "![](https://example.com/image.jpg)"
        result = convert_markdown_to_whatsapp(md)
        assert "https://example.com/image.jpg" in result

    def test_multiple_images(self):
        """Test multiple images"""
        md = """
![Image 1](https://example.com/1.jpg)
![Image 2](https://example.com/2.jpg)
"""
        result = convert_markdown_to_whatsapp(md)
        assert "https://example.com/1.jpg" in result
        assert "https://example.com/2.jpg" in result


class TestTables:
    """Test table conversions."""

    def test_simple_table(self):
        """Test basic 2-column table"""
        md = """
| Goal | Status |
|------|--------|
| Test | OK |
"""
        result = convert_markdown_to_whatsapp(md)

        # Should contain headers
        assert "Goal" in result
        assert "Status" in result

        # Should contain data
        assert "Test" in result
        assert "OK" in result

        # Should have separator
        assert "─" in result or "|" in result

        # Should NOT contain markdown separator
        assert "---" not in result or result.count("---") < md.count("---")

    def test_table_multiple_rows(self):
        """Test table with multiple data rows"""
        md = """
| Item | Quantity | Price |
|------|----------|-------|
| Apple | 5 | $2.50 |
| Banana | 10 | $1.00 |
| Orange | 3 | $3.00 |
"""
        result = convert_markdown_to_whatsapp(md)

        # Headers
        assert "Item" in result
        assert "Quantity" in result
        assert "Price" in result

        # All data rows
        assert "Apple" in result
        assert "5" in result
        assert "$2.50" in result
        assert "Banana" in result
        assert "10" in result
        assert "$1.00" in result
        assert "Orange" in result
        assert "3" in result
        assert "$3.00" in result

    def test_table_with_formatting(self):
        """Test table cells containing markdown formatting"""
        md = """
| Feature | Status | Notes |
|---------|--------|-------|
| Login | **Complete** | Works well |
| Signup | *In Progress* | Backend done |
| Profile | `Not Started` | Planned |
"""
        result = convert_markdown_to_whatsapp(md)

        assert "Feature" in result
        assert "Login" in result
        assert "*Complete*" in result  # Bold
        assert "_In Progress_" in result  # Italic
        assert "`Not Started`" in result  # Code

    def test_table_with_empty_cells(self):
        """Test table with empty cells"""
        md = """
| Name | Email | Phone |
|------|-------|-------|
| Alice | alice@example.com | 555-0001 |
| Bob | | 555-0002 |
| Carol | carol@example.com | |
"""
        result = convert_markdown_to_whatsapp(md)

        # All data should be present
        assert "Alice" in result
        assert "alice@example.com" in result
        assert "555-0001" in result
        assert "Bob" in result
        assert "555-0002" in result
        assert "Carol" in result
        assert "carol@example.com" in result

    def test_table_alignment(self):
        """Test table with column alignment (should be ignored)"""
        md = """
| Left | Center | Right |
|:-----|:------:|------:|
| L1 | C1 | R1 |
"""
        result = convert_markdown_to_whatsapp(md)

        assert "Left" in result
        assert "Center" in result
        assert "Right" in result
        assert "L1" in result
        assert "C1" in result
        assert "R1" in result

    def test_table_single_column(self):
        """Test table with single column"""
        md = """
| Todo |
|------|
| Task 1 |
| Task 2 |
"""
        result = convert_markdown_to_whatsapp(md)

        assert "Todo" in result
        assert "Task 1" in result
        assert "Task 2" in result

    def test_table_wide(self):
        """Test table with many columns"""
        md = """
| A | B | C | D | E | F |
|---|---|---|---|---|---|
| 1 | 2 | 3 | 4 | 5 | 6 |
"""
        result = convert_markdown_to_whatsapp(md)

        for letter in ["A", "B", "C", "D", "E", "F"]:
            assert letter in result
        for num in ["1", "2", "3", "4", "5", "6"]:
            assert num in result

    def test_table_preserves_order(self):
        """Test that table row order is preserved"""
        md = """
| Number | Letter |
|--------|--------|
| 1 | A |
| 2 | B |
| 3 | C |
"""
        result = convert_markdown_to_whatsapp(md)

        # Find positions
        pos_1 = result.find("1")
        pos_2 = result.find("2")
        pos_3 = result.find("3")

        # Verify order (if all found)
        assert pos_1 < pos_2 < pos_3

    def test_table_card_format(self):
        """Test the specific card-style layout for tables"""
        md = """
| Name | Role |
|------|------|
| Alice | Admin |
| Bob | User |
"""
        result = convert_markdown_to_whatsapp(md)

        # Check for card structure
        lines = result.strip().split("\n")

        # Should have dividers
        assert "────────────────────" in result

        # Check specific line structure for the first card
        assert "*Name*: Alice" in lines
        assert "*Role*: Admin" in lines

        # Check specific line structure for the second card
        assert "*Name*: Bob" in lines
        assert "*Role*: User" in lines

        # Verify that each field is on its own line
        name_idx = next(i for i, line in enumerate(lines) if "*Name*: Alice" in line)
        role_idx = next(i for i, line in enumerate(lines) if "*Role*: Admin" in line)
        assert role_idx == name_idx + 1


class TestHorizontalRules:
    """Test horizontal rule conversions."""

    def test_triple_dash(self):
        """Test --- converts to separator"""
        md = "Text before\n\n---\n\nText after"
        result = convert_markdown_to_whatsapp(md)
        assert "Text before" in result
        assert "Text after" in result
        assert "─" in result or "---" not in result

    def test_triple_asterisk(self):
        """Test *** converts to separator"""
        md = "Text before\n\n***\n\nText after"
        result = convert_markdown_to_whatsapp(md)
        assert "─" in result or "***" not in result

    def test_triple_underscore(self):
        """Test ___ converts to separator"""
        md = "Text before\n\n___\n\nText after"
        result = convert_markdown_to_whatsapp(md)
        assert "─" in result or "___" not in result


class TestComplexDocuments:
    """Test complex documents with mixed elements."""

    def test_full_document(self):
        """Test comprehensive document with all features"""
        md = """
# Project Report

## Executive Summary

This report covers **Q1 2024** performance.

### Key Metrics

| Metric | Value | Change |
|--------|-------|--------|
| Revenue | $100K | +15% |
| Users | 1000 | +25% |

### Action Items

1. **Complete** user authentication
2. *Review* analytics dashboard
3. ~~Fix~~ old bugs (done)

### Notes

> All features must pass QA before release

For more info, see our [documentation](https://docs.example.com).

Code example:

```python
def calculate_growth(current, previous):
    return (current - previous) / previous * 100
```

---

**Report Date:** 2024-01-15
"""
        result = convert_markdown_to_whatsapp(md)

        # Check major elements are present
        assert "PROJECT REPORT" in result or "Project Report" in result
        assert "Executive Summary" in result
        assert "Revenue" in result
        assert "$100K" in result
        assert "1. *Complete*" in result or "*Complete*" in result
        assert "> All features" in result
        assert "documentation" in result
        assert "https://docs.example.com" in result
        assert "def calculate_growth" in result
        assert "Report Date" in result

    def test_nested_structures(self):
        """Test nested lists and formatting"""
        md = """
- **Parent 1**
  - Child with *italic*
  - Child with `code`
- **Parent 2**
"""
        result = convert_markdown_to_whatsapp(md)

        assert "• *Parent 1*" in result or "*Parent 1*" in result
        assert "_italic_" in result
        assert "`code`" in result

    def test_formatting_in_different_contexts(self):
        """Test same formatting in different block types"""
        md = """
# **Bold** Heading

**Bold** in paragraph

- **Bold** in list

> **Bold** in quote

| **Bold** | In Table |
|----------|----------|
| Cell | **Bold** |
"""
        result = convert_markdown_to_whatsapp(md)

        # Bold should work in all contexts
        assert result.count("*") >= 8  # Multiple bold instances


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Test empty markdown input"""
        md = ""
        result = convert_markdown_to_whatsapp(md)
        assert result is not None
        assert isinstance(result, str)

    def test_whitespace_only(self):
        """Test whitespace-only input"""
        md = "   \n\n   "
        result = convert_markdown_to_whatsapp(md)
        assert result is not None

    def test_single_paragraph(self):
        """Test single paragraph"""
        md = "Just a simple paragraph."
        result = convert_markdown_to_whatsapp(md)
        assert "Just a simple paragraph" in result

    def test_no_markdown_formatting(self):
        """Test plain text without markdown"""
        md = "This is plain text with no formatting at all."
        result = convert_markdown_to_whatsapp(md)
        assert "This is plain text" in result

    def test_escaped_characters(self):
        """Test escaped markdown characters"""
        md = r"This has \*escaped\* asterisks"
        result = convert_markdown_to_whatsapp(md)
        # Escaped characters should appear as literals
        assert result is not None

    def test_malformed_markdown(self):
        """Test malformed markdown doesn't crash"""
        md = "**Bold without closing\n\n*Italic without closing"
        result = convert_markdown_to_whatsapp(md)
        assert result is not None
        assert isinstance(result, str)

    def test_unicode_characters(self):
        """Test unicode characters are preserved"""
        md = "Hello 👋 World 🌍 with **émojis** and **accénts**"
        result = convert_markdown_to_whatsapp(md)
        assert "👋" in result
        assert "🌍" in result
        assert "émojis" in result or "mojis" in result

    def test_very_long_document(self):
        """Test handling of large documents"""
        md = "# Heading\n\n" + ("Paragraph text. " * 100)
        result = convert_markdown_to_whatsapp(md)
        assert "Paragraph text" in result
        assert len(result) > 0


class TestWhatsAppSpecificFeatures:
    """Test WhatsApp-specific formatting requirements."""

    def test_no_double_asterisks_in_output(self):
        """Ensure ** is converted to single *"""
        md = "This is **bold text**"
        result = convert_markdown_to_whatsapp(md)
        assert "**" not in result
        assert "*bold text*" in result

    def test_no_double_tildes_in_output(self):
        """Ensure ~~ is converted to single ~"""
        md = "This is ~~strikethrough~~"
        result = convert_markdown_to_whatsapp(md)
        assert "~~" not in result
        assert "~strikethrough~" in result

    def test_markdown_syntax_removed(self):
        """Ensure markdown-specific syntax is removed or converted"""
        md = "# Heading\n\n**Bold** and *italic*\n\n- List item"
        result = convert_markdown_to_whatsapp(md)

        # Should not contain markdown syntax
        assert "**" not in result
        assert not result.strip().startswith("#")

    def test_preserves_whatsapp_compatible_syntax(self):
        """Test that WhatsApp-compatible syntax is preserved"""
        md = "Use `code` for commands"
        result = convert_markdown_to_whatsapp(md)
        assert "`code`" in result  # Backticks preserved


# Pytest fixtures for common test data
@pytest.fixture
def simple_markdown():
    """Simple markdown document for testing"""
    return """
# Title

This is **bold** and *italic*.

- Item 1
- Item 2
"""


@pytest.fixture
def complex_markdown():
    """Complex markdown document for testing"""
    return """
# Main Title

## Section 1

Here's some **bold** and *italic* text.

### Subsection

1. First item
2. Second item

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

> Important quote

```python
def hello():
    return "world"
```

---

End of document.
"""


class TestWithFixtures:
    """Tests using pytest fixtures."""

    def test_simple_markdown_conversion(self, simple_markdown):
        """Test simple markdown converts correctly"""
        result = convert_markdown_to_whatsapp(simple_markdown)
        assert "*TITLE*" in result or "*Title*" in result
        assert "*bold*" in result
        assert "_italic_" in result
        assert "• Item 1" in result

    def test_complex_markdown_conversion(self, complex_markdown):
        """Test complex markdown converts correctly"""
        result = convert_markdown_to_whatsapp(complex_markdown)
        assert "Main Title" in result
        assert "Section 1" in result
        assert "*bold*" in result
        assert "1. First item" in result
        assert "Header 1" in result
        assert "> Important quote" in result
        assert "def hello():" in result


# Parametrized tests for repetitive cases
@pytest.mark.parametrize(
    "md,expected",
    [
        ("**bold**", "*bold*"),
        ("*italic*", "_italic_"),
        ("~~strike~~", "~strike~"),
        ("`code`", "`code`"),
    ],
)
def test_inline_formatting_parametrized(md, expected):
    """Parametrized test for inline formatting"""
    result = convert_markdown_to_whatsapp(md)
    assert expected in result


@pytest.mark.parametrize(
    "heading_level,text",
    [
        ("# ", "Level 1"),
        ("## ", "Level 2"),
        ("### ", "Level 3"),
        ("#### ", "Level 4"),
    ],
)
def test_headings_parametrized(heading_level, text):
    """Parametrized test for different heading levels"""
    md = heading_level + text
    result = convert_markdown_to_whatsapp(md)
    assert text.upper() in result or text in result
    assert "*" in result  # Should be bold


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
