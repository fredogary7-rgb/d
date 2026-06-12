# Configuration iOS - LifeNova

Ce document explique les améliorations apportées pour une meilleure compatibilité iOS.

## Problèmes résolus

### 1. Safe Areas (Zones de sécurité)
**Problème:** L'application n'était pas correctement structurée sur iOS, en particulier sur les iPhones avec encoche (notch) ou Dynamic Island.

**Solution:** 
- Création d'un composant `SafeContainer` qui utilise `react-native-safe-area-context`
- Tous les écrans utilisent maintenant ce composant pour une gestion optimale des safe areas
- Le contenu ne sera plus caché derrière la barre d'état, l'encoche ou le bas de l'écran

### 2. Configuration iOS améliorée
**Modifications dans `app.json`:**
- Ajout du `bundleIdentifier` iOS: `com.lifenova.app`
- Configuration de la barre d'état iOS (`UIStatusBarStyle`)
- Ajout des permissions iOS (caméra, bibliothèque de photos, localisation)
- Configuration du chiffrement non exempté
- Ajout des associated domains pour les universal links

### 3. Configuration Babel
**Nouveau fichier `babel.config.js`:**
- Configuration appropriée pour `react-native-reanimated`
- Le plugin doit être en dernier dans la liste des plugins

## Comment exécuter l'application sur iOS

### 1. Installer les dépendances
```bash
npm install
```

### 2. Démarrer le serveur de développement
```bash
npm start
```

### 3. Lancer sur iOS
```bash
npm run ios
```

## Notes importantes

### Pour les développeurs
- Tous les écrans doivent utiliser le composant `SafeContainer` au lieu de `SafeAreaView` de `react-native`
- Le `SafeContainer` offre une meilleure gestion des safe areas sur iOS
- Pour les écrans avec clavier (comme AssistantScreen), continuer à utiliser `KeyboardAvoidingView` avec les offsets appropriés

### Structure du SafeContainer
```jsx
import { SafeContainer } from './src/components';

<SafeContainer 
  backgroundColor={colors.background.primary} 
  statusBarStyle="dark"
  edges={['top', 'bottom']}
>
  {children}
</SafeContainer>
```

### Propriétés du SafeContainer:
- `backgroundColor`: Couleur de fond (défaut: `colors.background.primary`)
- `statusBarStyle`: Style de la barre d'état ('dark' ou 'light')
- `edges`: Tableau des bords à gérer (défaut: `['top', 'bottom']`)
- `statusBarHidden`: Masquer la barre d'état (défaut: `false`)

## Tests recommandés

Testez l'application sur:
1. iPhone avec encoche (iPhone X et plus récent)
2. iPhone avec Dynamic Island (iPhone 14 Pro et plus récent)
3. iPad (pour vérifier le support tablette)
4. Simulateur iOS avec différentes tailles d'écran

## Ressources

- [React Native Safe Area Context](https://github.com/th3rdwave/react-native-safe-area-context)
- [Expo Configuration](https://docs.expo.dev/versions/v56.0.0/)
- [iOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/the-basics)