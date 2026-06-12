# LifeNova - Application Mobile

Application mobile de développement personnel et de suivi d'objectifs, propulsée par l'IA.

## 🚀 Fonctionnalités

### Écrans Principaux

- **Splash Screen** : Animation de chargement avec le logo LifeNova
- **Accueil** : Vue d'ensemble avec accès rapide aux fonctionnalités
- **Assistant IA** : Chat interactif pour obtenir conseils et réponses
- **Tâches** : Gestion des to-do avec analyse IA des tâches
- **Motivation** : Citation du jour, conseils de productivité et actions rapides

### Fonctionnalités Clés

#### 🧠 Assistant IA
- Chat conversationnel style ChatGPT
- Réponses contextuelles sur la motivation, la productivité, l'organisation
- Historique de conversation sauvegardé localement
- Suggestions rapides par thématique

#### 📅 Gestion des Tâches
- Ajouter, modifier, supprimer des tâches
- Filtrer par statut (toutes, à faire, terminées)
- Analyse IA pour décomposer les tâches complexes
- Stockage local avec AsyncStorage

#### 💡 Motivation Quotidienne
- Citation du jour catégorisée
- Conseil IA personnalisé selon le jour
- Liste de conseils de productivité
- Actions rapides (Pomodoro, voir tâches, parler à l'IA)
- Partage de citations

## 🎨 Design System

### Couleurs
- **Rose** : `#FF4FA3` - Couleur primaire
- **Orange** : `#FF8A3D` - Couleur secondaire
- **Bleu** : `#2D7CFF` - Couleur d'accent
- **Blanc** : `#FFFFFF` - Fond et texte

### Typographie
- Police système (SF Pro sur iOS, Roboto sur Android)
- Hiérarchie claire avec tailles et poids variés

## 📁 Structure du Projet

```
LifeNova/
├── src/
│   ├── screens/              # Écrans de l'application
│   │   ├── SplashScreen.js   # Écran de chargement
│   │   ├── HomeScreen.js     # Page d'accueil
│   │   ├── AssistantScreen.js # Assistant IA (chat)
│   │   ├── TasksScreen.js    # Gestion des tâches
│   │   ├── MotivationScreen.js # Motivation quotidienne
│   │   └── index.js
│   ├── components/           # Composants réutilisables (à venir)
│   ├── navigation/           # Configuration de navigation
│   │   ├── AppNavigator.js   # Navigateur principal
│   │   └── index.js
│   ├── constants/            # Constantes globales
│   │   ├── colors.js         # Palette de couleurs
│   │   ├── theme.js          # Design system complet
│   │   └── index.js
│   ├── config/               # Configuration API
│   │   ├── api.js            # Config et endpoints API
│   │   └── index.js
│   └── services/             # Services métier
│       ├── storageService.js # Gestion AsyncStorage
│       ├── aiService.js      # Service IA (simulation MVP)
│       └── index.js
├── assets/                   # Images, icônes, polices
├── App.js                    # Point d'entrée principal
├── app.json                  # Configuration Expo
├── package.json              # Dépendances
├── .env                      # Variables d'environnement
├── .env.example              # Exemple de fichier .env
└── .gitignore                # Fichiers à ignorer par Git
```

## 🛠️ Technologies

- **React Native** : Framework mobile cross-platform
- **Expo** : Outils de développement et de build
- **React Navigation** : Navigation entre écrans (Stack + Tabs)
- **AsyncStorage** : Stockage local des données
- **Expo Vector Icons** : Icônes Ionicons

## 🏃 Démarrage

### Prérequis
- Node.js (v16 ou supérieur)
- npm ou yarn
- Expo CLI (`npm install -g expo-cli`)

### Installation

1. Cloner le dépôt
```bash
git clone <repository-url>
cd LifeNova
```

2. Installer les dépendances
```bash
npm install
```

3. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

4. Démarrer l'application
```bash
npm start
```

5. Exécuter sur un appareil
- **iOS Simulator** : Appuyez sur `i` dans le terminal
- **Android Emulator** : Appuyez sur `a` dans le terminal
- **Appareil physique** : Scannez le QR code avec l'app Expo Go

## 🔧 Commandes disponibles

```bash
npm start          # Démarrer le serveur de développement
npm run android    # Lancer sur Android
npm run ios        # Lancer sur iOS
npm run web        # Lancer sur le web
```

## 📱 Architecture de Navigation

```
Splash Screen (3 secondes)
       ↓
Main Tabs (Navigation par onglets)
├── Accueil (Home)
├── Assistant (IA Chat)
├── Tâches (To-Do)
└── Motivation (Daily)
```

## 🔒 Sécurité

- Le fichier `.env` contient des données sensibles et ne doit **JAMAIS** être commité
- Utilisez `.env.example` comme modèle pour la configuration
- La `DATABASE_URL` est configurée pour le futur backend

## 🔄 Prochaines Étapes (Phase 3)

- [ ] Intégration API IA réelle (OpenAI/Anthropic)
- [ ] Authentification utilisateur
- [ ] Synchronisation cloud des données
- [ ] Notifications push
- [ ] Mode sombre
- [ ] Statistiques avancées
- [ ] Export des données
- [ ] Widget iOS/Android

## 📄 Licence

Propriétaire - Tous droits réservés

---

**LifeNova** - Votre vie, réinventée ✨

*Développé avec ❤️ par LifeNova Team*