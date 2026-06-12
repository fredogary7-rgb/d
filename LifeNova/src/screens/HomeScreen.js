/**
 * Écran Home LifeNova
 * Page d'accueil principale avec design moderne et minimaliste
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { SafeContainer } from '../components';
import { useTranslation } from '../i18n/useTranslation';

const HomeScreen = () => {
  const navigation = useNavigation();
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('home');
  const spinValue = useState(new Animated.Value(0))[0];

  React.useEffect(() => {
    Animated.loop(
      Animated.timing(spinValue, {
        toValue: 1,
        duration: 10000,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  // Données de démonstration (seront remplacées par les données de l'API)
  const features = [
    {
      id: 1,
      title: t('personalTracking'),
      description: t('manageDaily'),
      iconName: 'person-circle-outline',
      color: colors.primary.rose,
    },
    {
      id: 2,
      title: t('goals'),
      description: t('achieveAmbitions'),
      iconName: 'flag',
      color: colors.primary.orange,
    },
    {
      id: 3,
      title: t('progression'),
      description: t('visualizeProgress'),
      iconName: 'trending-up',
      color: colors.primary.blue,
    },
  ];

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      {/* Arrière-plan décoratif */}
      <View style={styles.backgroundDecorations}>
        <Animated.View
          style={[
            styles.decorCircle,
            styles.circle1,
            { transform: [{ rotate: spin }] },
          ]}
        />
        <Animated.View
          style={[
            styles.decorCircle,
            styles.circle2,
            { transform: [{ rotate: spin }] },
          ]}
        />
        <Animated.View
          style={[
            styles.decorCircle,
            styles.circle3,
            { transform: [{ rotate: spin }] },
          ]}
        />
      </View>

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.greeting}>{t('greeting')} 👋</Text>
            <Text style={styles.welcomeText}>{t('welcome')} LifeNova</Text>
          </View>
          <TouchableOpacity 
            style={styles.profileButton}
            onPress={() => navigation.navigate('Settings')}
          >
            <View style={styles.profileAvatar}>
              <Ionicons name="settings" size={22} color={colors.primary.white} />
            </View>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Section Hero */}
        <View style={styles.heroSection}>
          <View style={styles.heroCard}>
            <View style={styles.heroIconContainer}>
              <Ionicons name="sparkles" size={32} color={colors.primary.rose} />
            </View>
            <Text style={styles.heroTitle}>{t('getStarted')}</Text>
            <Text style={styles.heroSubtitle}>
              LifeNova {t('achieveAmbitions').toLowerCase()}.
            </Text>
            <TouchableOpacity
              style={styles.heroButton}
              onPress={() => navigation.navigate('Tâches')}
            >
            <Text style={styles.heroButtonText}>{t('getStarted')}</Text>
              <Ionicons name="arrow-forward" size={18} color={colors.primary.white} style={styles.heroButtonIcon} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Section Fonctionnalités */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="apps" size={20} color={colors.primary.orange} />
            <Text style={styles.sectionTitle}>{t('features')}</Text>
          </View>
          <View style={styles.featuresGrid}>
            {features.map((feature) => (
              <TouchableOpacity
                key={feature.id}
                style={[styles.featureCard, { borderLeftColor: feature.color }]}
                activeOpacity={0.7}
              >
              <View style={[styles.featureIconContainer, { backgroundColor: `${feature.color}15` }]}>
                <Ionicons name={feature.iconName} size={22} color={feature.color} />
              </View>
                <Text style={styles.featureTitle}>{feature.title}</Text>
                <Text style={styles.featureDescription}>{feature.description}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Section Statistiques */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="stats-chart" size={20} color={colors.primary.blue} />
            <Text style={styles.sectionTitle}>{t('overview')}</Text>
          </View>
          <View style={styles.statsCard}>
            <View style={styles.statItem}>
              <View style={styles.statIconWrapper}>
                <Ionicons name="flag" size={16} color={colors.primary.blue} />
              </View>
              <Text style={styles.statValue}>0</Text>
              <Text style={styles.statLabel}>{t('objectives')}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <View style={styles.statIconWrapper}>
                <Ionicons name="trending-up" size={16} color={colors.primary.orange} />
              </View>
              <Text style={styles.statValue}>0%</Text>
              <Text style={styles.statLabel}>{t('progression')}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <View style={styles.statIconWrapper}>
                <Ionicons name="calendar" size={16} color={colors.primary.rose} />
              </View>
              <Text style={styles.statValue}>0</Text>
              <Text style={styles.statLabel}>{t('days')}</Text>
            </View>
          </View>
        </View>

        {/* Section CTA */}
        <View style={styles.ctaSection}>
          <View style={styles.ctaCard}>
            <View style={styles.ctaIconContainer}>
              <Ionicons name="rocket" size={28} color={colors.primary.white} />
            </View>
            <Text style={styles.ctaTitle}>{t('readyToStart')}</Text>
            <Text style={styles.ctaSubtitle}>
              {t('createFirstGoal')}
            </Text>
            <TouchableOpacity
              style={styles.ctaButton}
              onPress={() => navigation.navigate('Tâches')}
            >
              <Text style={styles.ctaButtonText}>{t('createGoal')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>LifeNova - {t('slogan').replace('.', '')} ✨</Text>
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
  backgroundDecorations: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
    pointerEvents: 'none',
  },
  decorCircle: {
    position: 'absolute',
    borderRadius: 9999,
  },
  circle1: {
    width: 300,
    height: 300,
    backgroundColor: `${colors.primary.rose}08`,
    top: -80,
    right: -80,
  },
  circle2: {
    width: 250,
    height: 250,
    backgroundColor: `${colors.primary.orange}08`,
    bottom: '30%',
    left: -60,
  },
  circle3: {
    width: 200,
    height: 200,
    backgroundColor: `${colors.primary.blue}06`,
    top: '50%',
    right: -40,
  },
  header: {
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.md,
    paddingBottom: theme.spacing.md,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: theme.typography.sizes.lg,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  welcomeText: {
    fontSize: theme.typography.sizes.xxl,
    color: colors.text.primary,
    fontWeight: theme.typography.weights.bold,
    marginTop: theme.spacing.xs,
  },
  profileButton: {
    padding: theme.spacing.xs,
  },
  profileAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.xxl,
  },
  heroSection: {
    marginTop: theme.spacing.md,
  },
  heroCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    ...theme.shadows.md,
    overflow: 'hidden',
  },
  heroIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: `${colors.primary.rose}10`,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  heroTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  heroSubtitle: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 22,
    marginBottom: theme.spacing.lg,
  },
  heroButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary.rose,
    borderRadius: theme.borderRadius.md,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    alignSelf: 'flex-start',
  },
  heroButtonIcon: {
    marginLeft: theme.spacing.sm,
  },
  heroButtonText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  section: {
    marginTop: theme.spacing.xl,
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
  featuresGrid: {
    gap: theme.spacing.md,
  },
  featureCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    borderLeftWidth: 4,
    ...theme.shadows.sm,
  },
  featureIconContainer: {
    width: 44,
    height: 44,
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  featureTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  featureDescription: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  statsCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    ...theme.shadows.sm,
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statIconWrapper: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: `${colors.primary.blue}10`,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  statValue: {
    fontSize: theme.typography.sizes.xxl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  statLabel: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.background.tertiary,
    marginHorizontal: theme.spacing.md,
  },
  ctaSection: {
    marginTop: theme.spacing.xl,
  },
  ctaCard: {
    backgroundColor: colors.primary.blue,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    alignItems: 'center',
  },
  ctaIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  ctaTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.primary.white,
    marginBottom: theme.spacing.sm,
  },
  ctaSubtitle: {
    fontSize: theme.typography.sizes.md,
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: 22,
    marginBottom: theme.spacing.lg,
    textAlign: 'center',
  },
  ctaButton: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.md,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.xl,
    alignItems: 'center',
  },
  ctaButtonText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.blue,
  },
  footer: {
    marginTop: theme.spacing.xl,
    paddingVertical: theme.spacing.lg,
    alignItems: 'center',
  },
  footerText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    fontWeight: theme.typography.weights.medium,
  },
});

export default HomeScreen;