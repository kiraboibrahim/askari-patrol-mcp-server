"""
Comprehensive Markdown to WhatsApp Formatter
Handles all standard Markdown elements and converts them to WhatsApp-compatible format

WhatsApp Formatting Support:
- Bold: *text*
- Italic: _text_
- Strikethrough: ~text~
- Monospace: `text`
- Code blocks: ```text```
"""

import os
import re
from typing import Any

import httpx
from mistletoe import Document
from mistletoe.base_renderer import BaseRenderer


class WhatsAppRenderer(BaseRenderer):
    """
    Custom renderer that converts all standard Markdown to WhatsApp formatting.
    Handles: headings, paragraphs, lists, code blocks, tables, blockquotes,
    horizontal rules, images, links, and all inline formatting.
    """

    def __init__(self):
        super().__init__()
        self.list_depth = 0

    # Block-level elements

    def render_document(self, token):
        """Render the entire document"""
        content = self.render_inner(token)
        # Clean up excessive newlines at the end
        return content.rstrip() + "\n"

    def render_heading(self, token):
        """
        Convert headings to bold text with appropriate spacing
        # H1 -> *H1*
        ## H2 -> *H2*
        """
        content = self.render_inner(token)

        # Add visual hierarchy with newlines
        return f"\n*{content}*\n\n"

    def render_paragraph(self, token):
        """Render paragraphs with proper spacing"""
        content = self.render_inner(token)
        return f"{content}\n\n"

    def render_block_code(self, token):
        """
        Render code blocks with triple backticks
        Preserves language hint if present
        """
        # token.children[0] is RawText containing the code
        code = token.children[0].content if token.children else ""
        language = getattr(token, "language", "") or ""

        if language:
            return f"```{language}\n{code}```\n\n"
        else:
            return f"```\n{code}```\n\n"

    def render_list(self, token):
        """
        Render ordered and unordered lists
        Handles nested lists with proper indentation
        """
        self.list_depth += 1
        result = []

        # Check if ordered or unordered - ordered lists have a non-None start attribute
        start_num = getattr(token, "start", None)
        is_ordered = start_num is not None
        if not is_ordered:
            start_num = 1  # Default for safety

        for i, item in enumerate(token.children):
            if is_ordered:
                # Ordered list: use numbers
                result.append(
                    self.render_list_item(item, i + start_num, is_ordered=True)
                )
            else:
                # Unordered list: use bullets
                result.append(self.render_list_item(item, is_ordered=False))

        self.list_depth -= 1

        output = "".join(result)
        # Add spacing after list if not nested
        if self.list_depth == 0:
            output += "\n"
        return output

    def render_list_item(self, token, number=None, is_ordered=False):
        """Render individual list items with proper indentation"""
        content = self.render_inner(token).strip()
        indent = "  " * (self.list_depth - 1)

        if is_ordered:
            return f"{indent}{number}. {content}\n"
        else:
            return f"{indent}• {content}\n"

    def render_quote(self, token):
        """
        Render blockquotes with > prefix
        WhatsApp doesn't have native blockquote, so we use > prefix
        """
        # Render all children and join them
        content_parts = []
        for child in token.children:
            rendered = self.render(child)
            if rendered:
                content_parts.append(rendered)

        content = "".join(content_parts).strip()

        # Add > to each line
        lines = content.split("\n")
        quoted_lines = [f"> {line}" for line in lines if line.strip()]
        return "\n".join(quoted_lines) + "\n\n"

    def render_thematic_break(self, token):
        """
        Render horizontal rules
        WhatsApp doesn't support HR, so use a visual separator
        """
        return "─────────────────\n\n"

    def render_table(self, token):
        """
        Render tables as a series of "cards" for better readability on WhatsApp
        Each row becomes a card with labeled fields.
        """
        result = []
        headers = []

        # Collect headers
        if hasattr(token, "header") and token.header:
            for cell in token.header.children:
                headers.append(self.render(cell).strip())

        # Render rows (body)
        if hasattr(token, "children"):
            for _, row in enumerate(token.children):
                # Add divider between cards
                result.append("─" * 20)

                row_cells = list(row.children)
                for j, cell in enumerate(row_cells):
                    cell_content = self.render(cell).strip()
                    header_label = headers[j] if j < len(headers) else f"Field {j+1}"
                    result.append(f"*{header_label}*: {cell_content}")

            # Final divider
            if result:
                result.append("─" * 20)

        return "\n".join(result) + "\n\n" if result else "\n"

    def render_table_row(self, token):
        """Render table row (handled by render_table)"""
        return ""

    def render_table_cell(self, token):
        """Render table cell (handled by render_table)"""
        return self.render_inner(token)

    # Inline elements

    def render_strong(self, token):
        """
        Render bold text
        Standard MD: **text** or __text__
        WhatsApp: *text*
        """
        content = self.render_inner(token)
        return f"*{content}*"

    def render_emphasis(self, token):
        """
        Render italic text
        Standard MD: *text* or _text_
        WhatsApp: _text_
        """
        content = self.render_inner(token)
        return f"_{content}_"

    def render_inline_code(self, token):
        """
        Render inline code
        Both standard MD and WhatsApp use: `text`
        """
        return f"`{token.children[0].content}`"

    def render_strikethrough(self, token):
        """
        Render strikethrough text
        Standard MD: ~~text~~
        WhatsApp: ~text~
        """
        content = self.render_inner(token)
        return f"~{content}~"

    def render_link(self, token):
        """
        Render links
        WhatsApp auto-detects URLs but doesn't support MD link syntax
        Show as: text (url) or just url if text == url
        """
        content = self.render_inner(token)
        url = token.target

        # If link text is the same as URL, just show URL
        if content == url:
            return url
        else:
            return f"{content} ({url})"

    def render_auto_link(self, token):
        """Render auto-detected links"""
        return token.target

    def render_image(self, token):
        """
        Render images
        WhatsApp doesn't support inline images in text
        Show as: [Image: alt_text] url
        """
        alt_text = self.render_inner(token) or "Image"
        # Image tokens use 'src' attribute for the URL
        url = getattr(token, "src", getattr(token, "target", ""))
        return f"[{alt_text}] {url}"

    def render_escape_sequence(self, token):
        """Render escaped characters"""
        return token.children[0].content

    def render_raw_text(self, token):
        """Render plain text"""
        return token.content

    def render_line_break(self, token):
        """Render line breaks"""
        # Soft break becomes newline to preserve layout in WhatsApp
        return "\n"

    def render_html_span(self, token):
        """Strip HTML tags - WhatsApp doesn't support HTML"""
        return self.render_inner(token)

    def render_html_block(self, token):
        """Strip HTML blocks - WhatsApp doesn't support HTML"""
        return "\n"


