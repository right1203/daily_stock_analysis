# -*- coding: utf-8 -*-
"""
===================================
Formatting utilities
===================================

Utilities for converting common content into platform-specific formats.
"""

import re
from typing import List

import markdown2

TRUNCATION_SUFFIX = "\n\n...(이 구간은 너무 길어 잘렸습니다)"
PAGE_MARKER_PREFIX = f"\n\n📄"
PAGE_MARKER_SAFE_BYTES = 16  # "\n\n📄 9999/9999"
PAGE_MARKER_SAFE_LEN = 13  # "\n\n📄 9999/9999"
MIN_MAX_WORDS = 10
MIN_MAX_BYTES = 40

# Unicode code point ranges for special characters.
_SPECIAL_CHAR_RANGE = (0x10000, 0xFFFFF)
_SPECIAL_CHAR_REGEX = re.compile(r'[\U00010000-\U000FFFFF]')


def _page_marker(i: int, total: int) -> str:
    return f"{PAGE_MARKER_PREFIX} {i+1}/{total}"


def _is_special_char(c: str) -> bool:
    """
    Return whether a character is treated as special for length calculations.

    Args:
        c: Character.

    Returns:
        True when the character is special, otherwise False.
    """
    if len(c) != 1:
        return False
    cp = ord(c)
    return _SPECIAL_CHAR_RANGE[0] <= cp <= _SPECIAL_CHAR_RANGE[1]


def _count_special_chars(s: str) -> int:
    """
    Count special characters in a string.

    Args:
        s: String to inspect.
    """
    # reg find all (0x10000, 0xFFFFF)
    match = _SPECIAL_CHAR_REGEX.findall(s)
    return len(match)


def _effective_len(s: str, special_char_len: int = 2) -> int:
    """
    Calculate effective string length.

    Args:
        s: String to inspect.
        special_char_len: Effective length for each special character.

    Returns:
        Effective length of s.
    """
    n = len(s)
    n += _count_special_chars(s) * (special_char_len - 1)
    return n


def _slice_at_effective_len(s: str, effective_len: int, special_char_len: int = 2) -> tuple[str, str]:
    """
    Split a string at an effective length boundary.

    Args:
        s: String to split.
        effective_len: Effective split length.
        special_char_len: Effective length for each special character.

    Returns:
        Prefix and suffix after splitting.
    """
    if _effective_len(s, special_char_len) <= effective_len:
        return s, ""
    
    s_ = s[:effective_len]
    n_special_chars = _count_special_chars(s_)
    residual_lens = n_special_chars * (special_char_len - 1) + len(s_) - effective_len
    while residual_lens > 0:
        residual_lens -= special_char_len if _is_special_char(s_[-1]) else 1
        s_ = s_[:-1]
    return s_, s[len(s_):]


