/**
 * LifeNova Cycle Insights Service
 * Analyse intelligente des données de cycle et symptômes
 */

import { cycleService } from './cycleService';

/**
 * Calculer le score de régularité du cycle
 * Basé sur la variation des durées de cycles précédents
 */
export const calculateRegularityScore = (cycles) => {
  if (!cycles || cycles.length < 2) {
    return {
      score: 0,
      averageCycleLength: cycleService.AVERAGE_CYCLE_LENGTH,
      variation: 0,
      message: 'Enregistrez plus de cycles pour obtenir un score.',
    };
  }

  const lengths = cycles.map(c => c.cycleLength || cycleService.AVERAGE_CYCLE_LENGTH);
  const avg = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  const variations = lengths.map(l => Math.abs(l - avg));
  const avgVariation = variations.reduce((a, b) => a + b, 0) / variations.length;

  // Score basé sur la variation moyenne
  // 0 variation = 100%, 7+ variation = 0%
  let score = Math.max(0, Math.min(100, Math.round(100 - (avgVariation / 7) * 100)));

  return {
    score,
    averageCycleLength: Math.round(avg),
    variation: Math.round(avgVariation),
    message: getRegularityMessage(score, avgVariation),
  };
};

const getRegularityMessage = (score, variation) => {
  if (score >= 90) return 'Vos cycles sont très réguliers ! 🌟';
  if (score >= 75) return 'Vos cycles sont assez réguliers. 👍';
  if (score >= 50) return 'Vos cycles montrent une régularité moyenne. 📊';
  return 'Vos cycles sont irréguliers. Consultez si cela vous inquiète. 💡';
};

/**
 * Analyser les symptômes sur une période
 */
export const analyzeSymptoms = (symptoms, lastPeriodDate) => {
  if (!symptoms || symptoms.length === 0) {
    return {
      insights: ['Commencez à enregistrer vos symptômes pour obtenir des analyses.'],
      moodTrend: 'neutral',
      energyTrend: 'neutral',
      painPattern: 'none',
      sleepQuality: 'unknown',
    };
  }

  const insights = [];

  // Analyser l'humeur
  const moods = symptoms.map(s => s.mood).filter(Boolean);
  const moodCounts = moods.reduce((acc, mood) => {
    acc[mood] = (acc[mood] || 0) + 1;
    return acc;
  }, {});
  const dominantMood = Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0];
  
  if (dominantMood) {
    const [mood, count] = dominantMood;
    const percentage = Math.round((count / moods.length) * 100);
    insights.push(`Votre humeur dominante est "${getMoodLabel(mood)}" (${percentage}% des jours).`);
  }

  // Analyser l'énergie
  const energies = symptoms.map(s => s.energy).filter(Boolean);
  const lowEnergyCount = energies.filter(e => e === 'low' || e === 'very_low').length;
  const lowEnergyPercentage = energies.length > 0 ? Math.round((lowEnergyCount / energies.length) * 100) : 0;
  
  if (lowEnergyPercentage > 40) {
    insights.push(`Vous signalez une baisse d'énergie ${lowEnergyPercentage}% du temps. Cela peut être lié à votre cycle.`);
  }

  // Analyser la douleur
  const pains = symptoms.map(s => s.pain).filter(Boolean);
  const significantPainCount = pains.filter(p => p === 'moderate' || p === 'severe').length;
  const painPercentage = pains.length > 0 ? Math.round((significantPainCount / pains.length) * 100) : 0;

  if (painPercentage > 30) {
    insights.push(`Vous ressentez des douleurs significatives ${painPercentage}% du temps. Des techniques de relaxation peuvent aider.`);
  }

  // Analyser le sommeil
  const sleeps = symptoms.map(s => s.sleep).filter(Boolean);
  const poorSleepCount = sleeps.filter(s => s === 'poor' || s === 'fair').length;
  const poorSleepPercentage = sleeps.length > 0 ? Math.round((poorSleepCount / sleeps.length) * 100) : 0;

  if (poorSleepPercentage > 40) {
    insights.push(`Votre qualité de sommeil est mitigée ${poorSleepPercentage}% du temps. Essayez une routine relaxante avant de dormir.`);
  }

  // Tendance générale
  const moodTrend = dominantMood ? dominantMood[0] : 'neutral';
  const energyTrend = lowEnergyPercentage > 50 ? 'low' : 'normal';
  const painPattern = painPercentage > 30 ? 'frequent' : 'occasional';
  const sleepQuality = poorSleepPercentage > 40 ? 'poor' : 'good';

  return {
    insights,
    moodTrend,
    energyTrend,
    painPattern,
    sleepQuality,
  };
};

/**
 * Générer des insights basés sur la phase du cycle
 */
export const getPhaseInsights = (currentPhase, symptoms) => {
  if (!currentPhase) return [];

  const insights = [];
  const phaseName = currentPhase.name.toLowerCase();

  // Insights basés sur la phase
  if (phaseName.includes('règle') || phaseName.includes('menstruation')) {
    insights.push('Pendant les règles, il is normal de se sentir plus fatiguée. Écoutez votre corps.');
    
    const recentPain = symptoms?.filter(s => s.pain === 'moderate' || s.pain === 'severe').length || 0;
    if (recentPain > 2) {
      insights.push('Vos douleurs semblent importantes ce cycle. La chaleur et le repos peuvent aider.');
    }
  } else if (phaseName.includes('folliculaire')) {
    insights.push('La phase folliculaire est propice aux projets créatifs et à l\'énergie. Profitez-en !');
  } else if (phaseName.includes('ovulation')) {
    insights.push('Pendant l\'ovulation, votre énergie et votre libido peuvent être au plus haut.');
  } else if (phaseName.includes('lutéale')) {
    insights.push('La phase lutéale peut apporter des changements d\'humeur. Pratiquez l\'auto-compassion.');
    
    const recentMood = symptoms?.slice(-7).map(s => s.mood) || [];
    const negativeMoods = recentMood.filter(m => m === 'sad' || m === 'stressed').length;
    if (negativeMoods > 3) {
      insights.push('Vous semblez plus sensible ces derniers jours, ce qui est courant en phase lutéale.');
    }
  }

  return insights;
};

/**
 * Labels pour les valeurs de symptômes
 */
const getMoodLabel = (mood) => {
  const labels = {
    'very_happy': 'Très heureuse',
    'happy': 'Heureuse',
    'neutral': 'Neutre',
    'sad': 'Triste',
    'stressed': 'Stressée',
  };
  return labels[mood] || mood;
};

const getEnergyLabel = (energy) => {
  const labels = {
    'very_low': 'Très faible',
    'low': 'Faible',
    'normal': 'Normale',
    'high': 'Élevée',
  };
  return labels[energy] || energy;
};

const getPainLabel = (pain) => {
  const labels = {
    'none': 'Aucune',
    'mild': 'Légère',
    'moderate': 'Modérée',
    'severe': 'Forte',
  };
  return labels[pain] || pain;
};

const getSleepLabel = (sleep) => {
  const labels = {
    'excellent': 'Excellent',
    'good': 'Bon',
    'fair': 'Moyen',
    'poor': 'Mauvais',
  };
  return labels[sleep] || sleep;
};

/**
 * Export du service
 */
export const cycleInsightsService = {
  calculateRegularityScore,
  analyzeSymptoms,
  getPhaseInsights,
  getMoodLabel,
  getEnergyLabel,
  getPainLabel,
  getSleepLabel,
};

export default cycleInsightsService;