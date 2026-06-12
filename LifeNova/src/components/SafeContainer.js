/**
 * SafeContainer - Composant wrapper pour une gestion optimale des Safe Areas
 * 
 * Ce composant utilise react-native-safe-area-context pour une meilleure
 * compatibilité iOS, en particulier avec les encoches (notch) et les iPhones
 * modernes avec Dynamic Island.
 * 
 * Utilisation:
 * <SafeContainer>
 *   {children}
 * </SafeContainer>
 */

import React from 'react';
import { View, StyleSheet, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../constants';

const SafeContainer = ({ 
  children, 
  style, 
  backgroundColor, 
  edges = ['top', 'bottom'],
  statusBarStyle = 'dark',
  statusBarHidden = false,
}) => {
  return (
    <SafeAreaView 
      style={[styles.container, { backgroundColor: backgroundColor || colors.background.primary }, style]} 
      edges={edges}
    >
      <StatusBar 
        barStyle={statusBarStyle === 'dark' ? 'dark-content' : 'light-content'} 
        hidden={statusBarHidden}
        backgroundColor="transparent"
        translucent={false}
      />
      {children}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});

export default SafeContainer;