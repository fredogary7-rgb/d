/**
 * Thème LifeNova
 * Configuration des styles globaux et du design system
 */

import colors from './colors';

export default {
  colors,
  
  // Espacements (système de grille 4px)
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
    xxxl: 64,
  },
  
  // Typographie
  typography: {
    fontFamily: {
      regular: 'System',
      medium: 'System',
      bold: 'System',
    },
    sizes: {
      xs: 10,
      sm: 12,
      md: 14,
      lg: 16,
      xl: 18,
      xxl: 24,
      xxxl: 32,
      hero: 40,
    },
    lineHeights: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
    },
    weights: {
      regular: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
  },
  
  // Rayons des bordures
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    xxl: 24,
    full: 9999,
  },
  
  // Ombres
  shadows: {
    sm: {
      shadowColor: colors.shadow.light,
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 1,
    },
    md: {
      shadowColor: colors.shadow.medium,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 6,
      elevation: 3,
    },
    lg: {
      shadowColor: colors.shadow.dark,
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.15,
      shadowRadius: 12,
      elevation: 5,
    },
  },
  
  // Durées d'animation (en ms)
  animation: {
    fast: 150,
    normal: 250,
    slow: 400,
  },
  
  // Breakpoints (pour le responsive)
  breakpoints: {
    mobile: 320,
    tablet: 768,
    desktop: 1024,
  },
};