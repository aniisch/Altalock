"""
Script complet pour créer une release CPU-ONLY de AltaLock
Usage: python build_release_cpu.py

Cette version:
- N'inclut PAS les DLLs cuDNN (CPU seulement)
- Package plus léger (~200-300 Mo au lieu de ~1.5 Go)
- Génère un installeur Squirrel ET un ZIP portable

Ce script:
1. Build le backend Python CPU-only avec PyInstaller
2. Package l'application Electron avec Electron Forge
"""
import os
import subprocess
import shutil
import sys
from pathlib import Path

def run_command(cmd, cwd=None, shell=True):
    """Execute une commande et affiche la sortie"""
    print(f"\n> {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if result.returncode != 0:
        print(f"ERREUR: Commande échouée avec code {result.returncode}")
        return False
    return True

def build():
    print("=" * 60)
    print("BUILD RELEASE CPU-ONLY - AltaLock v2.1")
    print("=" * 60)
    print("Version légère sans support GPU")
    print("Taille estimée: ~200-300 Mo")
    print("=" * 60)

    root = Path(__file__).parent

    # Nettoyer les anciens builds
    print("\nNettoyage des anciens builds...")
    dirs_to_clean = ["out", "dist", "build"]
    for dir_name in dirs_to_clean:
        dir_path = root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   Supprimé: {dir_name}/")

    # Vérifier qu'on est dans le bon dossier
    if not (root / "package.json").exists():
        print("ERREUR: package.json non trouvé à la racine.")
        return False

    if not (root / "electron" / "main.js").exists():
        print("ERREUR: electron/main.js non trouvé.")
        return False

    # Étape 1: Build du backend Python CPU-ONLY
    print("\n" + "=" * 60)
    print("ÉTAPE 1: Build du backend Python CPU-ONLY")
    print("=" * 60)

    build_backend = root / "build_backend_cpu.py"
    if not build_backend.exists():
        print(f"ERREUR: {build_backend} non trouvé!")
        return False

    if not run_command(f"python {build_backend}", cwd=root):
        print("ERREUR: Build backend échoué!")
        return False

    # Copier le backend dans electron/backend pour electron-forge
    backend_src = root / "dist" / "altalock-backend.exe"
    backend_dest = root / "electron" / "backend"

    if backend_dest.exists():
        shutil.rmtree(backend_dest)
    backend_dest.mkdir(exist_ok=True)

    if backend_src.exists():
        print(f"\nCopie du backend vers {backend_dest}")
        shutil.copy2(backend_src, backend_dest / "altalock-backend.exe")

        # Afficher la taille
        size_mb = backend_src.stat().st_size / (1024 * 1024)
        print(f"   Taille du backend: {size_mb:.1f} Mo")

        # Copier aussi le dossier data s'il existe
        data_src = root / "data"
        if data_src.exists():
            data_dest = backend_dest / "data"
            if data_dest.exists():
                shutil.rmtree(data_dest)
            shutil.copytree(data_src, data_dest)
            print(f"   Copié: data/")
    else:
        print(f"ERREUR: Backend non trouvé: {backend_src}")
        return False

    # Étape 2: Installer les dépendances npm
    print("\n" + "=" * 60)
    print("ÉTAPE 2: Installation des dépendances npm")
    print("=" * 60)

    if not run_command("npm install", cwd=root):
        print("ERREUR: npm install échoué!")
        return False

    # Étape 3: Package avec Electron Forge
    print("\n" + "=" * 60)
    print("ÉTAPE 3: Package avec Electron Forge")
    print("=" * 60)

    if sys.platform == "win32":
        make_cmd = "npm run make:win"
    elif sys.platform == "darwin":
        make_cmd = "npm run make"
    else:
        make_cmd = "npm run make:linux"

    if not run_command(make_cmd, cwd=root):
        print("ERREUR: Electron Forge make a échoué!")
        return False

    # Résumé
    print("\n" + "=" * 60)
    print("BUILD CPU-ONLY TERMINÉ AVEC SUCCÈS!")
    print("=" * 60)

    out_dir = root / "out" / "make"
    print(f"\nFichiers de distribution dans: {out_dir}")

    if out_dir.exists():
        total_size = 0
        for item in out_dir.rglob("*"):
            if item.is_file() and item.suffix in [".exe", ".zip", ".deb", ".rpm"]:
                size_mb = item.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"  - {item.name} ({size_mb:.1f} MB)")

        if total_size > 0:
            print(f"\nTaille totale: {total_size:.1f} MB")
            if total_size > 1000:
                print("ATTENTION: Le package dépasse 1 Go, l'installeur Squirrel risque de ne pas fonctionner!")

    print("\n" + "=" * 60)
    print("AVANTAGES VERSION CPU:")
    print("  ✓ Package léger (~200-300 Mo)")
    print("  ✓ Installeur Windows disponible")
    print("  ✓ Installation plus rapide")
    print("LIMITATION:")
    print("  - Pas de support GPU (détection sur CPU uniquement)")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
