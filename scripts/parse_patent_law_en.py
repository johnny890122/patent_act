#!/usr/bin/env python3
"""
Parse knowledge/patent_law_en.md and generate knowledge/truth_law_en.json

This script parses the English Patent Act markdown file, converting law article
content into a structured JSON format.
"""

import os
import sys
import json
import re
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
PATENT_LAW_EN_MD = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'patent_law_en.md'
)

OUTPUT_JSON = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'truth_law_en.json'
)


def parse_patent_law_en(file_path):
    """
    Parse English Patent Act markdown file.
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        List[Dict]: List of law articles
    """
    logger.info(f"Starting to parse: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    laws = []
    current_chapter = ""
    current_article = None
    current_content = []
    
    # Pattern for chapter headers: "Chapter 1 General Provisions" or "Chapter II Invention Patent"
    chapter_pattern = re.compile(r'^Chapter\s+([IVX]+|\d+)(?:\s+(.+))?$')
    
    # Pattern for article headers: "Article 1"
    article_pattern = re.compile(r'^Article\s+(\d+(?:-\d+)?)$')
    
    # Pattern for section headers: "Section 1 ..."
    section_pattern = re.compile(r'^Section\s+\d+')
    
    def save_current_article():
        """Save current article"""
        nonlocal current_article, current_content, current_chapter
        
        if current_article and current_content:
            # Combine content, remove extra spaces
            content = ' '.join(current_content).strip()
            content = re.sub(r'\s+', ' ', content)  # Merge multiple spaces into one
            
            laws.append({
                "article_number": f"Article {current_article}",
                "content": content,
                "chapter": current_chapter,
                "lang": "en",
                "is_starred": False,
                "total_score": 0.0,
                "attempt_count": 0,
                "avg_score": 0.0
            })
            
            logger.debug(f"Saved Article {current_article}: {content[:50]}...")
    
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        
        # Skip empty lines and metadata lines
        if not line.strip() or line.startswith('Laws & Regulations') or \
           line.startswith('Print Time') or line.startswith('Title:') or \
           line.startswith('Amended Date') or line.startswith('Category') or \
           line.startswith('Article Content'):
            continue
        
        # Check for chapter header
        chapter_match = chapter_pattern.match(line.strip())
        if chapter_match:
            chapter_num = chapter_match.group(1)
            chapter_title = chapter_match.group(2) if chapter_match.group(2) else ""
            current_chapter = f"Chapter {chapter_num}" + (f" {chapter_title}" if chapter_title else "")
            logger.debug(f"Found chapter: {current_chapter}")
            continue
        
        # Check for section header (don't change chapter, just skip)
        section_match = section_pattern.match(line.strip())
        if section_match:
            logger.debug(f"Found section: {line.strip()}")
            continue
        
        # Check for new article
        article_match = article_pattern.match(line.strip())
        if article_match:
            # Save previous article
            save_current_article()
            
            # Start new article
            current_article = article_match.group(1)
            current_content = []
            logger.debug(f"Found Article: {current_article}")
            continue
        
        # If we have a current article, collect content
        if current_article:
            stripped = line.strip()
            if stripped:
                current_content.append(stripped)
    
    # Save last article
    save_current_article()
    
    logger.info(f"Parsing complete: {len(laws)} articles parsed")
    return laws


def generate_truth_law_en_json():
    """Generate truth_law_en.json file"""
    try:
        # Parse English Patent Act
        laws = parse_patent_law_en(PATENT_LAW_EN_MD)
        
        if not laws:
            logger.error("No articles parsed!")
            return False
        
        # Write JSON
        logger.info(f"Writing JSON file: {OUTPUT_JSON}")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(laws, f, ensure_ascii=False, indent=4)
        
        logger.info(f"✅ Successfully generated {OUTPUT_JSON}")
        logger.info(f"   Total: {len(laws)} articles")
        
        # Statistics
        chapters = {}
        for law in laws:
            chapter = law['chapter']
            chapters[chapter] = chapters.get(chapter, 0) + 1
        
        logger.info(f"   Chapter distribution:")
        for chapter, count in sorted(chapters.items()):
            logger.info(f"     {chapter}: {count} articles")
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating JSON: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = generate_truth_law_en_json()
    sys.exit(0 if success else 1)
