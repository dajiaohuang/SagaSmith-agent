import re


def chunk_markdown(text: str, source: str) -> list[dict]:
    chunks, headings, body = [], [], []

    def flush():
        content = "\n".join(body).strip()
        if content:
            chunks.append({"source": source, "chapter": headings[0] if headings else source,
                           "section": headings[-1] if headings else source, "chunk_text": content})
        body.clear()

    for line in text.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+)", line)
        page_match = re.match(r"^(?:【第\s*(\d+)\s*页】|\[Page\s+(\d+)\])$", line.strip(), re.IGNORECASE)
        if match:
            flush()
            level = len(match.group(1))
            headings[:] = headings[:level - 1]
            headings.append(match.group(2).strip())
        elif page_match:
            flush()
            page = page_match.group(1) or page_match.group(2)
            headings[:] = [headings[0] if headings else source, f"Page {page}"]
        else:
            body.append(line)
            if sum(len(x) for x in body) > 1400:
                flush()
    flush()
    return chunks
