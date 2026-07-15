"""
Pipeline complet ML AgriDec (3 etapes) :

  1) download_datasets.py      → telecharge One Acre Fund + LSMS-ISA
  2) build_agridec_dataset.py  → adapte (mois observes → labels Oui/Non)
  3) train_agridec_model.py    → entraine le modele Random Forest

Usage (depuis la racine du projet) :
  python ml/scripts/run_ml_pipeline.py
  python ml/scripts/run_ml_pipeline.py --skip-download   # si raw/ deja rempli
  python ml/scripts/run_ml_pipeline.py --force-download
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _run(script_name: str, argv: list[str] | None = None) -> None:
    path = SCRIPTS / script_name
    if not path.exists():
        raise SystemExit(f'Script introuvable : {path}')
    print()
    print('=' * 60)
    print(f'>> {script_name}')
    print('=' * 60)
    old_argv = sys.argv
    try:
        sys.argv = [str(path), *(argv or [])]
        runpy.run_path(str(path), run_name='__main__')
    finally:
        sys.argv = old_argv


def main() -> None:
    parser = argparse.ArgumentParser(description='Pipeline ML AgriDec complet.')
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Ne pas telecharger (utilise les fichiers deja dans ml/datasets/raw/).',
    )
    parser.add_argument(
        '--force-download',
        action='store_true',
        help='Force le re-telechargement des datasets bruts.',
    )
    args = parser.parse_args()

    print('=== Pipeline ML AgriDec ===')
    print('1) Telechargement  2) Adaptation  3) Entrainement')

    if not args.skip_download:
        dl_argv = ['--force'] if args.force_download else []
        _run('download_datasets.py', dl_argv)
    else:
        print('\n[skip] Telechargement ignore (--skip-download)')

    _run('build_agridec_dataset.py')
    _run('train_agridec_model.py')

    print()
    print('Pipeline termine.')
    print('Modele : ml/artifacts/agridec_model.joblib')


if __name__ == '__main__':
    main()
