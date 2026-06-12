/**
 * LifeNova - Application Mobile
 * 
 * Point d'entrée principal de l'application
 * 
 * Architecture:
 * - src/screens: Tous les écrans de l'application
 * - src/components: Composants réutilisables
 * - src/navigation: Configuration de navigation
 * - src/constants: Couleurs, thème, constantes globales
 * - src/config: Configuration API et services
 * - src/i18n: Gestion des langues et traductions
 */

import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { AppNavigator } from './src/navigation';
import { Background } from './src/components';
import { LanguageProvider } from './src/i18n/useTranslation';
import { colors } from './src/constants';

export default function App() {
  return (
    <LanguageProvider>
      <Background variant="gradient">
        <StatusBar style="dark" backgroundColor={colors.background.primary} />
        <AppNavigator />
      </Background>
    </LanguageProvider>
  );
}
