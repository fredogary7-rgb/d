/**
 * LifeNova Smart Dashboard
 * Écran principal intelligent - Vue d'ensemble de la vie de l'utilisateur
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Animated,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { colors, theme } from '../constants';
import { SafeContainer } from '../components';
import { aiCoachService } from '../services/aiCoachService';
import { cycleService } from '../services/cycleService';
import { cycleInsightsService } from '../services/cycleInsightsService';
import { useTranslation } from '../i18n/useTranslation';

const SmartDashboardScreen = () => {
  const navigation = useNavigation();
  const { t } = useTranslation();
  const [refreshing, setRefreshing] = useState(false);
  const [fadeAnim] = useState(new Animated.Value(0));

  // Mock data - would come from context/store in production
  const userProfile = useMemo(() => ({
    firstName: 'Marie',
    primaryGoal: 'productivity',
    lastPeriodDate: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    cycleLength: 28,
  }), []);

  const checkins = useMemo(() => [
    { date: new Date(), mood: 4, energy: 3, stress: 2, sleep: 4 },
    { date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), mood: 3, energy: 3, stress: 3, sleep: 3 },
    { date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), mood: 4, energy: 4, stress: 2, sleep: 4 },
  ], []);

  const cycles = useMemo(() => [
    { startDate: new Date(Date.now() - 28 * 24 * 60 * 60 * 1000).toISOString(), cycleLength: 28 },
    { startDate: new Date(Date.now() - 56 * 24 * 60 * 60 * 1000).toISOString(), cycleLength: 29 },
    { startDate: new Date(Date.now() - 84 * 24 * 60 * 60 * 1000).toISOString(), cycleLength: 28 },
  ], []);

  const tasks = useMemo(() => [
    { id: 1, title: 'Tâche 1', completed: true },
    { id: 2, title: 'Tâche 2', completed: true },
    { id: 3, title: 'Tâche 3', completed: false },
    { id: 4, title: 'Tâche 4', completed: true },
  ], []);

  // Calculations
  const lifeScore = useMemo(() => 
    aiCoachService.calculateLifeScore(userProfile, checkins, cycles, tasks),
    [userProfile, checkins, cycles, tasks]
  );

  const regularity = useMemo(() => 
    cycleInsightsService.calculateRegularityScore(cycles),
    [cycles]
  );

  const currentPhase = useMemo(() => 
    userProfile.lastPeriodDate 
      ? cycleService.getCyclePhase(userProfile.lastPeriodDate, userProfile.cycleLength)
      : null,
    [userProfile]
  );

  const dailyPlan = useMemo(() => 
    aiCoachService.generateDailyPlan(userProfile, currentPhase),
    [userProfile, currentPhase]
  );

  const insights = useMemo(() => {
    const result = [];
    
    // Insight based on recent checkins
    if (checkins.length >= 2) {
      const recentEnergy = checkins[0]?.energy || 3;
      const prevEnergy = checkins[1]?.energy || 3;
      if (recentEnergy > prevEnergy) {
        result.push("Votre énergie est plus élevée que la semaine dernière. 🌟");
      } else if (recentEnergy < prevEnergy) {
        result.push("Votre énergie a diminué. Pensez à vous reposer. 💤");
      }
    }

    // Insight based on cycle phase
    if (currentPhase?.name === 'Ovulation') {
      result.push("Vous êtes en phase d'ovulation. Période de haute énergie ! 🌸");
    }

    // Insight based on regularity
    if (regularity.score >= 75) {
      result.push("Vos cycles sont réguliers. Excellent pour la planification ! 📊");
    }

    // Insight based on tasks
    const completedTasks = tasks.filter(t => t.completed).length;
    if (completedTasks >= tasks.length * 0.7) {
      result.push("Vous êtes régulier dans vos objectifs. Continuez ! 💪");
    }

    if (result.length === 0) {
      result.push("Commencez votre check-in quotidien pour des insights personnalisés. ✨");
    }

    return result.slice(0, 3);
  }, [checkins, currentPhase, regularity, tasks]);

  // Goal progress
  const goalProgress = useMemo(() => {
    const completedTasks = tasks.filter(t => t.completed).length;
    return Math.round((completedTasks / Math.max(tasks.length, 1)) * 100);
  }, [tasks]);

  // Fade in animation
  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    // In production, would refresh data here
    await new Promise(resolve => setTimeout(resolve, 1000));
    setRefreshing(false);
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bon matin';
    if (hour < 18) return 'Bon après-midi';
    return 'Bon soir';
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
        <Animated.View style={[styles.header, { opacity: fadeAnim }]}>
          <View>
            <Text style={styles.greeting}>{getGreeting()}, {userProfile.firstName} 👋</Text>
            <Text style={styles.date}>
              {new Date().toLocaleDateString('fr-FR', { 
                weekday: 'long', 
                day: 'numeric', 
                month: 'long' 
              })}
            </Text>
          </View>
          <TouchableOpacity 
            style={styles.settingsButton}
            onPress={() => navigation.navigate('Settings')}
          >
            <Ionicons name="settings-outline" size={24} color={colors.text.secondary} />
          </TouchableOpacity>
        </Animated.View>

        {/* LifeScore Card */}
        <Animated.View style={[styles.scoreCard, { opacity: fadeAnim }]}>
          <View style={styles.scoreHeader}>
            <Text style={styles.scoreLabel}>Votre Score LifeNova</Text>
            <View style={[styles.scoreBadge, { backgroundColor: getScoreColor(lifeScore.score) + '15' }]}>
              <Text style={[styles.scoreBadgeText, { color: getScoreColor(lifeScore.score) }]}>
                {lifeScore.score}/100
              </Text>
            </View>
          </View>
          
          <View style={styles.scoreRing}>
            <View style={[styles.scoreRingFill, { 
              height: `${lifeScore.score}%`,
              backgroundColor: getScoreColor(lifeScore.score)
            }]} />
          </View>
          
          <Text style={styles.scoreMessage}>{lifeScore.message}</Text>
          
          <View style={styles.scoreBreakdown}>
            <ScoreItem 
              label="Productivité" 
              value={lifeScore.breakdown.activity} 
              color={colors.primary.rose}
            />
            <ScoreItem 
              label="Bien-être" 
              value={lifeScore.breakdown.consistency} 
              color={colors.primary.orange}
            />
            <ScoreItem 
              label="Habitudes" 
              value={lifeScore.breakdown.progression} 
              color={colors.primary.blue}
            />
            <ScoreItem 
              label="Énergie" 
              value={lifeScore.breakdown.regularity} 
              color="#10B981"
            />
          </View>
        </Animated.View>

        {/* Daily Mission */}
        <View style={styles.missionCard}>
          <View style={styles.missionHeader}>
            <Ionicons name="target" size={20} color={colors.primary.rose} />
            <Text style={styles.missionTitle}>Mission du Jour</Text>
          </View>
          <Text style={styles.missionText}>"{dailyPlan.mission}"</Text>
          <Text style={styles.missionPriority}>
            🎯 Priorité : {dailyPlan.priority}
          </Text>
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <ActionButton 
            icon="brain" 
            label="Coach IA" 
            color={colors.primary.blue}
            onPress={() => navigation.navigate('Assistant')}
          />
          <ActionButton 
            icon="checkbox" 
            label="Tâches" 
            color={colors.primary.rose}
            onPress={() => navigation.navigate('Tâches')}
          />
          <ActionButton 
            icon="flower" 
            label="Cycle" 
            color={colors.primary.orange}
            onPress={() => navigation.navigate('Cycle')}
          />
          <ActionButton 
            icon="stats-chart" 
            label="Progression" 
            color="#10B981"
            onPress={() => navigation.navigate('Progress')}
          />
        </View>

        {/* Goal Progress */}
        <View style={styles.goalCard}>
          <View style={styles.goalHeader}>
            <Ionicons name="flag" size={20} color={colors.primary.orange} />
            <Text style={styles.goalTitle}>
              {aiCoachService.GOALS[userProfile.primaryGoal]?.label || 'Objectif'}
            </Text>
            <Text style={styles.goalProgress}>{goalProgress}%</Text>
          </View>
          <View style={styles.goalBar}>
            <View style={[styles.goalFill, { width: `${goalProgress}%` }]} />
          </View>
        </View>

        {/* Smart Insights */}
        <View style={styles.insightsCard}>
          <View style={styles.insightsHeader}>
            <Ionicons name="bulb" size={20} color={colors.primary.orange} />
            <Text style={styles.insightsTitle}>Insights Intelligents</Text>
          </View>
          {insights.map((insight, index) => (
            <View key={index} style={styles.insightItem}>
              <Ionicons name="sparkles" size={16} color={colors.primary.orange} />
              <Text style={styles.insightText}>{insight}</Text>
            </View>
          ))}
        </View>

        {/* Daily Quote */}
        <View style={styles.quoteCard}>
          <Ionicons name="quote" size={24} color={colors.primary.rose} style={styles.quoteIcon} />
          <Text style={styles.quoteText}>{dailyPlan.quote}</Text>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>LifeNova - Votre vie, réinventée ✨</Text>
        </View>
      </ScrollView>
    </SafeContainer>
  );
};

