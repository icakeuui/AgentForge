from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List


@dataclass(slots=True)
class ParsedKnowledgeChunk:
    content: str
    chunk_type: str = "plain"
    section_path: List[str] = field(default_factory=list)
    article_no: str | None = None
    article_label: str | None = None
    page_no: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeParser:
    CHUNK_SIZE = 900
    CHUNK_OVERLAP = 120
    ARTICLE_PATTERN = re.compile(r"第\s*([一二三四五六七八九十百0-9]+)\s*条")
    CHAPTER_PATTERN = re.compile(r"第\s*([一二三四五六七八九十百0-9]+)\s*章")
    SECTION_PATTERN = re.compile(r"第\s*([一二三四五六七八九十百0-9]+)\s*节")

    def parse(self, *, title: str, content: str) -> list[ParsedKnowledgeChunk]:
        normalized = re.sub(r"\n{3,}", "\n\n", content.strip())
        if not normalized:
            return []

        article_chunks = self._parse_articles(title=title, content=normalized)
        if article_chunks:
            return article_chunks
        return self._fallback_chunks(title=title, content=normalized, chunk_type="plain")

    def _parse_articles(self, *, title: str, content: str) -> list[ParsedKnowledgeChunk]:
        matches = list(self.ARTICLE_PATTERN.finditer(content))
        if not matches:
            return []

        chunks: list[ParsedKnowledgeChunk] = []
        current_chapter: str | None = None
        current_section: str | None = None
        cursor = 0
        for index, match in enumerate(matches):
            prefix = content[cursor : match.start()]
            current_chapter = self._last_label(self.CHAPTER_PATTERN, prefix) or current_chapter
            current_section = self._last_label(self.SECTION_PATTERN, prefix) or current_section

            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            raw_chunk = content[match.start() : end].strip()
            article_no = self.chinese_number_to_int(match.group(1))
            article_label = re.sub(r"\s+", "", match.group(0))
            section_path = [title]
            if current_chapter:
                section_path.append(current_chapter)
            if current_section:
                section_path.append(current_section)
            section_path.append(article_label)
            chunks.extend(
                self._split_long_article(
                    raw_chunk,
                    section_path=section_path,
                    article_no=str(article_no) if article_no is not None else None,
                    article_label=article_label,
                    start_offset=match.start(),
                )
            )
            cursor = match.start()
        return chunks

    def _split_long_article(
        self,
        content: str,
        *,
        section_path: list[str],
        article_no: str | None,
        article_label: str,
        start_offset: int,
    ) -> list[ParsedKnowledgeChunk]:
        if len(content) <= 1200:
            return [
                ParsedKnowledgeChunk(
                    content=content,
                    chunk_type="article",
                    section_path=section_path,
                    article_no=article_no,
                    article_label=article_label,
                    start_char=start_offset,
                    end_char=start_offset + len(content),
                )
            ]

        chunks: list[ParsedKnowledgeChunk] = []
        start = 0
        part = 1
        while start < len(content):
            end = min(start + self.CHUNK_SIZE, len(content))
            chunk_content = content[start:end].strip()
            if chunk_content and article_label not in chunk_content[:30]:
                chunk_content = f"{article_label}\n{chunk_content}"
            if chunk_content:
                chunks.append(
                    ParsedKnowledgeChunk(
                        content=chunk_content,
                        chunk_type="article",
                        section_path=[*section_path, f"part {part}"],
                        article_no=article_no,
                        article_label=article_label,
                        start_char=start_offset + start,
                        end_char=start_offset + end,
                        metadata={"part": part},
                    )
                )
                part += 1
            if end >= len(content):
                break
            start = max(end - self.CHUNK_OVERLAP, start + 1)
        return chunks

    def _fallback_chunks(self, *, title: str, content: str, chunk_type: str) -> list[ParsedKnowledgeChunk]:
        if len(content) <= self.CHUNK_SIZE:
            return [
                ParsedKnowledgeChunk(
                    content=content,
                    chunk_type=chunk_type,
                    section_path=[title],
                    start_char=0,
                    end_char=len(content),
                )
            ]

        chunks: list[ParsedKnowledgeChunk] = []
        start = 0
        while start < len(content):
            end = min(start + self.CHUNK_SIZE, len(content))
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(
                    ParsedKnowledgeChunk(
                        content=chunk,
                        chunk_type=chunk_type,
                        section_path=[title, f"片段 {len(chunks) + 1}"],
                        start_char=start,
                        end_char=end,
                    )
                )
            if end >= len(content):
                break
            start = max(end - self.CHUNK_OVERLAP, start + 1)
        return chunks

    @staticmethod
    def _last_label(pattern: re.Pattern[str], text: str) -> str | None:
        matches = list(pattern.finditer(text))
        if not matches:
            return None
        return re.sub(r"\s+", "", matches[-1].group(0))

    @staticmethod
    def chinese_number_to_int(value: str) -> int | None:
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        digits = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if text == "十":
            return 10
        if "十" in text:
            left, _, right = text.partition("十")
            tens = digits.get(left, 1) if left else 1
            ones = digits.get(right, 0) if right else 0
            return tens * 10 + ones
        if text in digits:
            return digits[text]
        return None

    @classmethod
    def extract_article_no(cls, text: str) -> str | None:
        match = cls.ARTICLE_PATTERN.search(text)
        if not match:
            match = re.search(r"\barticle\s+([0-9]+)\b", text, flags=re.IGNORECASE)
        if not match:
            return None
        number = cls.chinese_number_to_int(match.group(1))
        return str(number) if number is not None else None

    @classmethod
    def extract_article_label(cls, text: str) -> str | None:
        match = cls.ARTICLE_PATTERN.search(text)
        return re.sub(r"\s+", "", match.group(0)) if match else None


knowledge_parser = KnowledgeParser()
