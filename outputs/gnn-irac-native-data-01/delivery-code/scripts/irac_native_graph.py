"""Versioned input-only graph CLI. Never fits models or overwrites output."""
import argparse
import json
from pathlib import Path
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import load_input
from legal_bench.rules_verdict_v1.irac_graph_builder_v1 import build_input_graph

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['validate','build'])
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(); data=load_input(args.input)
    if args.command=='validate':print('INPUT_CONTRACT_OK_NOT_SEMANTIC_CERTIFICATION');return
    if args.output is None:parser.error('build requires --output')
    graph=build_input_graph(data)
    # Exclusive creation protects frozen and historical runs.
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(graph,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(graph['graph_hash'])

if __name__=='__main__':main()
