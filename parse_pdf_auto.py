#!/usr/bin/env python3
"""
PDF 自動解析工具 - 簡化版
只需提供輸出目錄，自動判斷對應的 PDF 目錄和章節名稱
"""

import os
import json
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")

# 章節映射表
CHAPTER_MAPPING = {
    "01": {
        "name": "第一篇程序審查及專利權管理",
        "docs_dir": "docs/01"
    },
    "02": {
        "name": "第二篇發明專利實體審查",
        "docs_dir": "docs/02"
    },
    "03": {
        "name": "第三篇設計專利實體審查",
        "docs_dir": "docs/03"
    },
    "04": {
        "name": "第四篇新型專利形式審查",
        "docs_dir": "docs/04"
    },
    "05": {
        "name": "第五篇舉發審查",
        "docs_dir": "docs/05"
    },
    "06": {
        "name": "",
        "docs_dir": "docs/06"
    }
}

# --- System Prompt ---
SYSTEM_PROMPT = """你是一個專業的法規與專利審查基準文檔解析專家。你的任務是將使用者上傳的 PDF 文本，精準地提取、清理，並轉換為結構化的 JSON 陣列格式。

任務目標 (Task)
將文本以「X.Y (章節與小節標題)」為單位進行切割，過濾所有與正文無關的雜訊，並計算出用於資料庫排序的整數編號，最後輸出為純 JSON 陣列。

輸出 Schema 定義
每個區塊必須嚴格遵循以下 JSON 格式：

{
  "article_number": "字串 (例如: 1.1 前言)",
  "article_number_int": 整數 (例如: 10100),
  "chapter": "字串 (所屬篇章名稱)",
  "content": "字串 (完整正文內容)",
  "lang": "zh-TW"
}

資料處理嚴格規則 (Processing Rules)

1. 切割單位 (Chunking)：
   - 必須以標題（如 1.1 前言、1.4.1「相同發明」之判斷）作為一個新的物件單位。
   - 單純的 1. 國際優先權（大標題）不應單獨切為一個沒有內容的區塊，應從 1.1 開始將內容打包。

2. 雜訊過濾 (Noise Filtering)：
   - 絕對不要解析「目錄 (Table of Contents)」的內容。正文通常在目錄之後才開始。
   - 略過所有 PDF 產生的標籤。
   - 略過所有頁首、頁尾與頁碼，例如：「2023年版」、「第二篇發明專利實體審查」、「第五章 優先權」、「2-5-1」等純粹的版面資訊。
   - 完全忽略所有範例 (例如：「例」、「例1.」、「【例】」、「案例」等開頭的內容)。
   - 完全忽略所有圖示、圖表說明、圖號 (例如：「圖1」、「圖2-1」、「示意圖」等)。
   - 完全忽略所有表格內容。

3. 整數編號轉換 (Integer Conversion)：
   - 為了方便資料庫排序，必須將 article_number 前方的數字轉換為 article_number_int。
   - 計算邏輯：第一層 * 10000 + 第二層 * 100 + 第三層 * 1。
   - 範例一：標題為 1.1 前言，數字部分為 1.1，計算為 1*10000 + 1*100 = 10100。
   - 範例二：標題為 1.4.1「相同發明」之判斷，數字部分為 1.4.1，計算為 1*10000 + 4*100 + 1 = 10401。
   - 範例三：標題為 2.6.4 符合發明單一性...，數字部分為 2.6.4，計算為 2*10000 + 6*100 + 4 = 20604。

4. 內文處理 (Content Processing)：
   - 屬於同一個標題的段落必須合併至 content 中，保留正確的換行符號 \n。
   - 去除每行開頭與結尾多餘的空白，確保內文乾淨易讀。
   - 移除所有範例和圖示後的內容。

5. 輸出限制 (Output Constraint)：
   - 請僅輸出合法的 JSON 陣列 (JSON Array)。
   - 不要輸出任何問候語、解釋、或 JSON 以外的 Markdown 標記（不需要輸出 ```json 標籤）。
   - 直接輸出純 JSON 內容。"""

