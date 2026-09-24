"""
第二轮修复：深度扫描并修复正则表达式上下文中的管道符OCR错误
使用上下文感知策略
"""
import os
import re

INPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\chapters"

CHAPTER_FILES = sorted([
    f for f in os.listdir(INPUT_DIR)
    if f.endswith('.txt')
])

# 已知需要保护的正确英文单词（不能把其中的I/l/1替换成|）
PROTECTED_WORDS = {
    'Subject', 'Unix', 'DOS', 'MacOS', 'Windows', 'ASCII', 'HTML', 'ISO', 'PHP', 'Perl',
    'ANSI', 'CSV', 'API', 'URL', 'NFA', 'DFA', 'POSIX', 'EOS', 'PCRE', 'UTF', 'GNU',
    'SQL', 'XML', 'Tcl', 'BSD', 'TCP', 'NFS', 'Lisp', 'UNIX', 'CSDN', 'VB.NET',
    'ECMAScript', 'VBScript', 'ECMA', 'Tiny', 'MSIL', 'DLL', 'Emacs', 'AT&T',
    'Python', 'Java', 'Ruby', 'MySQL', 'GNU', 'Berkeley', 'Unicode',
    'First', 'Jeffrey', 'Geoffery', 'Jeffery', 'Geoffrey', 'Geoff', 'Jeff',
    'From', 'Date', 'Subject', 'Bob', 'Robert',
    'Jan', 'Feb', 'Mar', 'Apr', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
    'Email', 'Mail', 'Image', 'Input', 'Output',
}

PIPE_CORRUPTED = {}  # {corrupted_form: corrected_form}

def find_regex_context_lines(lines):
    """找出所有正则表达式上下文的行"""
    context_lines = set()
    in_code_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 检测代码块
        if re.match(r'^(% |\$ |8 |    |\t)', stripped):
            in_code_block = True
            context_lines.add(i)
        elif in_code_block and stripped == '':
            in_code_block = False
        elif in_code_block:
            context_lines.add(i)
        
        # 正则表达式关键词
        if any(kw in stripped for kw in [
            '正则表达式', '表达式', '元字符', '匹配', '捕获', '回溯',
            'regex', 'pattern', 'match', 'capture', 'backtrack',
        ]):
            context_lines.add(i)
        
        # 包含正则表达式分隔符
        if re.search(r'(m/|s/|qr/|/i\b|/g\b|/x\b|/m\b)', stripped):
            context_lines.add(i)
        
        # 包含括号组 + 疑似多选结构
        if re.search(r'\([^)]*[A-Z][a-z]+[iIl1][A-Z][a-z]+[^)]*\)', stripped):
            context_lines.add(i)
    
    return context_lines


