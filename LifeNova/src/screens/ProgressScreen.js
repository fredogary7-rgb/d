/**
 * Écran Mes Progrès
 * Statistiques, graphiques et suivi de l'évolution personnelle
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  FlatList,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { taskStorage, cycleStorage } from '../services';
import { SafeContainer } from '../components';

const ProgressScreen = () => {
  const [stats, setStats] = useState({
    totalTasks: 0,
    completedTasks: 0,
    completionRate: 0,
    currentStreak: 0,
    bestStreak: 0,
    tasksByCategory: {},
    weeklyProgress: [],
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    const tasks = await taskStorage.getTasks();
    const completedTasks = tasks.filter((t) => t.completed);
    const completionRate = tasks.length > 0 ? Math.round((completedTasks.length / tasks.length) * 100) : 0;

    // Calculer les tâches par catégorie
    const tasksByCategory = {};
    tasks.forEach((task) => {
      if (!tasksByCategory[task.category]) {
        tasksByCategory[task.category] = { total: 0, completed: 0 };
      }
      tasksByCategory[task.category].total++;
      if (task.completed) {
        tasksByCategory[task.category].completed++;
      }
    });

    // Simulation de la progression hebdomadaire
    const weeklyProgress = [
      { day: 'Lun', completed: 3, total: 5 },
      { day: 'Mar', completed: 5, total: 7 },
      { day: 'Mer', completed: 2, total: 4 },
      { day: 'Jeu', completed: 6, total: 8 },
      { day: 'Ven', completed: 4, total: 6 },
      { day: 'Sam', completed: 1, total: 2 },
      { day: 'Dim', completed: 2, total: 3 },
    ];

    // Calculer les streaks (jours consécutifs avec tâches complétées)
    const currentStreak = calculateStreak(tasks);
    const bestStreak = 7; // Simulation

    setStats({
      totalTasks: tasks.length,
      completedTasks: completedTasks.length,
      completionRate,
      currentStreak,
      bestStreak,
      tasksByCategory,
      weeklyProgress,
    });
  };

  const calculateStreak = (tasks) => {
    // Simplifié: retourne le nombre de tâches complétées aujourd'hui
    const today = new Date().toDateString();
    return tasks.filter((t) => t.completed).length;
  };

  const getCategoryName = (categoryId) => {
    const categories = {
      work: 'Travail',
      personal: 'Personnel',
      health: 'Santé',
      learning: 'Apprentissage',
      finance: 'Finance',
    };
    return categories[categoryId] || categoryId;
  };

  const getCategoryColor = (categoryId) => {
    const colors_map = {
      work: '#3B82F6',
      personal: '#10B981',
      health: '#EF4444',
      learning: '#8B5CF6',
      finance: '#F59E0B',
    };
    return colors_map[categoryId] || colors.text.secondary;
  };

  const achievements = [
    {
      id: 1,
      title: 'Premier pas',
      description: 'Créer votre première tâche',
      icon: 'flag',
      unlocked: stats.totalTasks > 0,
      color: colors.primary.rose,
    },
    {
      id: 2,
      title: 'Productif',
      description: 'Compléter 10 tâches',
      icon: 'checkmark-circle',
      unlocked: stats.completedTasks >= 10,
      color: colors.primary.orange,
    },
    {
      id: 3,
      title: 'Déterminé',
      description: 'Avoir 5 tâches cette semaine',
      icon: 'flame',
      unlocked: stats.currentStreak >= 5,
      color: colors.primary.blue,
    },
    {
      id: 4,
      title: 'Expert',
      description: 'Taux de complétion > 80%',
      icon: 'trophy',
      unlocked: stats.completionRate >= 80,
      color: '#10B981',
    },
  ];

  const renderStatCard = (title, value, icon, color, subtitle) => (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={[styles.statIconContainer, { backgroundColor: `${color}15` }]}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      <View style={styles.statContent}>
        <Text style={styles.statValue}>{value}</Text>
        <Text style={styles.statTitle}>{title}</Text>
        {subtitle && <Text style={styles.statSubtitle}>{subtitle}</Text>}
      </View>
    </View>
  );

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Mes Progrès</Text>
            <Text style={styles.headerSubtitle}>
              Suivez votre évolution et célébrez vos réussites
            </Text>
          </View>
          <TouchableOpacity style={styles.refreshButton} onPress={loadStats}>
            <Ionicons name="refresh" size={20} color={colors.primary.rose} />
          </TouchableOpacity>
        </View>

        {/* Stats principales */}
        <View style={styles.statsGrid}>
          {renderStatCard(
            'Tâches totales',
            stats.totalTasks,
            'clipboard',
            colors.primary.blue
          )}
          {renderStatCard(
            'Tâches complétées',
            stats.completedTasks,
            'checkmark-done-circle',
            colors.primary.rose
          )}
          {renderStatCard(
            'Taux de réussite',
            `${stats.completionRate}%`,
            'trending-up',
            colors.primary.orange
          )}
          {renderStatCard(
            'Série actuelle',
            `${stats.currentStreak} jours`,
            'flame',
            '#EF4444',
            `Meilleure: ${stats.bestStreak} jours`
          )}
        </View>

        {/* Progression hebdomadaire */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="bar-chart" size={20} color={colors.primary.blue} />
            <Text style={styles.sectionTitle}>Progression de la semaine</Text>
          </View>
          <View style={styles.chartContainer}>
            {stats.weeklyProgress.map((day, index) => (
              <View key={index} style={styles.chartBarContainer}>
                <View style={styles.chartBarWrapper}>
                  <View
                    style={[
                      styles.chartBar,
                      { height: `${(day.completed / day.total) * 100}%` },
                    ]}
                  />
                </View>
                <Text style={styles.chartLabel}>{day.day}</Text>
                <Text style={styles.chartValue}>{day.completed}/{day.total}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Répartition par catégorie */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="pie-chart" size={20} color={colors.primary.orange} />
            <Text style={styles.sectionTitle}>Répartition par catégorie</Text>
          </View>
          {Object.keys(stats.tasksByCategory).length > 0 ? (
            <View style={styles.categoriesList}>
              {Object.entries(stats.tasksByCategory).map(([categoryId, data]) => (
                <View key={categoryId} style={styles.categoryItem}>
                  <View style={styles.categoryInfo}>
                    <View
                      style={[
                        styles.categoryDot,
                        { backgroundColor: getCategoryColor(categoryId) },
                      ]}
                    />
                    <Text style={styles.categoryName}>
                      {getCategoryName(categoryId)}
                    </Text>
                  </View>
                  <View style={styles.categoryStats}>
                    <Text style={styles.categoryValue}>
                      {data.completed}/{data.total}
                    </Text>
                    <View style={styles.categoryProgressBar}>
                      <View
                        style={[
                          styles.categoryProgressFill,
                          {
                            width: `${(data.completed / data.total) * 100}%`,
                            backgroundColor: getCategoryColor(categoryId),
                          },
                        ]}
                      />
                    </View>
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.emptyCategory}>
              <Ionicons name="folder-open-outline" size={32} color={colors.text.light} />
              <Text style={styles.emptyCategoryText}>Aucune tâche pour le moment</Text>
            </View>
          )}
        </View>

        {/* Succès et badges */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="award" size={20} color={colors.primary.rose} />
            <Text style={styles.sectionTitle}>Succès et Badges</Text>
          </View>
          <View style={styles.achievementsGrid}>
            {achievements.map((achievement) => (
              <View
                key={achievement.id}
                style={[
                  styles.achievementCard,
                  !achievement.unlocked && styles.achievementCardLocked,
                ]}
              >
                <View
                  style={[
                    styles.achievementIcon,
                    {
                      backgroundColor: achievement.unlocked
                        ? `${achievement.color}20`
                        : colors.background.tertiary,
                    },
                  ]}
                >
                  <Ionicons
                    name={achievement.icon}
                    size={24}
                    color={achievement.unlocked ? achievement.color : colors.text.light}
                  />
                </View>
                <Text
                  style={[
                    styles.achievementTitle,
                    !achievement.unlocked && styles.achievementTitleLocked,
                  ]}
                >
                  {achievement.title}
                </Text>
                <Text
                  style={[
                    styles.achievementDescription,
                    !achievement.unlocked && styles.achievementDescriptionLocked,
                  ]}
                >
                  {achievement.description}
                </Text>
                {achievement.unlocked && (
                  <View style={styles.achievementBadge}>
                    <Ionicons name="checkmark-circle" size={14} color={achievement.color} />
                    <Text style={[styles.achievementBadgeText, { color: achievement.color }]}>
                      Débloqué
                    </Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        </View>

        {/* Conseils d'amélioration */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="lightbulb" size={20} color={colors.primary.orange} />
            <Text style={styles.sectionTitle}>Conseils d'amélioration</Text>
          </View>
          <View style={styles.tipsCard}>
            {stats.completionRate < 50 && (
              <View style={styles.tipItem}>
                <Ionicons name="arrow-redo" size={16} color={colors.primary.orange} />
                <Text style={styles.tipText}>
                  Essayez de décomposer vos grandes tâches en petites étapes plus gérables.
                </Text>
              </View>
            )}
            {stats.currentStreak < 3 && (
              <View style={styles.tipItem}>
                <Ionicons name="arrow-redo" size={16} color={colors.primary.orange} />
                <Text style={styles.tipText}>
                  Complétez au moins une tâche par jour pour maintenir votre motivation.
                </Text>
              </View>
            )}
            {stats.totalTasks === 0 && (
              <View style={styles.tipItem}>
                <Ionicons name="arrow-redo" size={16} color={colors.primary.orange} />
                <Text style={styles.tipText}>
                  Commencez par créer votre première tâche pour démarrer votre suivi !
                </Text>
              </View>
            )}
            {stats.completionRate >= 80 && (
              <View style={styles.tipItem}>
                <Ionicons name="arrow-redo" size={16} color="#10B981" />
                <Text style={styles.tipText}>
                  Excellent travail ! Continuez sur cette lancée et visez les 100%.
                </Text>
              </View>
            )}
          </View>
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.xxl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  headerSubtitle: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    marginTop: theme.spacing.xs,
  },
  refreshButton: {
    padding: theme.spacing.sm,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: theme.spacing.lg,
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  statCard: {
    flex: '48%',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    borderLeftWidth: 4,
    ...theme.shadows.sm,
  },
  statIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  statContent: {
    marginTop: theme.spacing.xs,
  },
  statValue: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  statTitle: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
    marginTop: 2,
  },
  statSubtitle: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
    marginTop: 2,
  },
  section: {
    marginTop: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
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
  chartContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    height: 150,
    ...theme.shadows.sm,
  },
  chartBarContainer: {
    flex: 1,
    alignItems: 'center',
  },
  chartBarWrapper: {
    width: 24,
    height: 100,
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.sm,
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  chartBar: {
    backgroundColor: colors.primary.blue,
    borderRadius: theme.borderRadius.sm,
    minHeight: 4,
  },
  chartLabel: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.secondary,
    marginTop: theme.spacing.sm,
    fontWeight: theme.typography.weights.medium,
  },
  chartValue: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
    marginTop: 2,
  },
  categoriesList: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.shadows.sm,
  },
  categoryItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
  },
  categoryInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  categoryDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  categoryName: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.primary,
  },
  categoryStats: {
    alignItems: 'flex-end',
  },
  categoryValue: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
    marginBottom: 4,
  },
  categoryProgressBar: {
    width: 80,
    height: 6,
    backgroundColor: colors.background.tertiary,
    borderRadius: 3,
    overflow: 'hidden',
  },
  categoryProgressFill: {
    height: '100%',
    borderRadius: 3,
  },
  emptyCategory: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    ...theme.shadows.sm,
  },
  emptyCategoryText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.light,
    marginTop: theme.spacing.sm,
  },
  achievementsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  achievementCard: {
    flex: '48%',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.shadows.sm,
  },
  achievementCardLocked: {
    opacity: 0.5,
  },
  achievementIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  achievementTitle: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  achievementTitleLocked: {
    color: colors.text.light,
  },
  achievementDescription: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    lineHeight: 18,
  },
  achievementDescriptionLocked: {
    color: colors.text.light,
  },
  achievementBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: theme.spacing.sm,
  },
  achievementBadgeText: {
    fontSize: theme.typography.sizes.xs,
    fontWeight: theme.typography.weights.medium,
  },
  tipsCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.shadows.sm,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
  },
  tipText: {
    flex: 1,
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    lineHeight: 20,
  },
});

export default ProgressScreen;