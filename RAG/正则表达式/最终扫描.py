"""第三轮：全面最终扫描所有已知OCR残留错误"""
import os, re

INPUT_DIR = r"d:\code_item\酒馆rag\RAG\正则表达式\chapters"
FILES = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')])

fixes = []
for fname in FILES:
    fp = os.path.join(INPUT_DIR, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        lineno = i + 1
        
        # R1: 4th14 -> 4th|4
        m = re.search(r'4th[1Ii]4\b', line)
        if m:
            fixes.append((fname, lineno, m.group(), '4th|4', line.strip()[:80]))
        
        # R2: greyIgray -> grey|gray  
        if 'greyIgray' in line and 'grey|gray' not in line:
            fixes.append((fname, lineno, 'greyIgray', 'grey|gray', line.strip()[:80]))
        
        # R3: s hell -> shell
        m = re.search(r'\bs hell\b', line)
        if m:
            fixes.append((fname, lineno, 's hell', 'shell', line.strip()[:80]))

        # R4: egre p -> egrep
        m = re.search(r'egre\s+p\b', line)
        if m:
            fixes.append((fname, lineno, m.group(), 'egrep', line.strip()[:80]))

        # R5: SARGV 
        if 'SARGV' in line:
            fixes.append((fname, lineno, 'SARGV', '$ARGV', line.strip()[:80]))
        
        # R6: 在正则表达式的描述中,\\<和\\>被破坏
        # 这里我们检查\<和\> 的OCR问题
        
        # R7: [^…1 -> [^…] (方括号缺失)
        m = re.search(r'\[\^[^\]]+1\b', line)
        if m and ']' not in m.group():
            fixes.append((fname, lineno, m.group(), m.group()[:-1]+']', line.strip()[:80]))

        # R8: …] 被OCR识别为 …1
        m = re.search(r'\[\^?[\w\s\-.]+\d\b', line)
        if m:
            s = m.group()
            if s.endswith('1') and ']' not in s:
                fixed_s = s[:-1] + ']'
                if '正则' in line or 'regex' in line.lower():
                    fixes.append((fname, lineno, s, fixed_s, line.strip()[:80]))

print(f'Found {len(fixes)} potential issues:')
for f in fixes:
    print(f'  [{f[0]}:L{f[1]}] {f[2]} -> {f[3]}')
    print(f'    {f[4]}')