def find_corrupted_alternations(line):
    """
    在给定行中查找被OCR破坏的管道符
    返回 [(start_pos, corrupted_text, corrected_text)]
    """
    fixes = []
    
    # 模式1: 括号内，两个首字母大写的词之间用小写字母或数字连接 -> 应该是|
    # 例: (FromISubject) -> (From|Subject), (BobIRobert) -> (Bob|Robert)
    pattern1 = re.finditer(r'\(([A-Z][a-z]{2,})([iIl1])([A-Z][a-z]{2,})\)', line)
    for m in pattern1:
        left, sep, right = m.group(1), m.group(2), m.group(3)
        full = m.group(0)
        if left not in PROTECTED_WORDS and right not in PROTECTED_WORDS:
            continue
        if sep in ('i', 'I', 'l', '1'):
            corrected = f'({left}|{right})'
            if corrected != full:
                fixes.append((m.start(), full, corrected))
    
    # 模式2: 两个大写单词之间用 I/l/1/i 连接 -> 应为 |
    # 需要更精确：只在正则表达式描述上下文中
    pattern2 = re.finditer(r'([A-Z][a-z]{2,})([Ii1l])([A-Z][a-z]{2,})', line)
    for m in pattern2:
        left, sep, right = m.group(1), m.group(2), m.group(3)
        full = m.group(0)
        # 排除特定已知单词序列
        if full in ('MacOS', 'VB.NET', 'GNUEmacs', 'GNUAwk', 'GNUEgrep'):
            continue
        # 只有在两个都是正则/编程相关术语时才替换
        regex_terms = {
            'From', 'Subject', 'Date', 'Bob', 'Robert', 'Jeffrey', 'Geoffery', 
            'Jeffery', 'Geoffrey', 'First', 'Reset', 'Set', 'July', 'Jun',
            'Color', 'Colour', 'Mr', 'Mrs', 'Dr', 'Jan', 'Feb', 'Mar', 'Apr',
            'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
        }
        if (left in regex_terms and right in regex_terms) or \
           (re.search(r'(正则|表达式|匹配|替换|多选|或|或者)', line)):
            if sep in ('I', 'i', 'l', '1'):
                corrected = f'{left}|{right}'
                if corrected != full:
                    fixes.append((m.start(), full, corrected))
    
    # 模式3: 英文单词+数字组合的多选分支 如 (First11st), (4th14)
    pattern3 = re.finditer(r'\(([A-Z][a-z]+)([1liI])(\d+[a-z]*)\)', line)
    for m in pattern3:
        left, sep, right = m.group(1), m.group(2), m.group(3)
        full = m.group(0)
        corrected = f'({left}|{right})'
        if corrected != full:
            fixes.append((m.start(), full, corrected))
    
    # 模式4: 数字+后缀 通过 I/l 连接 如 4th14
    pattern4 = re.finditer(r'(\d+[a-z]{1,3})([iIl1])(\d+[a-z]*)', line)
    for m in pattern4:
        left, sep, right = m.group(1), m.group(2), m.group(3)
        full = m.group(0)
        if sep in ('I', 'i', 'l', '1') and \
           (re.search(r'(正则|表达式|多选|alternation|or)', line, re.IGNORECASE)):
            corrected = f'{left}|{right}'
            if corrected != full:
                fixes.append((m.start(), full, corrected))
    
    # 模式5: 查找被空格分隔的 | 残留 - 如 "Jeffrey IGeoffery" -> "Jeffrey|Geoffery"
    # 这在描述正则多选结构时出现
    pattern5 = re.finditer(r'([A-Z][a-z]{2,})\s+I\s*([A-Z][a-z]{2,})', line)
    for m in pattern5:
        left, right = m.group(1), m.group(2)
        full = m.group(0)
        regex_terms = {
            'From', 'Subject', 'Date', 'Bob', 'Robert', 'Jeffrey', 
            'Geoffery', 'Jeffery', 'Geoffrey', 'Reset', 'Set',
            'First', 'Last', 'Mr', 'Mrs', 'Dr',
        }
        if left in regex_terms and right in regex_terms:
            corrected = f'{left}|{right}'
            if corrected != full.strip():
                fixes.append((m.start(), full, corrected))
    
    # 去重（同一位置只保留一个修复）
    unique_fixes = []
    seen_positions = set()
    for fix in fixes:
        if fix[0] not in seen_positions:
            unique_fixes.append(fix)
            seen_positions.add(fix[0])
    
    return unique_fixes


def main():
    print("=" * 70)
    print("第二轮：深度扫描并修复管道符OCR错误")
    print("=" * 70)
    
    total_fixes = 0
    
    for fname in CHAPTER_FILES:
        filepath = os.path.join(INPUT_DIR, fname)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        context_lines = find_regex_context_lines(lines)
        
        file_fixes = []
        for i, line in enumerate(lines):
            if i not in context_lines:
                continue
            
            fixes = find_corrupted_alternations(line)
            for pos, old, new in fixes:
                file_fixes.append((i, pos, old, new, line.strip()[:80]))
        
        if file_fixes:
            print(f"\n[{fname}] 发现 {len(file_fixes)} 处疑似错误:")
            # 从后往前修复，避免位置偏移
            file_fixes.sort(key=lambda x: (-x[0], -x[1]))
            
            for lineno, pos, old, new, ctx in file_fixes:
                line = lines[lineno]
                lines[lineno] = line[:pos] + new + line[pos + len(old):]
                print(f"  L{lineno+1:>5d}: '{old}' -> '{new}'")
                print(f"         上下文: {ctx}")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            total_fixes += len(file_fixes)
    
    print(f"\n总计修复 {total_fixes} 处")
    
    if total_fixes == 0:
        print("\n所有已知OCR错误已修复完毕！")

if __name__ == '__main__':
    main()
