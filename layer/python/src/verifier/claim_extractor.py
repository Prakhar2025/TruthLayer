"""Extract atomic factual claims from AI-generated text."""

import re
from typing import List

from src.utils.text_splitter import split_into_sentences


class ClaimExtractor:
    """Extract verifiable claims from AI responses."""
    
    def extract_claims(self, ai_response: str) -> List[str]:
        """
        Extract atomic factual claims from AI response text.
        
        Args:
            ai_response: The AI-generated text to analyze
            
        Returns:
            List of claim strings (sentences)
        """
        if not ai_response or not ai_response.strip():
            return []
        
        # Split into sentences
        sentences = split_into_sentences(ai_response)
        
        # Filter and clean claims
        claims = []
        for sentence in sentences:
            claim = self._process_claim(sentence)
            if claim and self._is_factual_claim(claim):
                claims.append(claim)
        
        return claims
    
    def _process_claim(self, sentence: str) -> str:
        """Clean and normalize a claim sentence."""
        # Remove extra whitespace
        claim = ' '.join(sentence.split())
        
        # Remove markdown formatting
        claim = re.sub(r'\*\*(.+?)\*\*', r'\1', claim)
        claim = re.sub(r'\*(.+?)\*', r'\1', claim)
        claim = re.sub(r'`(.+?)`', r'\1', claim)
        
        return claim.strip()
    
    def _is_factual_claim(self, claim: str) -> bool:
        """
        Determine if a claim is factual and verifiable.
        
        Args:
            claim: Claim text to evaluate
            
        Returns:
            True if claim appears factual
        """
        # Skip very short claims
        if len(claim) < 10:
            return False
        
        # Skip questions
        if claim.strip().endswith('?'):
            return False
        
        # Skip greetings and meta-statements
        skip_patterns = [
            r'^(hello|hi|hey|thanks|thank you)',
            r'^(i think|i believe|in my opinion)',
            r'^(let me|i will|i can)',
        ]
        
        claim_lower = claim.lower()
        for pattern in skip_patterns:
            if re.match(pattern, claim_lower):
                return False
        
        # Check for factual indicators (numbers, entities, specific terms)
        factual_indicators = [
            r'\d+',  # Numbers
            r'\d+%',  # Percentages
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Proper names
            r'\b(is|are|was|were|has|have|had)\b',  # Factual verbs
        ]
        
        for pattern in factual_indicators:
            if re.search(pattern, claim):
                return True
        
        # Default to including if it's a complete sentence
        return len(claim.split()) >= 5
