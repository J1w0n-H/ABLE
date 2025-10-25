#!/bin/bash
# 배치 완료 대기 후 자동 분석

LOG_DIR="/root/Git/ARVO2.0/v2.3/build_agent/log"
REPORT="/root/Git/ARVO2.0/v2.3/BATCH_ANALYSIS_REPORT.md"

echo "⏳ 배치 스크립트 완료 대기 중..."

# 배치 스크립트가 끝날 때까지 대기
while ps aux | grep "run_v2.3_batch.sh" | grep -v grep > /dev/null; do
    sleep 30
done

echo "🎉 배치 스크립트 완료! 분석 시작..."

# 분석 시작
python3 << 'PYEOF'
import os
import re
import json
from datetime import datetime

LOG_DIR = "/root/Git/ARVO2.0/v2.3/build_agent/log"
OUTPUT_DIR = "/root/Git/ARVO2.0/v2.3/build_agent/output"

projects = []

# 각 프로젝트별 분석
for log_file in sorted(os.listdir(LOG_DIR)):
    if not log_file.endswith('.log'):
        continue
    
    log_path = os.path.join(LOG_DIR, log_file)
    project_name = log_file.replace('_HEAD.log', '').replace('_', '/')
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    # 기본 정보
    info = {
        'name': project_name,
        'log_file': log_file,
        'log_size': len(content.split('\n')),
        'success': 'Congratulations' in content,
        'completed': 'Spend totally' in content,
    }
    
    # 턴 수
    info['turns'] = content.count('ENVIRONMENT REMINDER')
    
    # 실행 시간
    time_match = re.search(r'Spend totally ([\d.]+)', content)
    info['time'] = float(time_match.group(1)) if time_match else 0
    
    # 에러 패턴
    info['critical_errors'] = content.count('🚨 CRITICAL ERRORS')
    info['suggested_fixes'] = content.count('💡 SUGGESTED FIXES')
    
    # configure/make 실행 횟수
    info['configure_count'] = content.count('./configure')
    info['make_count'] = content.count('make -j4')
    
    # 특이사항 감지
    issues = []
    if info['configure_count'] > 10:
        issues.append(f"configure 과다 실행 ({info['configure_count']}회)")
    if info['turns'] > 50:
        issues.append(f"턴 수 과다 ({info['turns']}턴)")
    if '/usr/bin/file' in content:
        issues.append("file 명령어 누락")
    if 'syntax error near unexpected token' in content:
        issues.append("bash syntax error 루프")
    if content.count('cat /repo/configure.ac') > 3:
        issues.append("configure.ac 반복 읽기")
    
    info['issues'] = issues
    
    projects.append(info)

# 리포트 생성
with open('/root/Git/ARVO2.0/v2.3/BATCH_ANALYSIS_REPORT.md', 'w') as f:
    f.write("# ARVO 2.3 배치 실행 분석 보고서\n\n")
    f.write(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("---\n\n")
    
    # 전체 요약
    f.write("## 📊 전체 요약\n\n")
    total = len(projects)
    success = sum(1 for p in projects if p['success'])
    completed = sum(1 for p in projects if p['completed'])
    
    f.write(f"- **총 프로젝트**: {total}개\n")
    f.write(f"- **성공**: {success}개 ({success*100//total if total else 0}%)\n")
    f.write(f"- **완료**: {completed}개\n")
    f.write(f"- **진행 중**: {total - completed}개\n\n")
    
    # 프로젝트별 상세
    f.write("## 📋 프로젝트별 상세 결과\n\n")
    f.write("| 프로젝트 | 상태 | 시간(초) | 턴 수 | 로그(줄) | 특이사항 |\n")
    f.write("|----------|------|----------|-------|---------|----------|\n")
    
    for p in projects:
        status = "✅" if p['success'] else ("❌" if p['completed'] else "🔄")
        time_str = f"{p['time']:.1f}" if p['time'] > 0 else "진행중"
        issues_str = ", ".join(p['issues'][:2]) if p['issues'] else "-"
        f.write(f"| {p['name']} | {status} | {time_str} | {p['turns']} | {p['log_size']} | {issues_str} |\n")
    
    f.write("\n---\n\n")
    
    # 문제 프로젝트 분석
    f.write("## 🚨 문제 프로젝트 상세 분석\n\n")
    problem_projects = [p for p in projects if p['issues']]
    
    if problem_projects:
        for p in problem_projects:
            f.write(f"### {p['name']}\n\n")
            f.write(f"**문제점**:\n")
            for issue in p['issues']:
                f.write(f"- {issue}\n")
            f.write(f"\n**통계**:\n")
            f.write(f"- 턴 수: {p['turns']}\n")
            f.write(f"- configure 실행: {p['configure_count']}회\n")
            f.write(f"- make 실행: {p['make_count']}회\n")
            f.write(f"- CRITICAL ERRORS: {p['critical_errors']}회\n")
            f.write(f"- SUGGESTED FIXES: {p['suggested_fixes']}회\n")
            f.write("\n")
    else:
        f.write("✅ 모든 프로젝트가 정상적으로 실행되었습니다.\n\n")
    
    f.write("---\n\n")
    
    # 개선 권장사항
    f.write("## 💡 개선 권장사항\n\n")
    
    if any('/usr/bin/file' in str(p.get('issues', [])) for p in projects):
        f.write("### 1. error_parser.py 개선 적용 확인\n")
        f.write("- `/usr/bin/file` 감지 로직이 제대로 작동하는지 확인 필요\n\n")
    
    if any('syntax error' in str(p.get('issues', [])) for p in projects):
        f.write("### 2. split_cmd.py 개선 적용 확인\n")
        f.write("- if/then/fi 금지 로직이 작동하는지 확인 필요\n\n")
    
    if any('configure.ac 반복' in str(p.get('issues', [])) for p in projects):
        f.write("### 3. 프롬프트 ERROR RESPONSE 효과 확인\n")
        f.write("- 최상단 ERROR RESPONSE가 LLM 행동에 영향을 주는지 확인 필요\n\n")

print("✅ 분석 보고서 생성 완료!")
print(f"위치: /root/Git/ARVO2.0/v2.3/BATCH_ANALYSIS_REPORT.md")
PYEOF

echo "✅ 분석 완료! 보고서를 확인하세요."

