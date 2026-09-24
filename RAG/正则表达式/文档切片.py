"""
RAG切片脚本
将《精通正则表达式》各章节按语义边界切片，输出到 rag_chunks 文件夹
每个切片包含章节来源、序号等信息，适合用于向量检索
"""
import os
import re

INPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\chapters"
OUTPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\rag_chunks"

# 章节文件列表（保持顺序）
CHAPTER_FILES = [
    "00_前言与序言.txt",
    "00_目录.txt",
    "01_正则表达式入门.txt",
    "02_入门示例拓展.txt",
    "03_正则表达式的特性和流派概览.txt",
    "04_表达式的匹配原理.txt",
    "05_正则表达式实用技巧.txt",
    "06_打造高效正则表达式.txt",
    "07_Perl.txt",
    "08_Java.txt",
    "09_NET.txt",
    "10_PHP.txt",
    "11_索引.txt",
]

CHAPTER_NAMES = {
    "00_前言与序言": "前言与序言",
    "00_目录": "目录",
    "01_正则表达式入门": "第1章：正则表达式入门",
    "02_入门示例拓展": "第2章：入门示例拓展",
    "03_正则表达式的特性和流派概览": "第3章：正则表达式的特性和流派概览",
    "04_表达式的匹配原理": "第4章：表达式的匹配原理",
    "05_正则表达式实用技巧": "第5章：正则表达式实用技巧",
    "06_打造高效正则表达式": "第6章：打造高效正则表达式",
    "07_Perl": "第7章：Perl",
    "08_Java": "第8章：Java",
    "09_NET": "第9章：.NET",
    "10_PHP": "第10章：PHP",
    "11_索引": "索引",
}

# 最小切片字符数
MIN_CHUNK_SIZE = 300
# 目标切片字符数
TARGET_CHUNK_SIZE = 800
# 最大切片字符数
MAX_CHUNK_SIZE = 1500
# overlap 字符数
OVERLAP_SIZE = 80


def clean_text(text):
    """清理OCR噪声"""
    # 移除行尾的孤立反斜线（OCR格式噪声）
    text = re.sub(r'\\(?!\\)\s*\n', '\n', text)
    # 规范化换行
    text = re.sub(r'\r\n?', '\n', text)
    # 超过两个连续换行压缩为两个
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除BOM
    text = text.replace('\ufeff', '')
    return text


def extract_section_title(line):
    """判断一行是否为章节标题，返回标题文本或None"""
    line = line.strip()
    if not line:
        return None
    
    # 匹配常见标题模式
    patterns = [
        r'^第[一二三四五六七八九十\d]+章[：:].+',
        r'^[A-Z][a-zA-Z\s]+$',  # 英文标题（全大写或首字母大写）
        r'^[A-Z][a-zA-Z\s]+$',
        r'^[A-Z][a-z]+\s+[A-Z][a-z]+',  # 像 Perl 风格标题
        r'^[\u4e00-\u9fff]{2,15}$',  # 纯中文短标题（可能为小节标题）
    ]
    
    for pat in patterns:
        if re.match(pat, line):
            return line
    return None


def find_split_points(text):
    """
    找到文本中的自然分段点
    返回分段起始位置列表
    """
    split_positions = [0]
    lines = text.split('\n')
    
    char_positions = []
    pos = 0
    for line in lines:
        char_positions.append(pos)
        pos += len(line) + 1  # +1 for \n
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # 标题行作为分段点
        title = extract_section_title(stripped)
        if title and len(stripped) < 60:
            split_positions.append(char_positions[i])
            continue
        
        # 以 ● ◆ □ ■ 等特殊符号开头的行
        if stripped and stripped[0] in '●◆□■◎○△▲☆★→←↑↓⇒⇐①②③④⑤⑥⑦⑧⑨⑩注':
            split_positions.append(char_positions[i])
            continue
        
        # 表格说明行
        if re.match(r'^表\d+[-–—].+|^图\d+[-–—].+', stripped):
            split_positions.append(char_positions[i])
            continue
        
        # "注\d+:" 开头的注释
        if re.match(r'^注\d+[：:]', stripped):
            split_positions.append(char_positions[i])
            continue
    
    # 去重并排序
    split_positions = sorted(set(split_positions))
    return split_positions


