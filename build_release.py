"""
Script complet pour créer une release de AltaLock
Usage: python build_release.py

Ce script:
1. Build le backend Python avec PyInstaller
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
    print("BUILD RELEASE - AltaLock v2.0")
    print("=" * 60)

    root = Path(__file__).parent
    frontend = root / "frontend"

    # Vérifier qu'on est dans le bon dossier
    if not (frontend / "package.json").exists():
        print("ERREUR: frontend/package.json non trouvé.")
        return False

    # Étape 1: Build du backend Python
    print("\n" + "=" * 60)
    print("ÉTAPE 1: Build du backend Python avec PyInstaller")
    print("=" * 60)

    # Importer et exécuter le build du backend
    build_backend = root / "build_backend.py"
    if not run_command(f"python {build_backend}", cwd=root):
        print("ERREUR: Build backend échoué!")
        return False

    # Étape 2: Installer les dépendances npm si nécessaire
    print("\n" + "=" * 60)
    print("ÉTAPE 2: Installation des dépendances npm")
    print("=" * 60)

    if not (frontend / "node_modules").exists():
        if not run_command("npm install", cwd=frontend):
            print("ERREUR: npm install échoué!")
            return False
    else:
        print("   node_modules existe déjà")

    # Étape 3: Package Electron
    print("\n" + "=" * 60)
    print("ÉTAPE 3: Package Electron avec Electron Forge")
    print("=" * 60)

    if sys.platform == "win32":
        make_cmd = "npm run make:win"
    elif sys.platform == "darwin":
        make_cmd = "npm run make:mac"
    else:
        make_cmd = "npm run make:linux"

    if not run_command(make_cmd, cwd=frontend):
        print("ERREUR: Electron Forge make a échoué!")
        return False

    # Résumé
    print("\n" + "=" * 60)
    print("BUILD TERMINÉ AVEC SUCCÈS!")
    print("=" * 60)

    out_dir = frontend / "out" / "make"
    print(f"\nFichiers de distribution dans: {out_dir}")

    if out_dir.exists():
        for item in out_dir.rglob("*"):
            if item.is_file() and item.suffix in [".exe", ".msi", ".zip", ".deb", ".rpm"]:
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"  - {item.name} ({size_mb:.1f} MB)")

    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
