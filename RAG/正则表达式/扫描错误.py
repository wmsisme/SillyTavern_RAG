"""
全面扫描《精通正则表达式》章节文件中的 OCR 错误
输出所有需要修复的条目
"""
import os
import re
import sys

INPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\chapters"

CHAPTER_FILES = sorted([
    f for f in os.listdir(INPUT_DIR) 
    if f.endswith('.txt')
])

# ============================================================
# 错误模式列表
# ============================================================

# 1. 管道符 | 被 OCR 误识别 - 在正则表达式上下文中，| 应该是元字符
PIPE_CONTEXTS = [
    # \( 开头，后面是字母或数字，然后被误认的| ，再后面是字母
    # 比如 (First|1st) 中的 | 被识别成 1/I/l/i
    (r'\(([A-Za-z]+)([il1I\|])([A-Za-z0-9]+)\)', r'(\1|\3)'),
    # 英文多选分支：Word[il1I]Word
    (r'([A-Z][a-z]+)([il1I\|])([A-Z][a-z]+)', r'\1|\3'),
    # [字符组中不该出现的|误认]
    # 正则表达式中独立的 \| 和 正常的| 上下文
]

ERRORS = []

def report(filename, line_num, context, problem, suggestion):
    ERRORS.append({
        'file': filename,
        'line': line_num,
        'context': context.strip(),
        'problem': problem,
        'suggestion': suggestion
    })

def scan_file(filepath):
    filename = os.path.basename(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        lineno = i + 1
        
        # ---- 模式1: 管道符 | 被OCR误识别为普通字符 ----
        # 在正则表达式模式字符串中找疑似被破坏的管道符
        
        # 模式1a: 在括号内，两个单词之间用1/I/l连接 -> 应该是 |
        # 例: (First11st) -> (First|1st)
        m = re.search(r'\(([A-Za-z_]+)([il1I])([A-Za-z_0-9]+)\)', line)
        if m and len(m.group(1)) > 1 and len(m.group(3)) > 1:
            old = m.group(0)
            new = '(' + m.group(1) + '|' + m.group(3) + ')'
            if old != new:
                report(filename, lineno, old, '括号内疑似管道符误认', new)
        
        # 模式1b: 两个大写开头单词之间用非|字符连接  
        # 例: FromISubject -> From|Subject
        m = re.search(r'([A-Z][a-z]{2,})([il1I])([A-Z][a-z]{2,})', line)
        if m:
            old = m.group(0)
            # 检查是否是已知的非正则表达式文本
            if not any(w in line for w in ['Unix', 'DOS', 'MacOS', 'Windows', 'ASCII', 'HTML', 'ISO', 'PHP', 'Perl', 
                   'ANSI', 'CSV', 'API', 'URL', 'NFA', 'DFA', 'POSIX', 'EOS', 'PCRE', 'UTF', 'GNU', 
                   'SQL', 'XML', 'Tcl', 'BSD', 'TCP', 'NFS', 'Lisp', 'UNIX', 'CSDN', 'VB.NET',
                   'ECMAScript', 'VBScript', 'ECMA', 'Tiny', 'MSIL', 'DLL', 'Emacs', 'AT&T']):
                new = m.group(1) + '|' + m.group(3)
                if old != new:
                    report(filename, lineno, old, '大写单词间疑似管道符误认', new)
        
        # 模式1c: 数字和单词之间 - 如 4th|4 -> 4th14 / 4thl4 等
        # 这种情况需要更精确匹配
        
        # 模式1d: 小写单词间 - more general  
        m = re.search(r'([a-z]{3,})([il1I])([a-z]{3,})', line)
        if m:
            old = m.group(0)
            # 排除已知英文单词混合
            known_words = {'email', 'mailbox', 'command', 'shell', 'subject', 'egrep'}
            if not any(w in old.lower() for w in known_words):
                # 检查是否是正则中的多选结构
                if re.search(r'[/m(]\s*$', line) or 'regex' in line.lower() or '正则' in line or '表达式' in line:
                    new = m.group(1) + '|' + m.group(3)
                    if old != new:
                        report(filename, lineno, old, '小写单词间疑似管道符误认', new)
        
        # ---- 模式2: SARGV -> $ARGV ----
        if 'SARGV' in line:
            report(filename, lineno, line.strip()[:80], 'SARGV->$ARGV', line.replace('SARGV', '$ARGV').strip()[:80])
        
        # ---- 模式3: 字符组中的0误认为O ----
        # [Ff][Rr][0o] -> [Ff][Rr][Oo]
        
        # ---- 模式4: egre p -> egrep ----
        if re.search(r'egre\s+p\b', line):
            report(filename, lineno, line.strip()[:80], "egre p->egrep", re.sub(r'egre\s+p\b', 'egrep', line).strip()[:80])
        
        # ---- 模式5: 反斜线丢失 ----
        # \1b -> \1\b (反向引用后缺少\b的反斜线)
        if re.search(r'\\([1-9])b\b', line):
            m2 = re.search(r'\\([1-9])b\b', line)
            # 只在正则表达式上下文中
            if 'regex' in line.lower() or '正则' in line or 's/' in line or 'm/' in line:
                report(filename, lineno, line.strip()[:80], '反向引用后缺少\\b反斜线', 
                       line.replace('\\'+m2.group(1)+'b', '\\'+m2.group(1)+'\\b').strip()[:80])
        
        # ---- 模式6: 表格中的|被误认----
        # 表格行如 |xxx|xxx| 的| 
        
        # ---- 模式7: 中文引号" " 混用 (保持原样，这是中文排版) ----
        
        # ---- 模式8: \sl -> \s+ (空白字符简记) ----
        if re.search(r'\\s[liI1]', line):
            report(filename, lineno, line.strip()[:80], '\\s+l被误认', 
                   re.sub(r'\\s[liI1]', r'\\s+', line).strip()[:80])

def main():
    for fname in CHAPTER_FILES:
        filepath = os.path.join(INPUT_DIR, fname)
        scan_file(filepath)
    
    print(f"共发现 {len(ERRORS)} 个潜在错误\n")
    
    # 按文件分组输出
    current_file = None
    for err in ERRORS:
        if err['file'] != current_file:
            current_file = err['file']
            print(f"\n{'='*60}")
            print(f"文件: {current_file}")
            print(f"{'='*60}")
        print(f"  L{err['line']:>5d}: [{err['problem']}]")
        print(f"         原文: {err['context'][:100]}")
        print(f"         建议: {err['suggestion'][:100]}")
        print()

if __name__ == '__main__':
    main()