def convert_markdown_to_whatsapp(markdown_text: str) -> str:
    """
    Convert standard Markdown to WhatsApp-compatible format

    Args:
        markdown_text: Standard markdown string

    Returns:
        WhatsApp-formatted string

    Example:
        >>> md = "# Hello\\n\\nThis is **bold** and *italic*"
        >>> wa = convert_markdown_to_whatsapp(md)
        >>> print(wa)
    """
    with WhatsAppRenderer() as renderer:
        doc = Document(markdown_text)
        return renderer.render(doc)


def send_typing_indicator(
    message_id: str,
    channel: str = "whatsapp",
    account_sid: str | None = None,
    auth_token: str | None = None,
) -> dict[Any, Any]:
    """
    Send a typing indicator via Twilio API.

    Args:
        message_id: The Twilio message SID to show typing for
        channel: The messaging channel (default: "whatsapp")
        account_sid: Twilio Account SID (defaults to TWILIO_ACCOUNT_SID env var)
        auth_token: Twilio Auth Token (defaults to TWILIO_AUTH_TOKEN env var)

    Returns:
        Dict containing the API response

    Raises:
        httpx.HTTPStatusError: If the request fails
    """
    account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise ValueError(
            "Twilio credentials must be provided or set in environment variables"
        )

    data = {"messageId": message_id, "channel": channel}
    response = httpx.post(
        "https://messaging.twilio.com/v2/Indicators/Typing.json",
        auth=(account_sid, auth_token),
        data=data,
    )
    response.raise_for_status()

    return response.json()