def chunk_text(text, chapter_id):
    """
    将文本按语义边界切片，并在 chunk 间加入重叠
    """
    split_points = find_split_points(text)
    chunks = []
    
    for i in range(len(split_points)):
        start = split_points[i]
        end = split_points[i + 1] if i + 1 < len(split_points) else len(text)
        
        segment = text[start:end].strip()
        if not segment:
            continue
        
        # 如果段落超过最大长度，进一步按段落切分
        if len(segment) > MAX_CHUNK_SIZE:
            sub_chunks = split_large_segment(segment)
            for sub in sub_chunks:
                if len(sub) >= MIN_CHUNK_SIZE:
                    chunks.append(sub)
        elif len(segment) >= MIN_CHUNK_SIZE:
            chunks.append(segment)
        else:
            # 太小的段落合并到前一个chunk
            if chunks:
                chunks[-1] = chunks[-1] + '\n\n' + segment
            else:
                chunks.append(segment)
    
    # 合并过小的chunk
    merged = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHUNK_SIZE:
            merged[-1] = merged[-1] + '\n\n' + chunk
        else:
            merged.append(chunk)
    
    return merged


def split_large_segment(segment):
    """将过长段落按自然边界拆分"""
    paragraphs = segment.split('\n\n')
    chunks = []
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current) + len(para) < TARGET_CHUNK_SIZE:
            current = (current + '\n\n' + para).strip()
        else:
            if current:
                chunks.append(current)
            # 如果单个段落超过目标大小，按行拆分
            if len(para) > MAX_CHUNK_SIZE:
                sub_chunks = split_long_paragraph(para)
                chunks.extend(sub_chunks)
            else:
                current = para
    
    if current:
        chunks.append(current)
    
    return chunks


def split_long_paragraph(paragraph):
    """按句子边界拆分过长段落"""
    lines = paragraph.split('\n')
    chunks = []
    current = ""
    
    for line in lines:
        line = line.rstrip()
        if len(current) + len(line) < TARGET_CHUNK_SIZE:
            current = (current + '\n' + line).strip()
        else:
            if current:
                chunks.append(current)
            current = line
    
    if current:
        chunks.append(current)
    
    return chunks


def build_chunk_header(chapter_id, chunk_idx, total_chunks, chapter_name):
    """构建切片头部元信息"""
    return f"""---
章节: {chapter_name}
章节ID: {chapter_id}
切片序号: {chunk_idx}/{total_chunks}
---
"""


def process_file(filename):
    """处理单个章节文件"""
    filepath = os.path.join(INPUT_DIR, filename)
    chapter_id = filename.replace('.txt', '')
    chapter_name = CHAPTER_NAMES.get(chapter_id, chapter_id)
    
    if not os.path.exists(filepath):
        print(f"  [跳过] 文件不存在: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    text = clean_text(text)
    chunks = chunk_text(text, chapter_id)
    
    # 为每个章节创建子目录
    chapter_dir = os.path.join(OUTPUT_DIR, chapter_id)
    os.makedirs(chapter_dir, exist_ok=True)
    
    for i, chunk in enumerate(chunks):
        header = build_chunk_header(chapter_id, i + 1, len(chunks), chapter_name)
        chunk_filename = f"{chapter_id}_chunk_{i+1:04d}.txt"
        chunk_path = os.path.join(chapter_dir, chunk_filename)
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(header + chunk)
    
    print(f"  {chapter_name}: {len(chunks)} 个切片")
    return len(chunks)


def generate_index():
    """生成总索引文件"""
    index_lines = ["# RAG切片总索引\n", f"# 生成时间: {__import__('datetime').datetime.now()}\n\n"]
    
    total = 0
    for chapter_dir in sorted(os.listdir(OUTPUT_DIR)):
        dir_path = os.path.join(OUTPUT_DIR, chapter_dir)
        if not os.path.isdir(dir_path):
            continue
        
        chapter_name = CHAPTER_NAMES.get(chapter_dir, chapter_dir)
        files = sorted(os.listdir(dir_path))
        total += len(files)
        
        index_lines.append(f"\n## {chapter_name}\n")
        index_lines.append(f"路径: {dir_path}\n")
        index_lines.append(f"切片数: {len(files)}\n")
        
        for f in files:
            chunk_path = os.path.join(dir_path, f)
            with open(chunk_path, 'r', encoding='utf-8') as cf:
                first_lines = cf.read(300)
            # 取第一段实际内容作为摘要
            preview = first_lines.split('---\n')[-1].strip()[:80].replace('\n', ' ')
            index_lines.append(f"  - {f}: {preview}...\n")
    
    index_lines.insert(1, f"总切片数: {total}\n")
    
    index_path = os.path.join(OUTPUT_DIR, "_index.txt")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.writelines(index_lines)
    
    return total


def main():
    print("=" * 60)
    print("RAG 切片工具 - 《精通正则表达式》")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total_chunks = 0
    for filename in CHAPTER_FILES:
        count = process_file(filename)
        if count:
            total_chunks += count
    
    print(f"\n生成索引...")
    generate_index()
    
    print(f"\n完成！总计生成 {total_chunks} 个切片")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
