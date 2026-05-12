#!/usr/bin/env python3
"""
訴願法解析腳本
Parse Administrative Appeal Act from markdown format.

解析 knowledge/administrative_appeal_zh.md，提取結構化法條資料。

Usage:
    python scripts/parse_administrative_appeal.py --test
    python scripts/parse_administrative_appeal.py --output output.json
"""

import re
import json
from typing import List, Dict, Optional


def extract_article_number(line: str) -> Optional[int]:
    """
    從條號行提取數字
    
    Args:
        line: 條號行，例如 "第 1 條" 或 "第 101 條"
    
    Returns:
        int: 條號數字，如果無法提取則返回 None
    
    Examples:
        >>> extract_article_number("第 1 條")
        1
        >>> extract_article_number("第 101 條")
        101
    """
    match = re.search(r'第\s*(\d+)\s*條', line)
    if match:
        return int(match.group(1))
    return None


def format_chapter_path(chapter: str, section: str) -> str:
    """
    格式化完整章節路徑
    
    Args:
        chapter: 章標題，例如 "第一章 總則"
        section: 節標題，例如 "第一節 訴願事件"
    
    Returns:
        str: 完整路徑，例如 "第一章 總則 / 第一節 訴願事件"
    
    Examples:
        >>> format_chapter_path("第一章 總則", "第一節 訴願事件")
        '第一章 總則 / 第一節 訴願事件'
        >>> format_chapter_path("第一章 總則", "")
        '第一章 總則'
    """
    if section:
        return f"{chapter} / {section}"
    return chapter


def parse_administrative_appeal_md(file_path: str) -> List[Dict]:
    """
    解析訴願法 markdown 文件，提取結構化法條資料
    
    解析規則：
    1. 章標題: 行首3個空格 + "第 X 章"
    2. 節標題: 行首6個空格 + "第 X 節"
    3. 條號: "第 X 條"
    4. 條文內容: 可能有多段落，每段以 "1   ", "2   " 等數字開頭
    
    Args:
        file_path: markdown 文件路徑
    
    Returns:
        List[Dict]: 包含所有法條的列表，每個字典包含：
            - article_number: 條號字串 (e.g., "第 1 條")
            - article_number_int: 條號整數 (e.g., 1)
            - chapter: 完整章節路徑
            - content: 條文內容 (多段落用換行分隔)
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果解析失敗
    """
    articles = []
    current_chapter = ""
    current_section = ""
    current_article_number = None
    current_article_number_int = None
    current_content_lines = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到文件: {file_path}")
    
    def save_current_article():
        """保存當前收集的法條"""
        if current_article_number is not None and current_content_lines:
            # 合併內容行，用換行符分隔
            content = '\n'.join(current_content_lines)
            
            # 組合完整章節路徑
            chapter_path = format_chapter_path(current_chapter, current_section)
            
            article = {
                'article_number': current_article_number,
                'article_number_int': current_article_number_int,
                'chapter': chapter_path,
                'content': content.strip()
            }
            
            articles.append(article)
    
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip()
        
        # 跳過空行和法規標題/日期
        if not line or line.startswith('法規名稱') or line.startswith('修正日期'):
            continue
        
        # 檢測章標題 (前面有3個空格)
        if line.startswith('   第 ') and '章' in line and not line.startswith('      '):
            current_chapter = line.strip()
            current_section = ""  # 重置節
            continue
        
        # 檢測節標題 (前面有6個空格)
        if line.startswith('      第 ') and '節' in line:
            current_section = line.strip()
            continue
        
        # 檢測條號
        if line.startswith('第 ') and '條' in line:
            # 先保存前一條
            save_current_article()
            
            # 開始新條
            current_article_number = line.strip()
            current_article_number_int = extract_article_number(line)
            
            if current_article_number_int is None:
                print(f"警告: 第 {line_num} 行無法提取條號: {line}")
            
            current_content_lines = []
            continue
        
        # 收集條文內容
        if current_article_number is not None:
            # 移除行首的數字標記 (如 "1   ", "2   ")
            content = re.sub(r'^\d+\s+', '', line)
            if content.strip():  # 只添加非空內容
                current_content_lines.append(content.strip())
    
    # 保存最後一條
    save_current_article()
    
    if not articles:
        raise ValueError(f"未能從 {file_path} 中解析出任何法條")
    
    return articles


def main():
    """主函數，處理命令列參數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='解析訴願法 markdown 文件')
    parser.add_argument('--test', action='store_true',
                       help='測試模式：解析並顯示統計資訊')
    parser.add_argument('--output', type=str,
                       help='輸出 JSON 文件路徑')
    parser.add_argument('--input', type=str,
                       default='knowledge/administrative_appeal_zh.md',
                       help='輸入 markdown 文件路徑（預設：knowledge/administrative_appeal_zh.md）')
    
    args = parser.parse_args()
    
    print(f"📖 讀取文件: {args.input}")
    
    try:
        articles = parse_administrative_appeal_md(args.input)
        
        print(f"✅ 成功解析 {len(articles)} 條訴願法條文\n")
        
        # 統計資訊
        chapters = {}
        for article in articles:
            chapter = article['chapter'].split(' / ')[0]  # 只取章，不含節
            chapters[chapter] = chapters.get(chapter, 0) + 1
        
        print("📊 章節分布:")
        for chapter, count in sorted(chapters.items()):
            print(f"   {chapter}: {count} 條")
        
        print(f"\n📈 條號範圍: {articles[0]['article_number']} - {articles[-1]['article_number']}")
        
        # 如果是測試模式，顯示前幾條
        if args.test:
            print("\n📝 前 3 條預覽:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n   [{i}] {article['article_number']} (int: {article['article_number_int']})")
                print(f"       章節: {article['chapter']}")
                content_preview = article['content'][:100] + "..." if len(article['content']) > 100 else article['content']
                print(f"       內容: {content_preview}")
        
        # 如果指定了輸出文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"\n💾 已將結果保存到: {args.output}")
        
        return articles
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()