def split_whatsapp_message(text: str, limit: int = 1600) -> list[str]:
    """
    Split a message into chunks that fit within the Twilio/WhatsApp character limit.

    Uses a hierarchical splitting strategy to preserve message structure:
    1. Paragraphs (double newlines) - keeps logical sections together
    2. Lines (single newlines) - preserves line breaks
    3. Sentences (. ! ?) - keeps complete thoughts together
    4. Words (spaces) - avoids breaking mid-word
    5. Characters (fallback) - hard split for extremely long words

    Args:
        text: The message text to split
        limit: Maximum characters per chunk (default 1600 for WhatsApp)

    Returns:
        List of message chunks, each ≤ limit characters. Returns empty list
        if text is empty, single-element list if text fits in one chunk.

    Examples:
        >>> split_whatsapp_message("Short message")
        ['Short message']

        >>> split_whatsapp_message("A" * 2000, limit=1600)
        ['AAA...', 'AAA...']  # Split into 2 chunks
    """
    if not text or len(text) <= limit:
        return [text] if text else []

    chunks = []
    current_chunk = ""

    def flush_chunk():
        """Add current chunk to results and reset."""
        nonlocal current_chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""

    def add_piece(piece: str):
        """Add piece to current chunk, flushing if needed."""
        nonlocal current_chunk

        # If piece alone exceeds limit, it needs further splitting
        if len(piece) > limit:
            return False

        # If adding piece would exceed limit, flush current chunk first
        if current_chunk and len(current_chunk) + len(piece) > limit:
            flush_chunk()

        current_chunk += piece
        return True

    def split_by_sentences(text: str):
        """Split text by sentence boundaries."""
        # Split on sentence endings followed by space or newline
        sentences = re.split(r"([.!?]+[\s\n]+)", text)

        # Rejoin punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        # Add any remaining fragment
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])

        return result

    def split_by_words(text: str):
        """Split text by words, preserving spaces."""
        words = text.split(" ")
        for i, word in enumerate(words):
            word_with_space = word + (" " if i < len(words) - 1 else "")

            if not add_piece(word_with_space):
                # Word is too long, hard split
                split_by_chars(word_with_space)

    def split_by_chars(text: str):
        """Hard split text by character limit."""
        nonlocal current_chunk
        for i in range(0, len(text), limit):
            chunk = text[i : i + limit]
            if current_chunk and len(current_chunk) + len(chunk) > limit:
                flush_chunk()
            current_chunk += chunk

    # Split by paragraphs (double newlines)
    paragraphs = text.split("\n\n")

    for i, para in enumerate(paragraphs):
        # Preserve paragraph separator except after last paragraph
        separator = "\n\n" if i < len(paragraphs) - 1 else ""
        para_with_sep = para + separator

        if add_piece(para_with_sep):
            continue

        # Paragraph too long - split by lines
        lines = para.split("\n")
        for j, line in enumerate(lines):
            line_with_sep = line + ("\n" if j < len(lines) - 1 else "")

            if add_piece(line_with_sep):
                continue

            # Line too long - split by sentences
            sentences = split_by_sentences(line_with_sep)
            for sentence in sentences:
                if add_piece(sentence):
                    continue

                # Sentence too long - split by words
                split_by_words(sentence)

        # Re-add paragraph separator if needed
        if i < len(paragraphs) - 1:
            add_piece("\n\n")

    flush_chunk()
    return chunks
