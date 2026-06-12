/**
 * Composant Background - Version Premium
 * Arrière-plan élégant avec dégradés subtils et éléments décoratifs
 * Design inspiré de Notion, Calm, Duolingo, Airbnb
 */

import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { colors } from '../constants';

const Background = ({ children, style, variant = 'default' }) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Fade-in doux au montage
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 800,
      useNativeDriver: true,
    }).start();
  }, []);

  const getBackgroundStyle = () => {
    switch (variant) {
      case 'gradient':
        return styles.gradientBackground;
      case 'solid':
        return styles.solidBackground;
      case 'splash':
        return styles.splashBackground;
      default:
        return styles.defaultBackground;
    }
  };

  return (
    <Animated.View style={[styles.container, getBackgroundStyle(), style, { opacity: fadeAnim }]}>
      {/* Éléments décoratifs pour le dégradé */}
      {variant === 'gradient' && (
        <>
          <View style={styles.decorCircle1} />
          <View style={styles.decorCircle2} />
          <View style={styles.decorCircle3} />
        </>
      )}
      
      {/* Élément décoratif pour le splash */}
      {variant === 'splash' && (
        <View style={styles.splashDecor} />
      )}

      {/* Contenu */}
      {children}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background.primary,
  },

  // Style par défaut - blanc pur
  defaultBackground: {
    backgroundColor: colors.background.primary,
  },

  // Style solide - fond gris très clair
  solidBackground: {
    backgroundColor: colors.background.secondary,
  },

  // Style dégradé - avec cercles décoratifs
  gradientBackground: {
    backgroundColor: colors.background.primary,
    overflow: 'hidden',
  },

  // Style splash - pour l'écran de démarrage
  splashBackground: {
    backgroundColor: colors.primary.white,
    overflow: 'hidden',
  },

  // Cercles décoratifs pour le dégradé
  decorCircle1: {
    position: 'absolute',
    top: -150,
    right: -150,
    width: 400,
    height: 400,
    borderRadius: 200,
    backgroundColor: `${colors.primary.rose}08`,
  },

  decorCircle2: {
    position: 'absolute',
    bottom: -100,
    left: -100,
    width: 350,
    height: 350,
    borderRadius: 175,
    backgroundColor: `${colors.primary.orange}06`,
  },

  decorCircle3: {
    position: 'absolute',
    top: '40%',
    right: -80,
    width: 250,
    height: 250,
    borderRadius: 125,
    backgroundColor: `${colors.primary.blue}06`,
  },

  // Élément décoratif pour le splash
  splashDecor: {
    position: 'absolute',
    top: -120,
    right: -120,
    width: 350,
    height: 350,
    borderRadius: 175,
    backgroundColor: 'rgba(255, 79, 163, 0.08)',
  },
});

export default Background;