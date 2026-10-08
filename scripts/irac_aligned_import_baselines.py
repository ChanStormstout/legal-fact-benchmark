#!/usr/bin/env python3
"""Import complete browser JSON; only an explicit citation-marker escape is repaired."""
import sys,json,re,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_tasks import ROOT,put

def main():
    for p in sorted((ROOT/'web').glob('baseline-*-page.txt')):
        cid=p.stem.split('-')[1];dest=ROOT/'web'/f'baseline-{cid}.json'
        if dest.exists():continue
        text=p.read_text();start=text.find('{\n  "case_id"');end=text.rfind('\n}')
        if start<0 or end<start:continue
        raw=text[start:end+2];patched,n=re.subn(r':chatgpt-content-reference\{index="(\d+)"\}',lambda m:':chatgpt-content-reference{index=\\"'+m.group(1)+'\\"}',raw)
        try:d=json.loads(patched)
        except json.JSONDecodeError:continue
        if str(d.get('case_id'))!=cid:continue
        put(dest,d);put(ROOT/'web'/f'baseline-{cid}-format-processing.json',dict(operation='Remove visible UI wrapper and escape unescaped quotes inside citation marker; no string value, fact, status or source quote changed.',citation_markers_escaped=n,raw_page_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        print('content-preserving format import',cid)
if __name__=='__main__':main()
