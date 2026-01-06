# Instructions pour créer la version CPU-ONLY

## Problème
Si vous avez `dlib` compilé avec CUDA dans votre environnement actuel, PyInstaller va tenter d'inclure les dépendances CUDA et l'exécutable ne fonctionnera pas sans les DLLs cuDNN.

## Solution : Environnement Python CPU-only propre

### Étape 1 : Créer un nouvel environnement conda

```bash
# Créer un environnement propre Python 3.10
conda create -n altalock-cpu python=3.10 -y
conda activate altalock-cpu
```

### Étape 2 : Installer les outils de build

```bash
# Installer CMake et compilateurs (nécessaires pour dlib)
conda install -c conda-forge cmake -y

# Sur Windows, assurez-vous d'avoir Visual Studio Build Tools installé
```

### Étape 3 : Installer dlib CPU-ONLY

**IMPORTANT** : Installer dlib AVANT face_recognition pour s'assurer qu'il est compilé sans CUDA

```bash
# Forcer l'installation de dlib sans CUDA
conda install -c conda-forge "dlib=*=*cpu*" -y
```

### Étape 4 : Installer les dépendances

```bash
pip install -r requirements-cpu.txt
```

### Étape 5 : Installer PyInstaller

```bash
pip install pyinstaller
```

### Étape 6 : Vérifier l'installation

```bash
python -c "import dlib; print('CUDA disponible:', dlib.DLIB_USE_CUDA if hasattr(dlib, 'DLIB_USE_CUDA') else False)"
```

Devrait afficher : `CUDA disponible: False`

### Étape 7 : Build la release

```bash
# Assurez-vous d'être dans l'environnement altalock-cpu
conda activate altalock-cpu

# Lancer le build CPU
python build_release_cpu.py
```

## Résultat attendu

- Backend : ~50-100 Mo
- Package complet : ~200-300 Mo
- Installeur fonctionnel : `AltaLock-2.1.0 Setup.exe`

## Troubleshooting

### Le backend ne démarre toujours pas
Vérifiez les logs dans la console Electron. Si vous voyez des erreurs sur des DLLs manquantes, c'est que dlib a été compilé avec CUDA.

### Taille trop importante (> 500 Mo)
L'environnement n'est pas propre. Recommencez avec un nouvel environnement conda.

### Erreur de compilation de dlib
Installez Visual Studio Build Tools :
https://visualstudio.microsoft.com/downloads/ (Build Tools for Visual Studio 2022)
