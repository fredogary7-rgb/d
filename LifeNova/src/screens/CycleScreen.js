/**
 * Écran Cycle Féminin
 * Suivi des règles, ovulation, et informations éducatives
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  TextInput,
  FlatList,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { cycleService, cycleEducation } from '../services';
import { cycleStorage } from '../services/storageService';
import { SafeContainer } from '../components';

const CycleScreen = () => {
  const [lastPeriodDate, setLastPeriodDate] = useState(null);
  const [cycleLength, setCycleLength] = useState(cycleService.AVERAGE_CYCLE_LENGTH);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [nextPeriod, setNextPeriod] = useState(null);
  const [ovulationDate, setOvulationDate] = useState(null);
  const [fertileWindow, setFertileWindow] = useState(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showCycleInfo, setShowCycleInfo] = useState(false);
  const [selectedPhase, setSelectedPhase] = useState(null);
  const [cycles, setCycles] = useState([]);

  useEffect(() => {
    loadCycleData();
  }, []);

  const loadCycleData = async () => {
    const savedData = await cycleStorage.getCycleData();
    if (savedData && savedData.lastPeriodDate) {
      setLastPeriodDate(new Date(savedData.lastPeriodDate));
      setCycleLength(savedData.cycleLength || cycleService.AVERAGE_CYCLE_LENGTH);
      
      // Calculer les informations
      const phase = cycleService.getCyclePhase(savedData.lastPeriodDate, savedData.cycleLength);
      setCurrentPhase(phase);
      
      const nextP = cycleService.calculateNextPeriod(savedData.lastPeriodDate, savedData.cycleLength);
      setNextPeriod(nextP);
      
      const ovulation = cycleService.calculateOvulation(savedData.lastPeriodDate, savedData.cycleLength);
      setOvulationDate(ovulation);
      
      const fertile = cycleService.calculateFertileWindow(savedData.lastPeriodDate, savedData.cycleLength);
      setFertileWindow(fertile);
      
      // Charger l'historique
      const savedCycles = await cycleStorage.getCycles();
      setCycles(savedCycles);
    }
  };

  const saveLastPeriod = async (date) => {
    await cycleStorage.saveCycleData({
      lastPeriodDate: date.toISOString(),
      cycleLength: cycleLength,
    });
    
    // Ajouter à l'historique
    await cycleStorage.addCycle({
      startDate: date.toISOString(),
      cycleLength: cycleLength,
    });
    
    setLastPeriodDate(date);
    
    // Recalculer tout
    const phase = cycleService.getCyclePhase(date, cycleLength);
    setCurrentPhase(phase);
    
    const nextP = cycleService.calculateNextPeriod(date, cycleLength);
    setNextPeriod(nextP);
    
    const ovulation = cycleService.calculateOvulation(date, cycleLength);
    setOvulationDate(ovulation);
    
    const fertile = cycleService.calculateFertileWindow(date, cycleLength);
    setFertileWindow(fertile);
    
    // Recharger l'historique
    const savedCycles = await cycleStorage.getCycles();
    setCycles(savedCycles);
  };

  const formatDate = (date) => {
    if (!date) return 'Non défini';
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
    });
  };

  const getDaysUntil = (targetDate) => {
    if (!targetDate) return '?';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(targetDate);
    target.setHours(0, 0, 0, 0);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getDayOfCycle = () => {
    if (!lastPeriodDate) return '?';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const lastPeriod = new Date(lastPeriodDate);
    lastPeriod.setHours(0, 0, 0, 0);
    const diffTime = today - lastPeriod;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return diffDays % cycleLength || cycleLength;
  };

  const renderPhaseInfo = () => {
    if (!currentPhase) return null;

    return (
      <View style={[styles.phaseCard, { borderLeftColor: currentPhase.color }]}>
        <View style={styles.phaseHeader}>
          <Ionicons name={currentPhase.icon} size={24} color={currentPhase.color} />
          <View style={styles.phaseTitleContainer}>
            <Text style={styles.phaseTitle}>Phase actuelle</Text>
            <Text style={styles.phaseName}>{currentPhase.name}</Text>
          </View>
        </View>
        <Text style={styles.phaseDescription}>{currentPhase.description}</Text>
        
        <View style={styles.tipsContainer}>
          <Text style={styles.tipsTitle}>💡 Conseils du moment :</Text>
          {currentPhase.tips.map((tip, index) => (
            <View key={index} style={styles.tipItem}>
              <Ionicons name="checkmark-circle" size={16} color={colors.primary.blue} />
              <Text style={styles.tipText}>{tip}</Text>
            </View>
          ))}
        </View>
      </View>
    );
  };

  const renderCalendarPreview = () => {
    const today = new Date();
    const days = [];
    
    // Afficher 7 jours autour d'aujourd'hui
    for (let i = -3; i <= 3; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      
      const isToday = i === 0;
      const dayCycle = getDayOfCycle();
      const adjustedDay = ((dayCycle + i - 1) % cycleLength) + 1;
      
      let dayType = 'normal';
      if (adjustedDay <= 5) dayType = 'period';
      else if (adjustedDay >= 12 && adjustedDay <= 16) dayType = 'fertile';
      else if (adjustedDay === 14) dayType = 'ovulation';
      
      days.push({ date, isToday, dayType, day: date.getDate() });
    }
    
    return (
      <View style={styles.calendarPreview}>
        {days.map((day, index) => (
          <View
            key={index}
            style={[
              styles.calendarDay,
              day.isToday && styles.calendarDayToday,
              day.dayType === 'period' && styles.calendarDayPeriod,
              day.dayType === 'fertile' && styles.calendarDayFertile,
              day.dayType === 'ovulation' && styles.calendarDayOvulation,
            ]}
          >
            <Text
              style={[
                styles.calendarDayText,
                day.isToday && styles.calendarDayTextToday,
              ]}
            >
              {day.day}
            </Text>
            {day.dayType !== 'normal' && (
              <View
                style={[
                  styles.calendarDot,
                  day.dayType === 'period' && styles.dotPeriod,
                  day.dayType === 'fertile' && styles.dotFertile,
                  day.dayType === 'ovulation' && styles.dotOvulation,
                ]}
              />
            )}
          </View>
        ))}
      </View>
    );
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Mon Cycle</Text>
            <Text style={styles.headerSubtitle}>
              Jour {getDayOfCycle()} de votre cycle
            </Text>
          </View>
          <TouchableOpacity
            style={styles.infoButton}
            onPress={() => setShowCycleInfo(true)}
          >
            <Ionicons name="information-circle-outline" size={24} color={colors.primary.rose} />
          </TouchableOpacity>
        </View>

        {/* Phase actuelle */}
        {renderPhaseInfo()}

        {/* Prochaines règles */}
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <View style={styles.infoIconContainer}>
              <Ionicons name="calendar" size={20} color={colors.primary.white} />
            </View>
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Prochaines règles</Text>
              <Text style={styles.infoValue}>
                {formatDate(nextPeriod)}
              </Text>
              <Text style={styles.infoSubtext}>
                Dans {getDaysUntil(nextPeriod)} jours
              </Text>
            </View>
          </View>
        </View>

        {/* Ovulation */}
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <View style={[styles.infoIconContainer, { backgroundColor: colors.primary.orange }]}>
              <Ionicons name="egg" size={20} color={colors.primary.white} />
            </View>
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Ovulation estimée</Text>
              <Text style={styles.infoValue}>
                {formatDate(ovulationDate)}
              </Text>
              <Text style={styles.infoSubtext}>
                Dans {getDaysUntil(ovulationDate)} jours
              </Text>
            </View>
          </View>
        </View>

        {/* Fenêtre de fertilité */}
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <View style={[styles.infoIconContainer, { backgroundColor: '#E91E63' }]}>
              <Ionicons name="heart" size={20} color={colors.primary.white} />
            </View>
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Fenêtre de fertilité</Text>
              <Text style={styles.infoValue}>
                {fertileWindow ? `${formatDate(fertileWindow.start)} - ${formatDate(fertileWindow.end)}` : 'Non défini'}
              </Text>
              <Text style={styles.infoSubtext}>
                Période la plus fertile
              </Text>
            </View>
          </View>
        </View>

        {/* Aperçu calendrier */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Aperçu des 7 prochains jours</Text>
          {renderCalendarPreview()}
          
          <View style={styles.legend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, styles.dotPeriod]} />
              <Text style={styles.legendText}>Règles</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, styles.dotFertile]} />
              <Text style={styles.legendText}>Fertile</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, styles.dotOvulation]} />
              <Text style={styles.legendText}>Ovulation</Text>
            </View>
          </View>
        </View>

        {/* Bouton pour enregistrer les règles */}
        <TouchableOpacity
          style={styles.recordButton}
          onPress={() => setShowDatePicker(true)}
        >
          <Ionicons name="add-circle" size={24} color={colors.primary.white} />
          <Text style={styles.recordButtonText}>Enregistrer mes règles</Text>
        </TouchableOpacity>

        {/* Historique des cycles */}
        {cycles.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Historique récent</Text>
            {cycles.slice(0, 3).map((cycle, index) => (
              <View key={index} style={styles.cycleHistoryItem}>
                <Text style={styles.cycleHistoryDate}>
                  {formatDate(new Date(cycle.startDate))}
                </Text>
                <Text style={styles.cycleHistoryLength}>
                  Cycle de {cycle.cycleLength} jours
                </Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      {/* Modal pour sélectionner la date */}
      <Modal
        visible={showDatePicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowDatePicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Date de début des règles</Text>
            <Text style={styles.modalSubtitle}>
              Sélectionnez la date de début de vos dernières règles
            </Text>
            
            <TouchableOpacity
              style={styles.todayButton}
              onPress={() => saveLastPeriod(new Date())}
            >
              <Ionicons name="calendar" size={20} color={colors.primary.rose} />
              <Text style={styles.todayButtonText}>Aujourd'hui</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.yesterdayButton}
              onPress={() => {
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                saveLastPeriod(yesterday);
              }}
            >
              <Ionicons name="time" size={20} color={colors.primary.orange} />
              <Text style={styles.yesterdayButtonText}>Hier</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowDatePicker(false)}
            >
              <Text style={styles.closeButtonText}>Annuler</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Modal pour informations éducatives */}
      <Modal
        visible={showCycleInfo}
        transparent
        animationType="slide"
        onRequestClose={() => setShowCycleInfo(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Comprendre son cycle</Text>
              <TouchableOpacity onPress={() => setShowCycleInfo(false)}>
                <Ionicons name="close" size={24} color={colors.text.secondary} />
              </TouchableOpacity>
            </View>
            
            <FlatList
              data={cycleEducation.phases}
              keyExtractor={(item) => item.name}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.phaseInfoItem}
                  onPress={() => setSelectedPhase(item)}
                >
                  <Text style={styles.phaseInfoName}>{item.name}</Text>
                  <Text style={styles.phaseInfoDuration}>{item.duration}</Text>
                  <Ionicons name="chevron-forward" size={20} color={colors.text.light} />
                </TouchableOpacity>
              )}
            />
          </View>
        </View>
      </Modal>
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
    alignItems: 'center',
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
  infoButton: {
    padding: theme.spacing.sm,
  },
  phaseCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    marginHorizontal: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    borderLeftWidth: 4,
    ...theme.shadows.md,
  },
  phaseHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  phaseTitleContainer: {
    marginLeft: theme.spacing.md,
  },
  phaseTitle: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  phaseName: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  phaseDescription: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 22,
    marginBottom: theme.spacing.md,
  },
  tipsContainer: {
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
  },
  tipsTitle: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xs,
  },
  tipText: {
    flex: 1,
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
  },
  infoCard: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    marginHorizontal: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    ...theme.shadows.sm,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  infoIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  infoContent: {
    flex: 1,
  },
  infoLabel: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  infoValue: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginTop: theme.spacing.xs,
  },
  infoSubtext: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    marginTop: theme.spacing.xs,
  },
  section: {
    marginTop: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
  },
  sectionTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.md,
  },
  calendarPreview: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.shadows.sm,
  },
  calendarDay: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 40,
    height: 50,
    borderRadius: theme.borderRadius.md,
  },
  calendarDayToday: {
    backgroundColor: colors.primary.rose,
  },
  calendarDayPeriod: {
    backgroundColor: `${colors.primary.rose}15`,
  },
  calendarDayFertile: {
    backgroundColor: `${colors.primary.orange}15`,
  },
  calendarDayOvulation: {
    backgroundColor: `${'#E91E63'}15`,
  },
  calendarDayText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.secondary,
  },
  calendarDayTextToday: {
    color: colors.primary.white,
    fontWeight: theme.typography.weights.bold,
  },
  calendarDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 4,
  },
  dotPeriod: {
    backgroundColor: colors.primary.rose,
  },
  dotFertile: {
    backgroundColor: colors.primary.orange,
  },
  dotOvulation: {
    backgroundColor: '#E91E63',
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: theme.spacing.md,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
  },
  recordButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary.rose,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    margin: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  recordButtonText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  cycleHistoryItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  cycleHistoryDate: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.primary,
  },
  cycleHistoryLength: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.primary.white,
    borderTopLeftRadius: theme.borderRadius.xl,
    borderTopRightRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  modalTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  modalSubtitle: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    marginBottom: theme.spacing.lg,
    textAlign: 'center',
  },
  todayButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: `${colors.primary.rose}10`,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    gap: theme.spacing.sm,
  },
  todayButtonText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.rose,
  },
  yesterdayButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: `${colors.primary.orange}10`,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  yesterdayButtonText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.orange,
  },
  closeButton: {
    padding: theme.spacing.md,
    alignItems: 'center',
  },
  closeButtonText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  phaseInfoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
  },
  phaseInfoName: {
    flex: 1,
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.text.primary,
  },
  phaseInfoDuration: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    marginRight: theme.spacing.sm,
  },
});

export default CycleScreen;