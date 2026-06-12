/**
 * LifeNova - Hook useTranslation
 * Gestion de la langue et des traductions
 */

import React, { useState, useEffect, createContext, useContext } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations, defaultLanguage, getTranslation, isRTL } from './translations';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(defaultLanguage);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadLanguage();
  }, []);

  const loadLanguage = async () => {
    try {
      const savedLanguage = await AsyncStorage.getItem('language');
      if (savedLanguage && translations[savedLanguage]) {
        setLanguage(savedLanguage);
      }
    } catch (error) {
      console.error('Error loading language:', error);
    }
    setIsLoading(false);
  };

  const changeLanguage = async (newLang) => {
    if (translations[newLang]) {
      setLanguage(newLang);
      try {
        await AsyncStorage.setItem('language', newLang);
      } catch (error) {
        console.error('Error saving language:', error);
      }
    }
  };

  const t = (key) => getTranslation(language, key);

  const value = {
    language,
    setLanguage: changeLanguage,
    t,
    isLoading,
    isRTL: isRTL(language),
    languages: Object.keys(translations).map(key => ({
      code: key,
      name: translations[key].name,
      flag: translations[key].flag,
    })),
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
};

export default useTranslation;