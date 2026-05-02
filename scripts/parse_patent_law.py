#!/usr/bin/env python3
"""
解析 knowledge/patent_law.md 並生成 knowledge/truth_law.json

此腳本解析專利法 markdown 檔案,將法條內容轉換為結構化 JSON 格式。
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
PATENT_LAW_MD = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'patent_law.md'
)

OUTPUT_JSON = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'truth_law.json'
)


def parse_patent_law(file_path):
    """
    解析專利法 markdown 檔案。
    
    Args:
        file_path: markdown 檔案路徑
        
    Returns:
        List[Dict]: 法條列表
    """
    logger.info(f"開始解析: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    laws = []
    current_chapter = ""
    current_article = None
    current_content = []
    
    # 章節模式: "   第 X 章 標題" 或 "      第 X 節 標題"
    chapter_pattern = re.compile(r'^\s+(第\s+[一二三四五六七八九十]+\s+章\s+.+)$')
    section_pattern = re.compile(r'^\s+(第\s+[一二三四五六七八九十]+\s+節\s+.+)$')
    
    # 條文模式: "第 X 條"
    article_pattern = re.compile(r'^第\s+(\d+(?:-\d+)?)\s+條\s*$')
    
    # 項次模式: "1   內容" 或 "2   內容" (數字開頭)
    item_pattern = re.compile(r'^(\d+)\s+(.+)$')
    
    # 款項模式: "一、內容" 或 "二、內容"
    subitem_pattern = re.compile(r'^([一二三四五六七八九十]+)、(.+)$')
    
    def save_current_article():
        """儲存當前條文"""
        nonlocal current_article, current_content, current_chapter
        
        if current_article and current_content:
            # 組合內容,移除多餘空格
            content = ' '.join(current_content).strip()
            content = re.sub(r'\s+', ' ', content)  # 將多個空格合併為一個
            
            laws.append({
                "article_number": current_article,
                "content": content,
                "chapter": current_chapter,
                "is_starred": False,
                "total_score": 0.0,
                "attempt_count": 0,
                "avg_score": 0.0
            })
            
            logger.debug(f"已儲存 {current_article}: {content[:50]}...")
    
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        
        # 跳過空行和前面的標題行
        if not line.strip() or line.startswith('法規名稱') or line.startswith('修正日期'):
            continue
        
        # 檢查是否為章節標題
        chapter_match = chapter_pattern.match(line)
        if chapter_match:
            current_chapter = chapter_match.group(1).strip()
            logger.debug(f"發現章節: {current_chapter}")
            continue
        
        # 檢查是否為節標題(也算在章節中)
        section_match = section_pattern.match(line)
        if section_match:
            # 節標題不改變 current_chapter,只記錄
            logger.debug(f"發現節: {section_match.group(1).strip()}")
            continue
        
        # 檢查是否為新條文
        article_match = article_pattern.match(line)
        if article_match:
            # 儲存前一個條文
            save_current_article()
            
            # 開始新條文
            current_article = line.strip()
            current_content = []
            logger.debug(f"發現條文: {current_article}")
            continue
        
        # 如果有當前條文,收集內容
        if current_article:
            stripped = line.strip()
            if stripped:
                current_content.append(stripped)
    
    # 儲存最後一個條文
    save_current_article()
    
    logger.info(f"解析完成,共 {len(laws)} 條法條")
    return laws


def generate_truth_law_json():
    """生成 truth_law.json 檔案"""
    try:
        # 解析專利法
        laws = parse_patent_law(PATENT_LAW_MD)
        
        if not laws:
            logger.error("未解析到任何法條!")
            return False
        
        # 寫入 JSON
        logger.info(f"寫入 JSON 檔案: {OUTPUT_JSON}")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(laws, f, ensure_ascii=False, indent=4)
        
        logger.info(f"✅ 成功生成 {OUTPUT_JSON}")
        logger.info(f"   總共 {len(laws)} 條法條")
        
        # 統計章節
        chapters = {}
        for law in laws:
            chapter = law['chapter']
            chapters[chapter] = chapters.get(chapter, 0) + 1
        
        logger.info(f"   章節分布:")
        for chapter, count in sorted(chapters.items()):
            logger.info(f"     {chapter}: {count} 條")
        
        return True
        
    except Exception as e:
        logger.error(f"生成 JSON 時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = generate_truth_law_json()
    sys.exit(0 if success else 1)