def markdown_to_html_document(markdown_text: str) -> str:
    """
    Convert Markdown to a complete HTML document (for email, md2img, etc.).

    Uses markdown2 with table and code block support, wraps with inline CSS
    for compact, readable layout. Reused by notification email and md2img.

    Args:
        markdown_text: Raw Markdown content.

    Returns:
        Full HTML document string with DOCTYPE, head, and body.
    """
    html_content = markdown2.markdown(
        markdown_text,
        extras=["tables", "fenced-code-blocks", "break-on-newline", "cuddled-lists"],
    )

    css_style = """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.5;
                color: #24292e;
                font-size: 14px;
                padding: 15px;
                max-width: 900px;
                margin: 0 auto;
            }
            h1 {
                font-size: 20px;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
                margin-top: 1.2em;
                margin-bottom: 0.8em;
                color: #0366d6;
            }
            h2 {
                font-size: 18px;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
                margin-top: 1.0em;
                margin-bottom: 0.6em;
            }
            h3 {
                font-size: 16px;
                margin-top: 0.8em;
                margin-bottom: 0.4em;
            }
            p {
                margin-top: 0;
                margin-bottom: 8px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 12px 0;
                display: block;
                overflow-x: auto;
                font-size: 13px;
            }
            th, td {
                border: 1px solid #dfe2e5;
                padding: 6px 10px;
                text-align: left;
            }
            th {
                background-color: #f6f8fa;
                font-weight: 600;
            }
            tr:nth-child(2n) {
                background-color: #f8f8f8;
            }
            tr:hover {
                background-color: #f1f8ff;
            }
            blockquote {
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                padding: 0 1em;
                margin: 0 0 10px 0;
            }
            code {
                padding: 0.2em 0.4em;
                margin: 0;
                font-size: 85%;
                background-color: rgba(27,31,35,0.05);
                border-radius: 3px;
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            }
            pre {
                padding: 12px;
                overflow: auto;
                line-height: 1.45;
                background-color: #f6f8fa;
                border-radius: 3px;
                margin-bottom: 10px;
            }
            hr {
                height: 0.25em;
                padding: 0;
                margin: 16px 0;
                background-color: #e1e4e8;
                border: 0;
            }
            ul, ol {
                padding-left: 20px;
                margin-bottom: 10px;
            }
            li {
                margin: 2px 0;
            }
        """

    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {css_style}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """


def markdown_to_plain_text(markdown_text: str) -> str:
    """
    Convert Markdown to plain text.

    Removes Markdown formatting while preserving readability.
    """
    text = markdown_text

    # Remove heading markers.
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold markers.
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # Remove italic markers.
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # Remove blockquote markers.
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Replace list markers with a readable bullet.
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)

    # Replace horizontal rules.
    text = re.sub(r'^---+$', '────────', text, flags=re.MULTILINE)

    # Remove Markdown table separator syntax.
    text = re.sub(r'\|[-:]+\|[-:|\s]+\|', '', text)
    text = re.sub(r'^\|(.+)\|$', r'\1', text, flags=re.MULTILINE)

    # Collapse extra blank lines.
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def _bytes(s: str) -> int:
    return len(s.encode('utf-8'))


def _chunk_by_max_bytes(content: str, max_bytes: int) -> List[str]:
    if _bytes(content) <= max_bytes:
        return [content]
    if max_bytes < MIN_MAX_BYTES:
        raise ValueError(f"max_bytes={max_bytes} < {MIN_MAX_BYTES}; recursive chunking may not terminate.")
    
    sections: List[str] = []
    suffix = TRUNCATION_SUFFIX
    effective_max_bytes = max_bytes - _bytes(suffix)
    if effective_max_bytes <= 0:
        effective_max_bytes = max_bytes
        suffix = ""
        
    while True:
        chunk, content = slice_at_max_bytes(content, effective_max_bytes)
        if content.strip() != "":
            sections.append(chunk + suffix)
        else:
            # Last segment; append it and stop.
            sections.append(chunk)
            break
    return sections


def chunk_content_by_max_bytes(content: str, max_bytes: int, add_page_marker: bool = False) -> List[str]:
    """
    Split message content by byte length.

    Args:
        content: Full message content.
        max_bytes: Maximum bytes per message.
        add_page_marker: Whether to add page markers.

    Returns:
        Message chunks.
    """
    def _chunk(content: str, max_bytes: int) -> List[str]:
        # Prefer separators and headings to keep pagination natural.
        if max_bytes < MIN_MAX_BYTES:
            raise ValueError(f"max_bytes={max_bytes} < {MIN_MAX_BYTES}; recursive chunking may not terminate.")
        
        if _bytes(content) <= max_bytes:
            return [content]
        
        sections, separator = _chunk_by_separators(content)
        if separator == "" and len(sections) == 1:
            # Fall back to forced byte chunking when no natural separator exists.
            return _chunk_by_max_bytes(content, max_bytes)
        
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_bytes = 0
        separator_bytes = _bytes(separator) if separator else 0
        effective_max_bytes = max_bytes - separator_bytes

        for section in sections:
            section += separator
            section_bytes = _bytes(section)
            
            # Force-split a section that exceeds the byte budget by itself.
            if section_bytes > effective_max_bytes:
                # Flush accumulated content first.
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_bytes = 0

                # Force byte-level chunking so the section is not dropped.
                section_chunks = _chunk(
                    section[:-separator_bytes], effective_max_bytes
                )
                section_chunks[-1] = section_chunks[-1] + separator
                chunks.extend(section_chunks)
                continue

            # Start a new chunk if this section would exceed the limit.
            if current_bytes + section_bytes > effective_max_bytes:
                # Save current chunk and start a new one.
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = [section]
                current_bytes = section_bytes
            else:
                current_chunk.append(section)
                current_bytes += section_bytes
                
        # Add the last chunk.
        if current_chunk:
            chunks.append("".join(current_chunk))

        # Remove the separator from the final chunk.
        if (chunks and 
            len(chunks[-1]) > separator_bytes and 
            chunks[-1][-separator_bytes:] == separator
        ):
            chunks[-1] = chunks[-1][:-separator_bytes]
        
        return chunks
    
    if add_page_marker:
        max_bytes = max_bytes - PAGE_MARKER_SAFE_BYTES
    
    chunks = _chunk(content, max_bytes)
    if add_page_marker:
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            chunks[i] = chunk + _page_marker(i, total_chunks)
    return chunks


def slice_at_max_bytes(text: str, max_bytes: int) -> str:
    """
    Truncate a string by byte length without splitting multibyte characters.

    Args:
        text: String to truncate.
        max_bytes: Maximum byte length.

    Returns:
        Truncated prefix and remaining suffix.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, ""

    # Walk backward from the byte limit to a valid UTF-8 boundary.
    truncated = encoded[:max_bytes]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]

    truncated = truncated.decode('utf-8', errors='ignore')
    return truncated, text[len(truncated):]


