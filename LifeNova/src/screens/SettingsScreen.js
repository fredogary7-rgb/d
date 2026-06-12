/**
 * Écran Paramètres LifeNova
 * Gestion des langues et préférences
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from '../i18n/useTranslation';
import { colors, theme } from '../constants';
import { SafeContainer } from '../components';

const SettingsScreen = ({ navigation }) => {
  const { t, language, setLanguage, languages, isRTL } = useTranslation();

  const handleLanguageChange = (langCode) => {
    if (langCode !== language) {
      setLanguage(langCode);
      Alert.alert(
        t('success'),
        `${t('language')} ${languages.find(l => l.code === langCode)?.name} ${t('selected')}`,
        [{ text: 'OK' }]
      );
    }
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>{t('settings')}</Text>
          <View style={styles.placeholder} />
        </View>

        {/* Section Langue */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="language" size={20} color={colors.primary.blue} />
            <Text style={styles.sectionTitle}>{t('language')}</Text>
          </View>

          <View style={styles.languageList}>
            {languages.map((lang) => (
              <TouchableOpacity
                key={lang.code}
                style={[
                  styles.languageItem,
                  language === lang.code && styles.languageItemActive,
                ]}
                onPress={() => handleLanguageChange(lang.code)}
                activeOpacity={0.7}
              >
                <Text style={styles.languageFlag}>{lang.flag}</Text>
                <View style={styles.languageInfo}>
                  <Text
                    style={[
                      styles.languageName,
                      language === lang.code && styles.languageNameActive,
                    ]}
                  >
                    {lang.name}
                  </Text>
                  {lang.code === 'ar' && (
                    <Text style={styles.languageNote}>RTL</Text>
                  )}
                </View>
                {language === lang.code && (
                  <Ionicons
                    name="checkmark-circle"
                    size={24}
                    color={colors.primary.blue}
                  />
                )}
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Section À propos */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="information-circle" size={20} color={colors.primary.orange} />
            <Text style={styles.sectionTitle}>À propos</Text>
          </View>

          <View style={styles.aboutCard}>
            <View style={styles.aboutLogoContainer}>
              <View style={styles.aboutLogo}>
                <Text style={styles.aboutLogoText}>LN</Text>
              </View>
            </View>
            <Text style={styles.aboutAppName}>{t('appName')}</Text>
            <Text style={styles.aboutVersion}>Version 1.0.0</Text>
            <Text style={styles.aboutDescription}>
              {t('slogan')}
            </Text>
          </View>
        </View>

        {/* Section Actions */}
        <View style={styles.section}>
          <TouchableOpacity style={styles.actionItem} onPress={() => {}}>
            <Ionicons name="shield-outline" size={22} color={colors.text.secondary} />
            <Text style={styles.actionText}>Politique de confidentialité</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.text.light} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionItem} onPress={() => {}}>
            <Ionicons name="document-text-outline" size={22} color={colors.text.secondary} />
            <Text style={styles.actionText}>Conditions d'utilisation</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.text.light} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionItem} onPress={() => {}}>
            <Ionicons name="help-circle-outline" size={22} color={colors.text.secondary} />
            <Text style={styles.actionText}>Aide et support</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.text.light} />
          </TouchableOpacity>
        </View>

        {/* Section Authentification */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="person" size={20} color={colors.primary.rose} />
            <Text style={styles.sectionTitle}>Compte</Text>
          </View>

          <TouchableOpacity
            style={[styles.actionItem, styles.loginButton]}
            onPress={() => navigation.navigate('Login')}
          >
            <Ionicons name="log-in" size={22} color={colors.primary.rose} />
            <Text style={[styles.actionText, styles.loginText]}>Se connecter</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.primary.rose} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionItem, styles.signupButton]}
            onPress={() => navigation.navigate('Login')}
          >
            <Ionicons name="person-add" size={22} color={colors.primary.white} />
            <Text style={[styles.actionText, styles.signupText]}>Créer un compte</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.primary.white} />
          </TouchableOpacity>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>LifeNova © 2024</Text>
          <Text style={styles.footerSubtext}>Made with ❤️</Text>
        </View>
      </ScrollView>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background.primary,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.lg,
    paddingBottom: theme.spacing.xxl,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.xl,
  },
  backButton: {
    padding: theme.spacing.sm,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.xxl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  placeholder: {
    width: 48,
  },
  section: {
    marginBottom: theme.spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  sectionTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
  },
  languageList: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
    ...theme.shadows.sm,
  },
  languageItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
  },
  languageItemActive: {
    backgroundColor: `${colors.primary.blue}08`,
  },
  languageFlag: {
    fontSize: 28,
    marginRight: theme.spacing.md,
  },
  languageInfo: {
    flex: 1,
  },
  languageName: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.primary,
  },
  languageNameActive: {
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.blue,
  },
  languageNote: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
    marginTop: 2,
  },
  aboutCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.xl,
    alignItems: 'center',
    ...theme.shadows.sm,
  },
  aboutLogoContainer: {
    marginBottom: theme.spacing.md,
  },
  aboutLogo: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
  },
  aboutLogoText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.primary.white,
  },
  aboutAppName: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  aboutVersion: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    marginBottom: theme.spacing.md,
  },
  aboutDescription: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary.white,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.sm,
    ...theme.shadows.sm,
  },
  actionText: {
    flex: 1,
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
    marginLeft: theme.spacing.md,
  },
  loginButton: {
    backgroundColor: `${colors.primary.rose}08`,
    borderWidth: 1,
    borderColor: colors.primary.rose,
  },
  loginText: {
    color: colors.primary.rose,
    fontWeight: theme.typography.weights.semibold,
  },
  signupButton: {
    backgroundColor: colors.primary.rose,
  },
  signupText: {
    color: colors.primary.white,
    fontWeight: theme.typography.weights.semibold,
  },
  footer: {
    alignItems: 'center',
    marginTop: theme.spacing.xl,
    paddingTop: theme.spacing.lg,
  },
  footerText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
  },
  footerSubtext: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    marginTop: theme.spacing.xs,
  },
});

// Ajouter la traduction manquante
import { translations, defaultLanguage } from '../i18n/translations';
if (!translations.fr.strings.selected) {
  translations.fr.strings.selected = 'sélectionnée';
  translations.en.strings.selected = 'selected';
  translations.es.strings.selected = 'seleccionada';
  translations.de.strings.selected = 'ausgewählt';
  translations.zh.strings.selected = '已选择';
  translations.ar.strings.selected = 'محدد';
}

export default SettingsScreen;