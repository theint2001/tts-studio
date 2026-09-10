import re
from typing import List

class TextChunker:
    """
    Intelligent multi-lingual sentence and paragraph chunker
    specialized for Myanmar Unicode and English long-form narration.
    """

    # Myanmar punctuation:
    # U+104A: ၊ (Myanmar Little Section / Comma)
    # U+104B: ။ (Myanmar Section / Period)
    MYANMAR_SENTENCE_END = re.compile(r'([။!\?\n]+)')
    MYANMAR_CLAUSE_END = re.compile(r'([၊;]+)')
    
    # English punctuation
    ENGLISH_SENTENCE_END = re.compile(r'((?<=[.!?])\s+|\n+)')
    ENGLISH_CLAUSE_END = re.compile(r'((?<=[,;:])\s+)')

    def __init__(self, max_chunk_chars: int = 700, min_chunk_chars: int = 50):
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars

    def is_primarily_myanmar(self, text: str) -> bool:
        """Check if the text contains Myanmar Unicode characters (U+1000 - U+109F)."""
        myanmar_chars = len(re.findall(r'[\u1000-\u109F\uA9E0-\uA9FE\uAA60-\uAA7F]', text))
        total_non_ws = len(re.findall(r'\S', text))
        if total_non_ws == 0:
            return False
        return (myanmar_chars / total_non_ws) > 0.2

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Splits text into cohesive sentences or thought units,
        preserving punctuation at the end of each unit.
        """
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        units: List[str] = []

        for paragraph in paragraphs:
            if self.is_primarily_myanmar(paragraph):
                # Myanmar sentence splitting: split on ။ or \n while keeping the delimiter
                tokens = re.split(r'([။!\?]+)', paragraph)
                current = ""
                for token in tokens:
                    if not token:
                        continue
                    current += token
                    if re.match(r'[။!\?]+', token):
                        if current.strip():
                            units.append(current.strip())
                        current = ""
                if current.strip():
                    units.append(current.strip())
            else:
                # English sentence splitting: split on .!? followed by space or end
                tokens = re.split(r'([.!?]+(?:\s+|$))', paragraph)
                current = ""
                for token in tokens:
                    if not token:
                        continue
                    current += token
                    if re.match(r'[.!?]+(?:\s+|$)', token):
                        if current.strip():
                            units.append(current.strip())
                        current = ""
                if current.strip():
                    units.append(current.strip())

        return units if units else [text.strip()]

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunks text into manageable segments for TTS synthesis.
        Guarantees that each chunk is within reasonable length while
        never cutting words or phrases mid-stream.
        """
        cleaned = text.strip()
        if not cleaned:
            return []

        # If overall text is shorter than max limit, return as single chunk
        if len(cleaned) <= self.max_chunk_chars:
            return [cleaned]

        sentences = self.split_into_sentences(cleaned)
        chunks: List[str] = []
        current_chunk = ""

        for sent in sentences:
            # If a single sentence is abnormally long, break it by clauses (၊ or comma)
            if len(sent) > self.max_chunk_chars:
                # Flush existing chunk first
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Sub-split by clause
                if self.is_primarily_myanmar(sent):
                    sub_parts = re.split(r'([၊]+)', sent)
                else:
                    sub_parts = re.split(r'([,;:]+\s*)', sent)

                sub_curr = ""
                for part in sub_parts:
                    if not part:
                        continue
                    if len(sub_curr) + len(part) <= self.max_chunk_chars:
                        sub_curr += part
                    else:
                        if sub_curr.strip():
                            chunks.append(sub_curr.strip())
                        sub_curr = part
                if sub_curr.strip():
                    chunks.append(sub_curr.strip())
                continue

            # Check if adding this sentence exceeds limit
            delimiter = " " if not self.is_primarily_myanmar(sent) and current_chunk else ""
            candidate_len = len(current_chunk) + len(delimiter) + len(sent)

            if candidate_len <= self.max_chunk_chars:
                current_chunk = f"{current_chunk}{delimiter}{sent}" if current_chunk else sent
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sent

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks
