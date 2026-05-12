#!/usr/bin/env python3
"""
行政訴訟法解析腳本
Parse Administrative Litigation Act from markdown format.

解析 knowledge/administrative_litigation_zh.md，提取結構化法條資料。

Usage:
    python scripts/parse_administrative_litigation.py --test
    python scripts/parse_administrative_litigation.py --output output.json
"""

import re
import json
from typing import List, Dict, Optional, Tuple


def extract_article_number(line: str) -> Optional[Tuple[int, str]]:
    """
    從條號行提取數字和完整條號
    
    Args:
        line: 條號行，例如 "第 1 條" 或 "第 3-1 條" 或 "第 307-1 條"
    
    Returns:
        Tuple[int, str]: (主要數字, 完整條號)，如果無法提取則返回 None
    
    Examples:
        >>> extract_article_number("第 1 條")
        (1, "第 1 條")
        >>> extract_article_number("第 3-1 條")
        (3, "第 3-1 條")
        >>> extract_article_number("第 307-1 條")
        (307, "第 307-1 條")
    """
    # 匹配 "第 X 條" 或 "第 X-Y 條" 格式
    match = re.search(r'第\s*(\d+)(?:-\d+)?\s*條', line)
    if match:
        main_number = int(match.group(1))
        full_article = line.strip()
        return (main_number, full_article)
    return None


def format_chapter_path(edition: str, chapter: str, section: str) -> str:
    """
    格式化完整章節路徑（三層級：編/章/節）
    
    Args:
        edition: 編標題，例如 "第一編 總則"
        chapter: 章標題，例如 "第一章 行政訴訟事件"
        section: 節標題，例如 "第一節 管轄"
    
    Returns:
        str: 完整路徑
    
    Examples:
        >>> format_chapter_path("第一編 總則", "第一章 行政訴訟事件", "")
        '第一編 總則 / 第一章 行政訴訟事件'
        >>> format_chapter_path("第一編 總則", "第二章 行政法院", "第一節 管轄")
        '第一編 總則 / 第二章 行政法院 / 第一節 管轄'
    """
    parts = [edition, chapter]
    if section:
        parts.append(section)
    return ' / '.join(filter(None, parts))


def parse_administrative_litigation_md(file_path: str) -> List[Dict]:
    """
    解析行政訴訟法 markdown 文件，提取結構化法條資料
    
    解析規則：
    1. 編標題: "第 X 編" (無前綴空格)
    2. 章標題: 行首3個空格 + "第 X 章"
    3. 節標題: 行首6個空格 + "第 X 節"
    4. 條號: "第 X 條" 或 "第 X-Y 條" (支援附加條號)
    5. 條文內容: 可能有多段落，每段以 "1   ", "2   " 等數字開頭
    
    Args:
        file_path: markdown 文件路徑
    
    Returns:
        List[Dict]: 包含所有法條的列表，每個字典包含：
            - article_number: 條號字串 (e.g., "第 1 條", "第 3-1 條")
            - article_number_int: 條號整數 (e.g., 1, 3, 307)
            - chapter: 完整章節路徑（編/章/節）
            - content: 條文內容 (多段落用換行分隔)
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果解析失敗
    """
    articles = []
    current_edition = ""
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
            
            # 組合完整章節路徑（編/章/節）
            chapter_path = format_chapter_path(current_edition, current_chapter, current_section)
            
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
        
        # 檢測編標題 (無前綴空格，"第 X 編")
        if line.startswith('第 ') and '編' in line and not line.startswith('   '):
            current_edition = line.strip()
            current_chapter = ""  # 重置章
            current_section = ""  # 重置節
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
        
        # 檢測條號（包含附加條號如 3-1, 307-1）
        if line.startswith('第 ') and '條' in line:
            # 先保存前一條
            save_current_article()
            
            # 開始新條
            result = extract_article_number(line)
            if result:
                current_article_number_int, current_article_number = result
            else:
                print(f"警告: 第 {line_num} 行無法提取條號: {line}")
                current_article_number = line.strip()
                current_article_number_int = None
            
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
    
    parser = argparse.ArgumentParser(description='解析行政訴訟法 markdown 文件')
    parser.add_argument('--test', action='store_true',
                       help='測試模式：解析並顯示統計資訊')
    parser.add_argument('--output', type=str,
                       help='輸出 JSON 文件路徑')
    parser.add_argument('--input', type=str,
                       default='knowledge/administrative_litigation_zh.md',
                       help='輸入 markdown 文件路徑（預設：knowledge/administrative_litigation_zh.md）')
    
    args = parser.parse_args()
    
    print(f"📖 讀取文件: {args.input}")
    
    try:
        articles = parse_administrative_litigation_md(args.input)
        
        print(f"✅ 成功解析 {len(articles)} 條行政訴訟法條文\n")
        
        # 統計編分布
        editions = {}
        for article in articles:
            # 提取編（第一層級）
            if ' / ' in article['chapter']:
                edition = article['chapter'].split(' / ')[0]
            else:
                edition = article['chapter']
            editions[edition] = editions.get(edition, 0) + 1
        
        print("📊 編分布:")
        for edition, count in sorted(editions.items()):
            print(f"   {edition}: {count} 條")
        
        print(f"\n📈 條號範圍: {articles[0]['article_number']} - {articles[-1]['article_number']}")
        print(f"📈 條號整數範圍: {articles[0]['article_number_int']} - {articles[-1]['article_number_int']}")
        
        # 檢查附加條號
        compound_articles = [a for a in articles if '-' in a['article_number']]
        if compound_articles:
            print(f"\n🔢 發現 {len(compound_articles)} 個附加條號，例如:")
            for article in compound_articles[:5]:
                print(f"   {article['article_number']} (int: {article['article_number_int']})")
        
        # 如果是測試模式，顯示前幾條
        if args.test:
            print("\n📝 前 3 條預覽:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n   [{i}] {article['article_number']} (int: {article['article_number_int']})")
                print(f"       章節: {article['chapter']}")
                content_preview = article['content'][:100] + "..." if len(article['content']) > 100 else article['content']
                print(f"       內容: {content_preview}")
            
            print("\n📝 最後 3 條預覽:")
            for i, article in enumerate(articles[-3:], len(articles)-2):
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
