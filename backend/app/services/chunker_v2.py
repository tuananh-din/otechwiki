"""Heading-aware chunking with section extraction. Replaces token-only split."""
import re
import tiktoken
from app.services.dedup import text_hash

tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
SEPARATOR_RE = re.compile(r"^---+$", re.MULTILINE)

MAX_CHUNK_TOKENS = 500
MIN_CHUNK_TOKENS = 50
OVERLAP_TOKENS = 50


def _token_count(text: str) -> int:
    return len(tokenizer.encode(text))


def _split_by_headings(text: str) -> list[dict]:
    """Split text into sections by headings (# ## ### etc)."""
    sections = []
    lines = text.split("\n")
    current_section = {"title": "", "path": "", "lines": [], "level": 0}
    heading_stack = []  # [(level, title)]

    for line in lines:
        heading_match = HEADING_RE.match(line)
        sep_match = SEPARATOR_RE.match(line.strip())

        if heading_match:
            # Save current section if it has content
            if current_section["lines"]:
                sections.append(current_section)

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            # Update heading stack
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))

            path = " > ".join(h[1] for h in heading_stack)
            current_section = {"title": title, "path": path, "lines": [], "level": level}

        elif sep_match:
            # Separator acts as section break
            if current_section["lines"]:
                sections.append(current_section)
                current_section = {
                    "title": current_section["title"],
                    "path": current_section["path"],
                    "lines": [],
                    "level": current_section["level"],
                }
        else:
            current_section["lines"].append(line)

    # Don't forget the last section
    if current_section["lines"]:
        sections.append(current_section)

    return sections


def _split_long_section(text: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[str]:
    """Split a long section by sentences, respecting token limits."""
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?。\n])\s+', text)
    chunks = []
    current = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = _token_count(sentence)
        if current_tokens + s_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            # Keep last sentence for overlap context
            if current and s_tokens < max_tokens:
                current = [current[-1], sentence]
                current_tokens = _token_count(current[-2]) + s_tokens
            else:
                current = [sentence]
                current_tokens = s_tokens
        else:
            current.append(sentence)
            current_tokens += s_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks


def smart_chunk(cleaned_text: str, document_title: str = "") -> list[dict]:
    """
    Heading-aware chunking with section extraction.
    Returns list of chunk dicts ready for DB insertion.
    """
    if not cleaned_text or not cleaned_text.strip():
        return []

    sections = _split_by_headings(cleaned_text)

    # If no headings found, treat entire text as one section
    if not sections:
        sections = [{"title": "", "path": "", "lines": cleaned_text.split("\n"), "level": 0}]

    chunks = []
    idx = 0

    for section in sections:
        section_text = "\n".join(line for line in section["lines"] if line.strip())
        if not section_text.strip():
            continue

        tokens = _token_count(section_text)

        if tokens <= MAX_CHUNK_TOKENS:
            # Section fits in one chunk
            display_content = section_text
            if document_title:
                display_content = f"[{document_title}] {section['title']}\n{section_text}" if section["title"] else f"[{document_title}]\n{section_text}"

            chunks.append({
                "content": display_content,
                "cleaned_content": section_text,  # Pure text for embedding/search
                "section_title": section["title"] or None,
                "section_path": section["path"] or None,
                "chunk_index": idx,
                "token_count": _token_count(section_text),
                "dedup_hash": text_hash(section_text),
                "is_searchable": True,
            })
            idx += 1

        elif tokens > MAX_CHUNK_TOKENS:
            # Split long section by sentences
            sub_chunks = _split_long_section(section_text, MAX_CHUNK_TOKENS)
            for i, sub_text in enumerate(sub_chunks):
                if _token_count(sub_text) < MIN_CHUNK_TOKENS:
                    continue

                sub_title = f"{section['title']} (phần {i+1})" if section["title"] else ""
                display_content = sub_text
                if document_title:
                    display_content = f"[{document_title}] {sub_title}\n{sub_text}" if sub_title else f"[{document_title}]\n{sub_text}"

                chunks.append({
                    "content": display_content,
                    "cleaned_content": sub_text,  # Pure text for embedding/search
                    "section_title": sub_title or section["title"] or None,
                    "section_path": section["path"] or None,
                    "chunk_index": idx,
                    "token_count": _token_count(sub_text),
                    "dedup_hash": text_hash(sub_text),
                    "is_searchable": True,
                })
                idx += 1

    return chunks
