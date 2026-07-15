"""
Télécharge les datasets bruts utilisés pour entraîner AgriDec.

Sources :
  1) One Acre Fund — enquête maïs Afrique (Zenodo 11122388)
  2) LSMS-ISA — Plotcrop + Plot (Banque mondiale, Zenodo 15773365)

Fichiers écrits dans ml/datasets/raw/ :
  - one_acre_fund_maize.csv
  - lsms_plotcrop.dta
  - lsms_plot.dta

Usage (depuis la racine du projet) :
  python ml/scripts/download_datasets.py
  python ml/scripts/download_datasets.py --force   # re-télécharger même si présent

Ensuite :
  python ml/scripts/build_agridec_dataset.py   # adaptation → agridec_training.csv
  python ml/scripts/train_agridec_model.py     # entraînement du modèle
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / 'ml' / 'datasets' / 'raw'

# URLs officielles de téléchargement (mêmes liens que dans README.md)
DATASETS = [
    {
        'name': 'One Acre Fund — Maize survey 2016-2022',
        'url': (
            'https://zenodo.org/records/11122388/files/'
            'One_Acre_Fund_MEL_maize_survey_data_2016-2022.csv?download=1'
        ),
        'filename': 'one_acre_fund_maize.csv',
        # Taille approximative (~5.6 Mo) — pour info uniquement
        'approx_mb': 5.6,
    },
    {
        'name': 'LSMS-ISA — Plotcrop (semis, récolte, chocs)',
        'url': (
            'https://zenodo.org/records/15773365/files/'
            'Plotcrop_dataset.dta?download=1'
        ),
        'filename': 'lsms_plotcrop.dta',
        'approx_mb': 246.0,
    },
    {
        'name': 'LSMS-ISA — Plot (irrigation, sol)',
        'url': (
            'https://zenodo.org/records/15773365/files/'
            'Plot_dataset.dta?download=1'
        ),
        'filename': 'lsms_plot.dta',
        'approx_mb': 249.0,
    },
]


def _format_mb(num_bytes: int) -> str:
    return f'{num_bytes / (1024 * 1024):.1f} Mo'


def download_file(url: str, dest: Path, force: bool = False) -> bool:
    """
    Télécharge un fichier avec barre de progression simple.
    Retourne True si un téléchargement a eu lieu, False si déjà présent (skip).
    """
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f'  [OK] Deja present : {dest.name} ({_format_mb(dest.stat().st_size)})')
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Fichier temporaire pour éviter un fichier corrompu en cas d'interruption
    tmp = dest.with_suffix(dest.suffix + '.part')

    print(f'  Telechargement : {dest.name}')
    print(f'  URL : {url}')

    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            total = response.headers.get('Content-Length')
            total = int(total) if total else None
            downloaded = 0
            chunk_size = 1024 * 256  # 256 Ko

            with open(tmp, 'wb') as out:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        msg = (
                            f'\r  Progression : {pct}% '
                            f'({_format_mb(downloaded)} / {_format_mb(total)})'
                        )
                    else:
                        msg = f'\r  Recu : {_format_mb(downloaded)}'
                    sys.stdout.write(msg)
                    sys.stdout.flush()

        print()  # saut de ligne après la barre

        # Vérifie que le téléchargement n'est pas tronqué
        if total is not None and tmp.stat().st_size != total:
            tmp.unlink(missing_ok=True)
            raise IOError(
                f'Telechargement incomplet : {_format_mb(tmp.stat().st_size)} '
                f'sur {_format_mb(total)} attendus'
            )

        if dest.exists():
            dest.unlink()
        tmp.rename(dest)
        print(f'  [OK] Sauve : {dest} ({_format_mb(dest.stat().st_size)})')
        return True

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f'  [ERREUR] Echec telechargement {dest.name} : {exc}') from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Telecharge One Acre Fund + LSMS-ISA pour AgriDec.'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-telecharge meme si les fichiers existent deja.',
    )
    args = parser.parse_args(argv)

    print('=== Telechargement des datasets AgriDec ===')
    print(f'Dossier cible : {RAW_DIR}')
    print()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for item in DATASETS:
        print(f"- {item['name']} (~{item['approx_mb']} Mo)")
        download_file(item['url'], RAW_DIR / item['filename'], force=args.force)
        print()

    print('Termine. Prochaine etape :')
    print('  python ml/scripts/build_agridec_dataset.py')
    print('  python ml/scripts/train_agridec_model.py')


if __name__ == '__main__':
    main()
