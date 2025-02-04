
# Cahier des charges du projet AltaLock

## Objectif du projet 
Développer une application de sécurité AltaLock qui utilise la reconnaissance faciale pour protéger un PC des accès non autorisés.

## Fonctionnalités principales
- Authentification par reconnaissance faciale via webcam
- Blocage de session si visage non reconnu  
- Ajout/suppression de visages autorisés
- Alertes email et vocales en cas d'intrusion
- Gestion des utilisateurs (inscription, connexion, gestion des visages)
- Gestion des paramétres (nb de détections de suite avant blocage, nb de farme a tréter par seconde, email destinataire des alertes, mot a pronancer pour l'alerte vocale, connection avec une page sharepoint pour récupérer toutes les images/ nom dedans)  

## Architecture technique 
- Front-end : HTML/CSS/JS 
- Back-end : Python avec bibliothèques OpenCV, Dlib, face_recognition
- API REST pour communication front-end/back-end
- Conversion en exécutable avec electronjs

## Livrable
- Code source de l'application (HTML/CSS/JS/Python)
- Exécutable autonome pour Windows
- Documentation utilisateur et technique

## Étapes principales du projet
1. Mise en place de l'environnement de développement 
2. Développement du front-end (pages web, UI)
3. Développement du back-end (reconnaissance faciale, actions)
4. Développement de l'API de communication 
5. Intégration front-end / back-end
6. Conversion en exécutable
7. Tests, débogage et optimisations
8. Rédaction de la documentation