// Sub-components
const ScoreItem = ({ label, value, color }) => (
  <View style={styles.scoreItem}>
    <View style={[styles.scoreItemBar, { backgroundColor: color + '20' }]}>
      <View style={[styles.scoreItemFill, { width: `${value * 4}%`, backgroundColor: color }]} />
    </View>
    <Text style={styles.scoreItemLabel}>{label}</Text>
  </View>
);

const ActionButton = ({ icon, label, color, onPress }) => (
  <TouchableOpacity style={styles.actionButton} onPress={onPress} activeOpacity={0.7}>
    <View style={[styles.actionIcon, { backgroundColor: color + '15' }]}>
      <Ionicons name={icon} size={22} color={color} />
    </View>
    <Text style={styles.actionLabel}>{label}</Text>
  </TouchableOpacity>
);

// Helper functions
const getScoreColor = (score) => {
  if (score >= 80) return '#10B981';
  if (score >= 60) return '#FF8A3D';
  if (score >= 40) return '#FF4FA3';
  return '#EF4444';
};

const styles = StyleSheet.create({
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
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  greeting: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  date: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    marginTop: theme.spacing.xs,
    textTransform: 'capitalize',
  },
  settingsButton: {
    padding: theme.spacing.sm,
  },
  scoreCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    ...theme.shadows.md,
  },
  scoreHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  scoreLabel: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
  },
  scoreBadge: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.md,
  },
  scoreBadgeText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.bold,
  },
  scoreRing: {
    height: 80,
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
    marginBottom: theme.spacing.md,
  },
  scoreRingFill: {
    width: '100%',
    borderTopLeftRadius: theme.borderRadius.lg,
    borderTopRightRadius: theme.borderRadius.lg,
  },
  scoreMessage: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: theme.spacing.lg,
    fontStyle: 'italic',
  },
  scoreBreakdown: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  scoreItem: {
    flex: 1,
    alignItems: 'center',
  },
  scoreItemBar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  scoreItemFill: {
    width: '100%',
    height: '100%',
    borderRadius: 20,
  },
  scoreItemLabel: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
    textAlign: 'center',
  },
  missionCard: {
    backgroundColor: colors.primary.blue,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  missionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  missionTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  missionText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.medium,
    color: colors.primary.white,
    fontStyle: 'italic',
    marginBottom: theme.spacing.sm,
  },
  missionPriority: {
    fontSize: theme.typography.sizes.md,
    color: 'rgba(255, 255, 255, 0.9)',
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.lg,
  },
  actionButton: {
    alignItems: 'center',
    flex: 1,
  },
  actionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  actionLabel: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  goalCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    ...theme.shadows.sm,
  },
  goalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  goalTitle: {
    flex: 1,
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
  },
  goalProgress: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.bold,
    color: colors.primary.orange,
  },
  goalBar: {
    height: 8,
    backgroundColor: colors.background.secondary,
    borderRadius: 4,
    overflow: 'hidden',
  },
  goalFill: {
    height: '100%',
    backgroundColor: colors.primary.orange,
    borderRadius: 4,
  },
  insightsCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    ...theme.shadows.sm,
  },
  insightsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  insightsTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
  },
  insightText: {
    flex: 1,
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 22,
  },
  quoteCard: {
    backgroundColor: `${colors.primary.rose}08`,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
  },
  quoteIcon: {
    marginBottom: theme.spacing.sm,
  },
  quoteText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    fontStyle: 'italic',
    lineHeight: 24,
  },
  footer: {
    alignItems: 'center',
    marginTop: theme.spacing.lg,
  },
  footerText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
  },
});

export default SmartDashboardScreen;