def _chunk_by_separators(content: str) -> tuple[list[str], str]:
    """
    Split message content into sections using separators and headings.

    Args:
        content: Full message content.

    Returns:
        Sections and the separator between sections.
    """
    # Prefer "---" separators between stocks, then headings.
    if "\n---\n" in content:
        sections = content.split("\n---\n")
        separator = "\n---\n"
    elif "\n# " in content:
        # Split by top-level headings.
        parts = content.split("\n## ")
        sections = [parts[0]] + [f"## {p}" for p in parts[1:]]
        separator = "\n"
    elif "\n## " in content:
        # Split by second-level headings.
        parts = content.split("\n## ")
        sections = [parts[0]] + [f"## {p}" for p in parts[1:]]
        separator = "\n"
    elif "\n### " in content:
        # Split by third-level headings.
        parts = content.split("\n### ")
        sections = [parts[0]] + [f"### {p}" for p in parts[1:]]
        separator = "\n"
    elif "\n**" in content:
        # Split by bold headings when AI output does not use Markdown headings.
        parts = content.split("\n**")
        sections = [parts[0]] + [f"**{p}" for p in parts[1:]]
        separator = "\n"
    elif "\n" in content:
        # Split by newline as a final natural separator.
        sections = content.split("\n")
        separator = "\n"
    else:
        return [content], ""
    return sections, separator


def _chunk_by_max_words(content: str, max_words: int, special_char_len: int = 2) -> list[str]:
    """
    Split message content by effective character count.

    Args:
        content: Full message content.
        max_words: Maximum effective characters per message.
        special_char_len: Effective length for each special character.

    Returns:
        Message chunks.
    """
    if _effective_len(content, special_char_len) <= max_words:
        return [content]
    if max_words < MIN_MAX_WORDS:
        raise ValueError(
            f"max_words={max_words} < {MIN_MAX_WORDS}; recursive chunking may not terminate."
        )

    sections = []
    suffix = TRUNCATION_SUFFIX
    effective_max_words = max_words - len(suffix)  # Reserve suffix length.
    if effective_max_words <= 0:
        effective_max_words = max_words
        suffix = ""

    while True:
        chunk, content = _slice_at_effective_len(content, effective_max_words, special_char_len)
        if content.strip() != "":
            sections.append(chunk + suffix)
        else:
            # Last segment; append it and stop.
            sections.append(chunk)
            break
    return sections


def chunk_content_by_max_words(
    content: str, 
    max_words: int, 
    special_char_len: int = 2,
    add_page_marker: bool = False
    ) -> list[str]:
    """
    Split message content by effective character count using natural boundaries.

    Args:
        content: Full message content.
        max_words: Maximum effective characters per message.
        special_char_len: Effective length for each special character.
        add_page_marker: Whether to add page markers.

    Returns:
        Message chunks.
    """
    def _chunk(content: str, max_words: int, special_char_len: int = 2) -> list[str]:
        if max_words < MIN_MAX_WORDS:
            # Guard against recursive chunking that cannot make progress.
            raise ValueError(f"max_words={max_words} < {MIN_MAX_WORDS}; recursive chunking may not terminate.")
        
        if _effective_len(content, special_char_len) <= max_words:
            return [content]

        sections, separator = _chunk_by_separators(content)
        if separator == "" and len(sections) == 1:
            # Fall back to forced character-count chunking.
            return _chunk_by_max_words(content, max_words, special_char_len)

        chunks = []
        current_chunk = []
        current_word_len = 0
        separator_len = len(separator) if separator else 0
        effective_max_words = max_words - separator_len  # Reserve separator length.

        for section in sections:
            section += separator
            section_word_len = _effective_len(section, special_char_len)

            # Force-split a section that exceeds the word budget by itself.
            if section_word_len > max_words:
                # Flush accumulated content first.
                if current_chunk:
                    chunks.append("".join(current_chunk))

                # Force-split the oversized section.
                section_chunks = _chunk(
                    section[:-separator_len], effective_max_words, special_char_len
                    )
                section_chunks[-1] = section_chunks[-1] + separator
                chunks.extend(section_chunks)
                continue

            # Start a new chunk if this section would exceed the limit.
            if current_word_len + section_word_len > max_words:
                # Save current chunk and start a new one.
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = [section]
                current_word_len = section_word_len
            else:
                current_chunk.append(section)
                current_word_len += section_word_len

        # Add the last chunk.
        if current_chunk:
            chunks.append("".join(current_chunk))

        # Remove the separator from the final chunk.
        if (chunks and
            len(chunks[-1]) > separator_len and
            chunks[-1][-separator_len:] == separator
        ):
            chunks[-1] = chunks[-1][:-separator_len]
        return chunks
    
    
    if add_page_marker:
        max_words = max_words - PAGE_MARKER_SAFE_LEN
    
    chunks = _chunk(content, max_words, special_char_len)
    if add_page_marker:
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            chunks[i] = chunk + _page_marker(i, total_chunks)
    return chunks
