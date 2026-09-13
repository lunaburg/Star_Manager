from __future__ import annotations
import argparse, json, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'apps' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))
import extract_ts4_package_fbx as extractor

def no_filter(mesh, coverage):
    return mesh, {
        'applied': False,
        'source_vertices': mesh['vertex_count'],
        'source_triangles': mesh['triangle_count'],
        'removed_vertices': 0,
        'removed_triangles': 0,
        'reason': 'disabled_for_diagnosis',
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    extractor.filter_mesh_by_alpha_coverage = no_filter
    manifest = extractor.extract_lod0_fbx(args.package.resolve(), args.output_dir.resolve())
    print(json.dumps({'ok': True, 'output_dir': str(args.output_dir.resolve()), 'exports': manifest['exports']}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
