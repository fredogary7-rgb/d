/**
 * Écran Daily Motivation
 * Citation du jour, conseils de productivité et messages positifs
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Share,
  Alert,
  Linking,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { aiService, motivationStorage } from '../services';
import { SafeContainer } from '../components';

// Citations de motivation (seront mélangées avec l'IA)
const DAILY_QUOTES = [
  {
    text: "Le seul moyen de faire du bon travail est d'aimer ce que vous faites.",
    author: 'Steve Jobs',
    category: 'motivation',
  },
  {
    text: "La vie, c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre.",
    author: 'Albert Einstein',
    category: 'motivation',
  },
  {
    text: "Il n'est jamais trop tard pour devenir ce que vous auriez dû être.",
    author: 'George Eliot',
    category: 'inspiration',
  },
  {
    text: "Le succès, c'est d'aller d'échec en échec sans perdre son enthousiasme.",
    author: 'Winston Churchill',
    category: 'success',
  },
  {
    text: "Votre temps est limité, ne le gâchez pas en menant une existence qui n'est pas la vôtre.",
    author: 'Steve Jobs',
    category: 'inspiration',
  },
  {
    text: "La meilleure façon de prédire l'avenir est de le créer.",
    author: 'Peter Drucker',
    category: 'motivation',
  },
  {
    text: "Ce n'est pas parce que les choses sont difficiles que nous n'osons pas, c'est parce que nous n'osons pas qu'elles sont difficiles.",
    author: 'Sénèque',
    category: 'courage',
  },
  {
    text: "Le bonheur n'est pas quelque chose de prêt. Il vient de vos propres actions.",
    author: 'Dalai Lama',
    category: 'happiness',
  },
  {
    text: "La seule limite à notre épanouissement de demain sera nos doutes d'aujourd'hui.",
    author: 'Franklin D. Roosevelt',
    category: 'motivation',
  },
  {
    text: "Commencez là où vous êtes. Utilisez ce que vous avez. Faites ce que vous pouvez.",
    author: 'Arthur Ashe',
    category: 'action',
  },
];

// Conseils de productivité
const PRODUCTIVITY_TIPS = [
  "🍅 Technique Pomodoro : 25 min de travail concentré + 5 min de pause",
  "📝 La règle des 2 minutes : si ça prend moins de 2 min, faites-le maintenant",
  "🎯 Mangez la grenouille : commencez par la tâche la plus difficile",
  "📵 Éliminez les distractions : téléphone en mode avion pendant le travail",
  "🔄 La règle des 5 secondes : comptez 5-4-3-2-1 et passez à l'action",
  "📊 Time blocking : réservez des blocs de temps pour chaque type de tâche",
  "💪 La règle du 1% : améliorez-vous de 1% chaque jour",
  "🧘 La pause stratégique : 10 min de marche pour recharger l'énergie",
  "📚 La lecture matinale : 10 pages par jour = 15 livres par an",
  "🌙 Préparez votre journée la veille au soir",
];

const MotivationScreen = () => {
  const navigation = useNavigation();
  const [dailyQuote, setDailyQuote] = useState(null);
  const [dailyTip, setDailyTip] = useState(null);
  const [dailyAdvice, setDailyAdvice] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [showFullAdvice, setShowFullAdvice] = useState(false);
  const [pomodoroActive, setPomodoroActive] = useState(false);
  const [pomodoroTime, setPomodoroTime] = useState(25 * 60); // 25 minutes in seconds

  useEffect(() => {
    loadDailyContent();
  }, []);

  const loadDailyContent = async () => {
    // Vérifier si on a déjà chargé le contenu d'aujourd'hui
    const today = new Date().toDateString();
    const lastDate = await motivationStorage.getMotivationDate();

    if (lastDate === today) {
      // Charger le contenu sauvegardé (dans une vraie app, on le chargerait du storage)
      loadNewContent();
    } else {
      loadNewContent();
      await motivationStorage.setMotivationDate(today);
    }
  };

  const loadNewContent = async () => {
    // Sélectionner une citation aléatoire
    const randomQuote = DAILY_QUOTES[Math.floor(Math.random() * DAILY_QUOTES.length)];
    setDailyQuote(randomQuote);

    // Sélectionner un conseil aléatoire
    const randomTip = PRODUCTIVITY_TIPS[Math.floor(Math.random() * PRODUCTIVITY_TIPS.length)];
    setDailyTip(randomTip);

    // Obtenir le conseil IA du jour
    const advice = await aiService.getDailyAdvice();
    setDailyAdvice(advice);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadNewContent();
    setRefreshing(false);
  };

  const shareQuote = async () => {
    if (!dailyQuote) return;

    try {
      await Share.share({
        message: `"${dailyQuote.text}" — ${dailyQuote.author}\n\n🌟 Partagé depuis LifeNova`,
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  // Pomodoro Timer
  const startPomodoro = () => {
    if (pomodoroActive) {
      // Stop timer
      setPomodoroActive(false);
      Alert.alert('⏱️ Pomodoro arrêté', 'Votre session a été interrompue.');
    } else {
      // Start timer
      setPomodoroActive(true);
      Alert.alert(
        '🍅 Pomodoro démarré !',
        '25 minutes de concentration. Bonne productivité !',
        [{ text: 'OK' }]
      );
    }
  };

  // Navigate to Tasks
  const goToTasks = () => {
    navigation.navigate('Tâches');
  };

  // Navigate to Assistant
  const goToAssistant = () => {
    navigation.navigate('Assistant');
  };

  // Navigate to Progress
  const showProgress = () => {
    navigation.navigate('Progress');
  };

  const getCategoryIcon = (category) => {
    const icons = {
      motivation: 'flame',
      inspiration: 'lightbulb',
      success: 'trophy',
      courage: 'shield',
      happiness: 'heart',
      action: 'play',
    };
    return icons[category] || 'star';
  };

  const getCategoryColor = (category) => {
    const colors_map = {
      motivation: colors.primary.rose,
      inspiration: colors.primary.orange,
      success: colors.primary.blue,
      courage: '#8B5CF6',
      happiness: '#EC4899',
      action: '#10B981',
    };
    return colors_map[category] || colors.primary.rose;
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary.rose}
            colors={[colors.primary.rose]}
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerGreeting}>Bonjour ! ☀️</Text>
            <Text style={styles.headerTitle}>Votre dose quotidienne</Text>
          </View>
          <TouchableOpacity style={styles.refreshButton} onPress={onRefresh}>
            <Ionicons
              name={refreshing ? 'hourglass' : 'refresh'}
              size={20}
              color={colors.primary.rose}
            />
          </TouchableOpacity>
        </View>

        {/* Citation du Jour */}
        {dailyQuote && (
          <View style={styles.quoteCard}>
            <View style={styles.quoteHeader}>
              <Ionicons
                name={getCategoryIcon(dailyQuote.category)}
                size={20}
                color={getCategoryColor(dailyQuote.category)}
              />
              <Text
                style={[
                  styles.quoteCategory,
                  { color: getCategoryColor(dailyQuote.category) },
                ]}
              >
                {dailyQuote.category.toUpperCase()}
              </Text>
            </View>
            <Text style={styles.quoteText}>"{dailyQuote.text}"</Text>
            <Text style={styles.quoteAuthor}>— {dailyQuote.author}</Text>
            <TouchableOpacity style={styles.shareButton} onPress={shareQuote}>
              <Ionicons name="share-outline" size={18} color={colors.primary.rose} />
              <Text style={styles.shareButtonText}>Partager</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Conseil IA du Jour */}
        {dailyAdvice && (
          <View style={styles.adviceCard}>
            <View style={styles.adviceHeader}>
              <View style={styles.adviceIconContainer}>
                <Ionicons name="sparkles" size={20} color={colors.primary.white} />
              </View>
              <View>
                <Text style={styles.adviceTitle}>Conseil du Jour</Text>
                <Text style={styles.adviceType}>{dailyAdvice.type}</Text>
              </View>
            </View>
            <Text style={styles.adviceText}>{dailyAdvice.text}</Text>
            <View style={styles.adviceActionContainer}>
              <Ionicons name="arrow-forward-circle" size={18} color={colors.primary.blue} />
              <Text style={styles.adviceAction}>{dailyAdvice.action}</Text>
            </View>
          </View>
        )}

        {/* Section Conseils Rapides */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="bulb" size={20} color={colors.primary.orange} />
            <Text style={styles.sectionTitle}>Conseils Productivité</Text>
          </View>

          {dailyTip && (
            <View style={styles.tipCard}>
              <Text style={styles.tipText}>{dailyTip}</Text>
            </View>
          )}

          {/* Liste de tous les conseils */}
          <View style={styles.tipsGrid}>
            {PRODUCTIVITY_TIPS.slice(0, 6).map((tip, index) => (
              <View key={index} style={styles.tipItem}>
                <Ionicons name="checkmark-circle" size={16} color={colors.primary.blue} />
                <Text style={styles.tipItemText} numberOfLines={2}>
                  {tip.substring(3)}
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Section Actions Rapides */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Actions du Moment</Text>
          <View style={styles.quickActions}>
            <TouchableOpacity style={styles.quickAction} onPress={startPomodoro}>
              <View style={[styles.quickActionIcon, { backgroundColor: colors.primary.rose }]}>
                <Ionicons name={pomodoroActive ? 'stop' : 'timer'} size={20} color={colors.primary.white} />
              </View>
              <Text style={styles.quickActionText}>
                {pomodoroActive ? 'Arrêter Pomodoro' : 'Démarrer Pomodoro'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.quickAction} onPress={goToTasks}>
              <View style={[styles.quickActionIcon, { backgroundColor: colors.primary.orange }]}>
                <Ionicons name="list" size={20} color={colors.primary.white} />
              </View>
              <Text style={styles.quickActionText}>Voir mes tâches</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.quickAction} onPress={goToAssistant}>
              <View style={[styles.quickActionIcon, { backgroundColor: colors.primary.blue }]}>
                <Ionicons name="chatbubble" size={20} color={colors.primary.white} />
              </View>
              <Text style={styles.quickActionText}>Parler à l'IA</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.quickAction} onPress={showProgress}>
              <View style={[styles.quickActionIcon, { backgroundColor: '#10B981' }]}>
                <Ionicons name="stats-chart" size={20} color={colors.primary.white} />
              </View>
              <Text style={styles.quickActionText}>Mes progrès</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Footer Motivation */}
        <View style={styles.footer}>
          <Ionicons name="heart" size={24} color={colors.primary.rose} />
          <Text style={styles.footerText}>
            LifeNova est là pour vous accompagner chaque jour.
          </Text>
          <Text style={styles.footerSubtext}>
            Revenez demain pour une nouvelle dose de motivation !
          </Text>
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
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.lg,
  },
  headerGreeting: {
    fontSize: theme.typography.sizes.lg,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.xxl,
    color: colors.text.primary,
    fontWeight: theme.typography.weights.bold,
    marginTop: theme.spacing.xs,
  },
  refreshButton: {
    padding: theme.spacing.sm,
  },
  quoteCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    ...theme.shadows.md,
  },
  quoteHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  quoteCategory: {
    fontSize: theme.typography.sizes.xs,
    fontWeight: theme.typography.weights.bold,
    letterSpacing: 1,
  },
  quoteText: {
    fontSize: theme.typography.sizes.lg,
    color: colors.text.primary,
    fontWeight: theme.typography.weights.medium,
    lineHeight: 26,
    fontStyle: 'italic',
    marginBottom: theme.spacing.md,
  },
  quoteAuthor: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
    marginBottom: theme.spacing.md,
  },
  shareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
    alignSelf: 'flex-start',
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    backgroundColor: `${colors.primary.rose}10`,
    borderRadius: theme.borderRadius.md,
  },
  shareButtonText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.primary.rose,
    fontWeight: theme.typography.weights.medium,
  },
  adviceCard: {
    backgroundColor: colors.primary.blue,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  adviceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  adviceIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  adviceTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  adviceType: {
    fontSize: theme.typography.sizes.sm,
    color: 'rgba(255, 255, 255, 0.8)',
    textTransform: 'capitalize',
  },
  adviceText: {
    fontSize: theme.typography.sizes.md,
    color: colors.primary.white,
    lineHeight: 24,
    marginBottom: theme.spacing.md,
  },
  adviceActionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
  },
  adviceAction: {
    fontSize: theme.typography.sizes.md,
    color: colors.primary.white,
    fontWeight: theme.typography.weights.semibold,
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
  tipCard: {
    backgroundColor: `${colors.primary.orange}10`,
    borderLeftWidth: 4,
    borderLeftColor: colors.primary.orange,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  tipText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
    lineHeight: 22,
  },
  tipsGrid: {
    gap: theme.spacing.sm,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: theme.spacing.sm,
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    ...theme.shadows.sm,
  },
  tipItemText: {
    flex: 1,
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.md,
  },
  quickAction: {
    width: '47%',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    alignItems: 'center',
    ...theme.shadows.sm,
  },
  quickActionIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  quickActionText: {
    fontSize: theme.typography.sizes.sm,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.primary,
    textAlign: 'center',
  },
  footer: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    marginTop: theme.spacing.md,
  },
  footerText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: theme.spacing.sm,
  },
  footerSubtext: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    textAlign: 'center',
    marginTop: theme.spacing.xs,
  },
});

export default MotivationScreen;