"""Text splitting utilities for processing source documents."""

from typing import List


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using basic punctuation rules.
    
    Args:
        text: Input text to split
        
    Returns:
        List of sentence strings
    """
    if not text or not text.strip():
        return []
    
    # Simple sentence splitting on common terminators
    sentences = []
    current = []
    
    for i, char in enumerate(text):
        current.append(char)
        
        # Check if this is a sentence terminator
        if char in '.!?':
            # Look ahead to see if this is end of sentence
            # (not a decimal, abbreviation, etc.)
            is_end = False
            
            if i + 1 >= len(text):
                # End of text
                is_end = True
            elif text[i + 1].isspace():
                # Followed by whitespace
                # Check if previous char is a digit (could be decimal)
                if i > 0 and text[i - 1].isdigit() and i + 1 < len(text) and text[i + 1:i + 2].strip() and text[i + 1].isdigit():
                    # Likely a decimal like "3.11"
                    is_end = False
                else:
                    is_end = True
            
            if is_end and len(current) > 1:
                sentence = ''.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []
    
    # Add remaining text
    if current:
        sentence = ''.join(current).strip()
        if sentence:
            sentences.append(sentence)
    
    return sentences


def chunk_text(text: str, max_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: Input text to chunk
        max_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    if len(text) <= max_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    
    return chunks
