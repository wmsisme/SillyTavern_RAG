"""
《精通正则表达式》章节文件OCR错误全面修复脚本
只修复正则表达式上下文中的OCR错误，不误改普通英文单词
"""
import os
import re

INPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\chapters"

CHAPTER_FILES = sorted([
    f for f in os.listdir(INPUT_DIR)
    if f.endswith('.txt')
])

fix_log = []

def log_fix(filename, lineno, desc, old_part, new_part):
    fix_log.append(f"[{filename}:L{lineno}] {desc}: '{old_part}' -> '{new_part}'")

def fix_file(filepath):
    filename = os.path.basename(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    changes = 0
    
    fixed_lines = []
    for i, line in enumerate(lines):
        lineno = i + 1
        original = line
        
        # ================================================================
        # 修复规则（按优先级排序）
        # ================================================================
        
        # ---- R1: SARGV -> $ARGV (Perl 特殊变量) ----
        if 'SARGV' in line:
            line = line.replace('SARGV', '$ARGV')
            if line != original:
                log_fix(filename, lineno, 'SARGV->$ARGV', 'SARGV', '$ARGV')
                changes += 1
        
        # ---- R2: \sl / \si -> \s+ (正则中的空白匹配简记) ----
        # \sl / \si 出现在正则表达式上下文中
        if re.search(r'\\s[liI1]', line):
            line = re.sub(r'\\s[liI1]', r'\\s+', line)
            if line != original:
                log_fix(filename, lineno, '\\sl/\\si -> \\s+', 
                       re.search(r'\\s[liI1]', original).group(), r'\s+')
                changes += 1
        
        # ---- R3: (\1b) -> (\1\b) 反向引用后缺反斜线 ----
        # 正则上下文中，\1b 应该是 \1\b
        if re.search(r'\\([1-9])b\b', line):
            # 检查是否在正则上下文：包含 s/ 或 m/ 或正则相关关键词
            if any(kw in line for kw in ['s/', 'm/', 'regex', '正则', '表达式', '匹配', '替换']):
                line = re.sub(r'\\([1-9])b\b', r'\\\1\\b', line)
                if line != original:
                    log_fix(filename, lineno, '(\\1b)->(\\1\\b)', 
                           re.search(r'\\[1-9]b', original).group(), 
                           re.search(r'\\[1-9]\\b', line).group() if re.search(r'\\[1-9]\\b', line) else '')
                    changes += 1
        
        # ---- R4: egre p -> egrep ----
        if re.search(r'egre\s+p\b', line):
            line = re.sub(r'egre\s+p\b', 'egrep', line)
            if line != original:
                log_fix(filename, lineno, 'egre p->egrep', 'egre p', 'egrep')
                changes += 1
        
        # ---- R5: [Ff][Rr][0o][Mm] -> [Ff][Rr][Oo][Mm] ----
        if '[0o]' in line and ('[Mm]' in line or '[Rr]' in line):
            # 上下文：匹配 from 的大小写变体
            if re.search(r'\[Ff\]\[Rr\]\[0o\]', line):
                line = line.replace('[0o]', '[Oo]')
                if line != original:
                    log_fix(filename, lineno, '字符组[0o]->[Oo]', '[0o]', '[Oo]')
                    changes += 1
        
        # ---- R6: Perl逻辑错误 eq"C" or eq"C" -> eq"C" or eq"c" ----
        if 'eq"C"or $type eq"C"' in line or 'eq"C" or $type eq"C"' in line:
            line = line.replace('eq"C"or $type eq"C"', 'eq"C"or $type eq"c"')
            line = line.replace('eq"C" or $type eq"C"', 'eq"C" or $type eq"c"')
            if line != original:
                log_fix(filename, lineno, '逻辑错误: eq"C"or eq"C"->eq"C"or eq"c"', 
                       'eq"C"or $type eq"C"', 'eq"C"or $type eq"c"')
                changes += 1
        
        # ---- R7: 智能引号版本的逻辑错误 ----
        if '\u201cC\u201d or $type eq\u201cC\u201d' in line:
            line = line.replace('\u201cC\u201d or $type eq\u201cC\u201d', '\u201cC\u201d or $type eq\u201cc\u201d')
            if line != original:
                log_fix(filename, lineno, '逻辑错误(智能引号): eq"C"or eq"C"->eq"C"or eq"c"', '', '')
                changes += 1
        
        # ---- R8: 正则表达式中括号内的管道符被误认为1/I/i/l ----
        # 此规则修复 01_正则表达式入门.txt 中已确认的问题
        # 使用精确替换，避免误伤普通英文单词
        
        # R8a: (First11st) -> (First|1st) 
        old = '(First11st)'
        new = '(First|1st)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (First11st)->(First|1st)', old, new)
            changes += 1
        
        # R8b: (Firl1)st -> (Fir|1)st
        old = '( Firl1)st'
        new = '( Fir|1)st'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (Firl1)st->(Fir|1)st', old, new)
            changes += 1
        
        # R8c: (FirstI1st) -> (First|1st)
        old = '( FirstI1st)'
        new = '( First|1st)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (FirstI1st)->(First|1st)', old, new)
            changes += 1
        
        # R8d: (firl1)st -> (fir|1)st
        old = '( firl1)st)'
        new = '( fir|1)st)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (firl1)st->(fir|1)st', old, new)
            changes += 1
        
        # R8e: (Geoff1Jeff)(reylery) -> (Geoff|Jeff)(rey|ery)
        old = '(Geoff1Jeff)(reylery)'
        new = '(Geoff|Jeff)(rey|ery)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (Geoff1Jeff)(reylery)->(Geoff|Jeff)(rey|ery)', old, new)
            changes += 1
        
        # R8f: FromISubject -> From|Subject
        old = 'FromISubject'
        new = 'From|Subject'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: FromISubject->From|Subject', old, new)
            changes += 1
        
        # R8g: FromiSubject -> From|Subject
        old = 'FromiSubject'
        new = 'From|Subject'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: FromiSubject->From|Subject', old, new)
            changes += 1
        
        # R8h: iDate -> |Date (在正则上下文中)
        old = 'iDate:'
        new = '|Date:'
        if old in line and ('regex' in line.lower() or '正则' in line or '表达式' in line or '^From' in line):
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: iDate:->|Date:', old, new)
            changes += 1
        
        # R8i: FromiSubject IDate: -> From|Subject|Date:
        old = 'FromiSubject IDate:'
        new = 'From|Subject|Date:'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: FromiSubject IDate:->From|Subject|Date:', old, new)
            changes += 1
        
        # R8j: FromISubject iDate -> From|Subject|Date
        old = 'FromISubject iDate'
        new = 'From|Subject|Date'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: FromISubject iDate->From|Subject|Date', old, new)
            changes += 1
        
        # R8k: (GeolJe) -> (Geo|Je)
        old = '(GeolJe)'
        new = '(Geo|Je)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (GeolJe)->(Geo|Je)', old, new)
            changes += 1
        
        # R8l: (reylery) -> (rey|ery)
        old = '(reylery)]'
        new = '(rey|ery)]'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (reylery)]->(rey|ery)]', old, new)
            changes += 1
        
        # R8m: (reler)y -> (re|er)y
        old = '(reler)y'
        new = '(re|er)y'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: (reler)y->(re|er)y', old, new)
            changes += 1

        # R8n: Jeffrey IGeoffery IJeffery IGeoffrey -> Jeffrey|Geoffery|Jeffery|Geoffrey
        old = 'Jeffrey IGeoffery IJeffery IGeoffrey'
        new = 'Jeffrey|Geoffery|Jeffery|Geoffrey'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: Jeffrey IGeoffery IJeffery IGeoffrey->Jeffrey|Geoffery|Jeffery|Geoffrey', old, new)
            changes += 1
        
        # R8o: greyIgray -> grey|gray 
        old = 'greyIgray'
        new = 'grey|gray'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: greyIgray->grey|gray', old, new)
            changes += 1
        
        # R8p: graIey -> gra|ey
        old = 'graIey'
        new = 'gra|ey'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: graIey->gra|ey', old, new)
            changes += 1
        
        # R8q: ^ FromiSubject IDate: -> ^From|Subject|Date:
        old = '^ FromiSubject IDate:'
        new = '^From|Subject|Date:'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: ^ FromiSubject IDate:->^From|Subject|Date:', old, new)
            changes += 1
        
        # R8r: ^(FromISubject |Date) -> ^(From|Subject|Date)
        old = '^(FromISubject |Date)'
        new = '^(From|Subject|Date)'
        if old in line:
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: ^(FromISubject |Date)->^(From|Subject|Date)', old, new)
            changes += 1
        
        # R8s: "graj 或者'eyj" -> 保留（这是中文描述，无需修复），但检查graley -> gra|ey
        old = 'graley'
        new = 'gra|ey'
        if old in line and ('或者' in line or '意思' in line):
            line = line.replace(old, new)
            log_fix(filename, lineno, '管道符OCR: graley->gra|ey', old, new)
            changes += 1
        
        # ---- R9: [^\\"] 被OCR破坏 ----
        # [^\\"I 应该有 \\. 多选分支，但 OCR 可能破坏了
        # '[^"\n]' 等模式
        
        # ---- R10: 修复多余空格：mailbox-fil e -> mailbox-file ----
        if 'mailbox-fil e' in line:
            line = line.replace('mailbox-fil e', 'mailbox-file')
            if line != original:
                log_fix(filename, lineno, '空格: mailbox-fil e->mailbox-file', 'mailbox-fil e', 'mailbox-file')
                changes += 1
        
        # ---- R11: 修复 ma ilbox-file -> mailbox-file ----
        if 'ma ilbox-fil' in line:
            line = line.replace('ma ilbox-fil e', 'mailbox-file')
            line = line.replace('ma ilbox-file', 'mailbox-file')
            if line != original:
                log_fix(filename, lineno, '空格: ma ilbox-file->mailbox-file', 'ma ilbox-file', 'mailbox-file')
                changes += 1
        
        # ---- R12: command-shell 空格问题----
        if 's hell' in line and 'hell' in line:
            line = line.replace('s hell', 'shell')
            if line != original:
                log_fix(filename, lineno, '空格: s hell->shell', 's hell', 'shell')
                changes += 1
        
        fixed_lines.append(line)
    
    # 写回文件
    new_content = '\n'.join(fixed_lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return changes


def main():
    print("=" * 70)
    print("《精通正则表达式》章节文件 OCR 错误修复工具")
    print("=" * 70)
    
    total_changes = 0
    for fname in CHAPTER_FILES:
        filepath = os.path.join(INPUT_DIR, fname)
        changes = fix_file(filepath)
        if changes > 0:
            print(f"\n[{fname}] 修复 {changes} 处错误")
        total_changes += changes
    
    print(f"\n{'='*70}")
    print(f"修复日志 ({total_changes} 处):")
    print(f"{'='*70}")
    for entry in fix_log:
        print(f"  {entry}")
    
    print(f"\n总计修复 {total_changes} 处错误")

if __name__ == '__main__':
    main()