# --- Helper Functions ---

def detect_chapter_from_output_dir(output_dir: str) -> Optional[Tuple[str, str, str]]:
    """
    從輸出目錄自動偵測章節資訊
    
    Args:
        output_dir: 輸出目錄（例如：knowledge/examination/01）
        
    Returns:
        (chapter_id, chapter_name, docs_dir) 或 None
    """
    output_path = Path(output_dir)
    
    # 嘗試從路徑中提取章節編號
    for part in reversed(output_path.parts):
        if part in CHAPTER_MAPPING:
            chapter_info = CHAPTER_MAPPING[part]
            return (part, chapter_info["name"], chapter_info["docs_dir"])
    
    return None

def read_pdf(file_path: Path) -> str:
    """從 PDF 文件中提取文本內容"""
    try:
        with fitz.open(file_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
            return text
    except Exception as e:
        print(f"讀取 PDF 失敗 {file_path}: {e}")
        return ""

def query_openrouter(
    pdf_content: str,
    chapter_name: str,
    model: str = "anthropic/claude-sonnet-4.5"
) -> Dict[str, Any]:
    """呼叫 OpenRouter API 解析 PDF 內容"""
    user_prompt = f"""章節名稱：{chapter_name}

PDF 內容：
---
{pdf_content}
---

請按照系統提示詞的規則，將上述 PDF 內容解析為 JSON 陣列格式。記得：
1. 完全忽略範例和圖示
2. 忽略目錄、頁首、頁尾
3. 以章節標題切割
4. 正確計算 article_number_int
5. 直接輸出 JSON 陣列，不要任何額外說明"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1
            },
            timeout=300
        )
        response.raise_for_status()
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        
        # 解析 JSON
        if "```json" in ai_response:
            json_text = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            json_text = ai_response.split("```")[1].split("```")[0].strip()
        else:
            json_text = ai_response.strip()
        
        parsed_data = json.loads(json_text)
        return {
            "success": True,
            "data": parsed_data,
            "raw_response": ai_response
        }
        
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API 請求失敗: {str(e)}", "data": None}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 解析失敗: {str(e)}", "data": None, "raw_response": ai_response if 'ai_response' in locals() else None}
    except Exception as e:
        return {"success": False, "error": f"未預期的錯誤: {str(e)}", "data": None}

def process_pdf_file(
    pdf_path: Path,
    output_path: Path,
    chapter_name: str,
    model: str,
    log_dir: Path
) -> bool:
    """處理單個 PDF 文件"""
    thread_name = threading.current_thread().name
    print(f"\n[{thread_name}] 處理中: {pdf_path.name}")
    
    # 讀取 PDF
    pdf_content = read_pdf(pdf_path)
    if not pdf_content:
        print(f"[{thread_name}] ❌ 無法讀取 PDF 內容")
        return False
    
    print(f"[{thread_name}] 📄 已讀取 PDF，共 {len(pdf_content)} 字元")
    
    # 呼叫 API
    print(f"[{thread_name}] 🤖 正在呼叫 OpenRouter API...")
    result = query_openrouter(pdf_content, chapter_name, model)
    
    # 記錄日誌
    log_filename = f"parse_{pdf_path.stem}_{datetime.now():%Y%m%d_%H%M%S}.log"
    log_filepath = log_dir / log_filename
    
    log_content = f"""--- 解析日誌 ---
時間: {datetime.now()}
PDF 檔案: {pdf_path}
輸出檔案: {output_path}
章節名稱: {chapter_name}
模型: {model}
成功: {result['success']}
"""
    
    if result['success']:
        # 儲存 JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result['data'], f, ensure_ascii=False, indent=2)
        
        print(f"[{thread_name}] ✅ 成功解析並儲存至: {output_path}")
        print(f"[{thread_name}] 📊 共解析出 {len(result['data'])} 個條文")
        
        log_content += f"\n解析條文數量: {len(result['data'])}\n"
        log_content += f"\n--- AI 原始回應 ---\n{result['raw_response']}\n"
    else:
        print(f"[{thread_name}] ❌ 解析失敗: {result['error']}")
        log_content += f"\n錯誤訊息: {result['error']}\n"
        if result.get('raw_response'):
            log_content += f"\n--- AI 原始回應 ---\n{result['raw_response']}\n"
    
    # 寫入日誌
    with open(log_filepath, 'w', encoding='utf-8') as f:
        f.write(log_content)
    print(f"[{thread_name}] 📝 日誌已儲存至: {log_filepath}")
    
    return result['success']

def main():
    parser = argparse.ArgumentParser(
        description="PDF 自動解析工具 - 只需提供輸出目錄",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  # 自動處理第一篇（會自動找到 docs/01 和章節名稱）
  python parse_pdf_auto.py knowledge/examination/01
  
  # 指定線程數
  python parse_pdf_auto.py knowledge/examination/01 --max-workers 10
  
  # 使用不同模型
  python parse_pdf_auto.py knowledge/examination/02 --model "anthropic/claude-3.5-sonnet"
        """
    )
    
    parser.add_argument(
        "output_dir",
        type=str,
        help="輸出目錄（例如：knowledge/examination/01）"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="anthropic/claude-sonnet-4.5",
        help="使用的 OpenRouter 模型（預設: anthropic/claude-sonnet-4.5）"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="併發處理的最大線程數（預設: 5）"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="日誌目錄（預設: logs）"
    )
    
    args = parser.parse_args()
    
    # 自動偵測章節資訊
    chapter_info = detect_chapter_from_output_dir(args.output_dir)
    if not chapter_info:
        print(f"❌ 錯誤: 無法從 '{args.output_dir}' 識別章節")
        print("支援的目錄格式：knowledge/examination/01, knowledge/examination/02, ...")
        return
    
    chapter_id, chapter_name, docs_dir = chapter_info
    output_dir = Path(args.output_dir)
    input_dir = Path(docs_dir)
    
    print(f"{'='*60}")
    print(f"🤖 PDF 自動解析工具")
    print(f"{'='*60}")
    print(f"📚 章節編號: {chapter_id}")
    print(f"📖 章節名稱: {chapter_name}")
    print(f"📁 PDF 目錄: {input_dir}")
    print(f"💾 輸出目錄: {output_dir}")
    print(f"🧠 AI 模型: {args.model}")
    print(f"🔧 併發線程: {args.max_workers}")
    print(f"{'='*60}\n")
    
    # 檢查輸入目錄
    if not input_dir.is_dir():
        print(f"❌ 錯誤: PDF 目錄不存在: {input_dir}")
        return
    
    # 建立日誌目錄
    log_dir = Path(args.log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # 找出所有 PDF 檔案
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ 錯誤: 在 {input_dir} 中找不到 PDF 檔案")
        return
    
    print(f"📚 找到 {len(pdf_files)} 個 PDF 檔案\n")
    
    success_count = 0
    fail_count = 0
    
    # 準備任務列表
    tasks = []
    for pdf_path in pdf_files:
        output_path = output_dir / pdf_path.with_suffix(".json").name
        tasks.append((pdf_path, output_path, chapter_name, args.model, log_dir))
    
    # 使用 ThreadPoolExecutor 進行併發處理
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_pdf = {
            executor.submit(process_pdf_file, task[0], task[1], task[2], task[3], task[4]): task[0]
            for task in tasks
        }
        
        for future in as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"\n❌ 處理 {pdf_path.name} 時發生異常: {e}")
                fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 批次處理完成")
    print(f"✅ 成功: {success_count} 個")
    print(f"❌ 失敗: {fail_count} 個")
    print(f"🔧 使用線程數: {args.max_workers}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
