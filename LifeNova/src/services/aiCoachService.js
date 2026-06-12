/**
 * LifeNova AI Coach Service
 * Cerveau principal - Coach personnel intelligent
 */

import { cycleService } from './cycleService';
import { cycleInsightsService } from './cycleInsightsService';

/**
 * Objectifs possibles
 */
export const GOALS = {
  productivity: { label: 'Productivité', icon: 'rocket', color: '#FF4FA3' },
  health: { label: 'Santé', icon: 'heart', color: '#10B981' },
  studies: { label: 'Études', icon: 'book', color: '#2D7CFF' },
  work: { label: 'Travail', icon: 'briefcase', color: '#8B5CF6' },
  wellness: { label: 'Bien-être', icon: 'spa', color: '#FF8A3D' },
  personal: { label: 'Développement personnel', icon: 'trending-up', color: '#EC4899' },
};

/**
 * Niveaux pour les check-ins
 */
export const MOOD_LEVELS = [
  { value: 1, emoji: '😢', label: 'Très bas' },
  { value: 2, emoji: '😔', label: 'Bas' },
  { value: 3, emoji: '😐', label: 'Neutre' },
  { value: 4, emoji: '😊', label: 'Bon' },
  { value: 5, emoji: '🤩', label: 'Excellent' },
];

export const ENERGY_LEVELS = [
  { value: 1, emoji: '🔋', label: 'Très faible' },
  { value: 2, emoji: '🪫', label: 'Faible' },
  { value: 3, emoji: '⚡', label: 'Normale' },
  { value: 4, emoji: '💪', label: 'Élevée' },
  { value: 5, emoji: '🚀', label: 'Maximale' },
];

export const STRESS_LEVELS = [
  { value: 1, emoji: '🧘', label: 'Très détendu' },
  { value: 2, emoji: '😌', label: 'Calme' },
  { value: 3, emoji: '😐', label: 'Modéré' },
  { value: 4, emoji: '😰', label: 'Élevé' },
  { value: 5, emoji: '🤯', label: 'Très stressé' },
];

export const SLEEP_QUALITY = [
  { value: 1, emoji: '😫', label: 'Mauvais' },
  { value: 2, emoji: '😴', label: 'Moyen' },
  { value: 3, emoji: '😪', label: 'Correct' },
  { value: 4, emoji: '😊', label: 'Bon' },
  { value: 5, emoji: '🌟', label: 'Excellent' },
];

/**
 * Base de connaissances pour le coach IA
 */
const coachKnowledge = {
  motivation: {
    keywords: ['motivation', 'motivé', 'envie', 'booster', 'dynamique'],
    responses: [
      "La motivation vient de l'action, pas l'inverse. Commencez par une petite tâche facile pour lancer la machine ! 🚀",
      "Rappelez-vous pourquoi vous avez commencé. Votre objectif LifeNova est là pour une raison importante. ✨",
      "La motivation, c'est comme une douche : ça ne dure pas, c'est pourquoi on en a besoin chaque jour. Quelle petite action pouvez-vous faire maintenant ?",
    ],
  },
  productivity: {
    keywords: ['productif', 'productivité', 'efficace', 'organisation', 'temps'],
    responses: [
      "Essayez la technique Pomodoro : 25 min de focus total, 5 min de pause. Répétez 4 fois puis pause longue. 🍅",
      "La règle des 2 minutes : si une tâche prend moins de 2 minutes, faites-la maintenant. Ça libère l'esprit ! ⚡",
      "Mangez la grenouille : commencez par la tâche la plus difficile. Le reste semblera facile en comparaison ! 🐸",
      "Divisez vos grandes tâches en micro-étapes. Une montagne se gravit pas à pas. 🏔️",
    ],
  },
  stress: {
    keywords: ['stress', 'stressé', 'anxiété', 'angoisse', 'pression'],
    responses: [
      "Prenez 3 profondes respirations. Inspirez 4 secondes, retenez 4 secondes, expirez 6 secondes. Répétez 5 fois. 🧘‍♀️",
      "Le stress vient souvent de ce qu'on ne contrôle pas. Concentrez-vous sur ce que vous POUVEZ faire maintenant. 💪",
      "Écrivez tout ce qui vous préoccupe sur papier. Voir ses soucis noir sur blanc aide à les relativiser. 📝",
      "Une marche de 10 minutes peut réduire significativement le stress. Le mouvement libère des endorphines. 🚶‍♀️",
    ],
  },
  sleep: {
    keywords: ['sommeil', 'dormir', 'fatigué', 'insomnie', 'nuit'],
    responses: [
      "Établissez une routine du coucher : même heure, pas d'écrans 1h avant, lecture ou méditation. 😴",
      "Votre chambre doit être fraîche (18-19°C), sombre et silencieuse. Investissez dans un bon oreiller ! 🛏️",
      "Évitez caféine après 14h et repas lourds le soir. Privilégiez les tisanes (camomille, verveine). 🍵",
      "Si vous ne dormez pas après 20 min, levez-vous et faites une activité calme. Le lit = sommeil uniquement. 📖",
    ],
  },
  energy: {
    keywords: ['énergie', 'fatigue', 'épuisé', 'vitalité', 'coup de barre'],
    responses: [
      "L'hydratation est clé ! Buvez un grand verre d'eau. La déshydratation cause souvent de la fatigue. 💧",
      "Une collation protéinée (amandes, yaourt) donne de l'énergie durable, contrairement au sucre rapide. 🥜",
      "5 minutes d'étirements ou de marche peuvent relancer votre énergie mieux qu'un café. Essayez ! 🏃‍♀️",
      "Vérifiez votre apport en fer et vitamine D. Une carence peut expliquer une fatigue persistante. 🌞",
    ],
  },
  goals: {
    keywords: ['objectif', 'but', 'projet', 'ambition', 'rêve'],
    responses: [
      "Utilisez la méthode SMART : Spécifique, Mesurable, Atteignable, Réaliste, Temporel. 🎯",
      "Visualisez-vous ayant atteint votre objectif. Comment vous sentez-vous ? Cette image vous guidera. ✨",
      "Partagez vos objectifs avec quelqu'un. La responsabilité sociale augmente considérablement les chances de succès. 🤝",
      "Célébrez chaque petite victoire. Le cerveau adore les récompenses et ça motive à continuer. 🎉",
    ],
  },
  focus: {
    keywords: ['concentration', 'focus', 'distraction', 'attention', 'distrait'],
    responses: [
      "Éliminez les distractions : téléphone en mode avion, notifications désactivées, environnement calme. 📵",
      "Travaillez par blocs de 90 min max. Le cerveau ne peut pas se concentrer intensément plus longtemps. 🧠",
      "La musique instrumentale ou les bruits blancs (nature, café) peuvent améliorer la concentration. 🎵",
      "Entraînez votre focus comme un muscle : commencez par 15 min, puis augmentez progressivement. 💪",
    ],
  },
};

/**
 * Répondre comme un coach
 */
export const coachResponse = (message, userProfile, recentCheckins = []) => {
  const lowerMessage = message.toLowerCase();
  
  // Trouver la catégorie la plus pertinente
  let bestMatch = null;
  let bestScore = 0;

  for (const [category, data] of Object.entries(coachKnowledge)) {
    const matchCount = data.keywords.filter(keyword => 
      lowerMessage.includes(keyword)
    ).length;
    
    if (matchCount > bestScore) {
      bestScore = matchCount;
      bestMatch = data;
    }
  }

  // Si aucune correspondance, réponse générique
  if (!bestMatch || bestScore === 0) {
    return {
      response: "Je suis là pour vous accompagner ! Je peux vous aider avec : la motivation, la productivité, le stress, le sommeil, l'énergie, les objectifs ou la concentration. Dites-moi ce qui vous préoccupe. 🌟",
      category: 'general',
    };
  }

  // Choisir une réponse aléatoire dans la catégorie
  const responses = bestMatch.responses;
  const randomIndex = Math.floor(Math.random() * responses.length);
  
  // Personnaliser avec le prénom si disponible
  let response = responses[randomIndex];
  if (userProfile?.firstName) {
    response = `${response}\n\nContinuez comme ça${userProfile.firstName ? ', ' + userProfile.firstName : ''} ! 💪`;
  }

  return {
    response,
    category: bestMatch,
  };
};

/**
 * Générer le plan du jour
 */
export const generateDailyPlan = (userProfile, currentPhase = null) => {
  const plans = [
    {
      priority: 'Commencez par votre tâche la plus importante',
      advice: 'Une chose à la fois. La qualité prime sur la quantité.',
      mission: 'Aujourd\'hui, je me concentre sur l\'essentiel.',
    },
    {
      priority: 'Prenez soin de votre énergie',
      advice: 'Faites des pauses régulières et hydratez-vous.',
      mission: 'Aujourd\'hui, j\'écoute mon corps.',
    },
    {
      priority: 'Avancez sur un projet qui vous tient à cœur',
      advice: 'Même 15 minutes par jour font la différence.',
      mission: 'Aujourd\'hui, je fais un pas vers mon rêve.',
    },
    {
      priority: 'Connectez-vous avec vos proches',
      advice: 'Les relations sont le pilier du bien-être.',
      mission: 'Aujourd\'hui, je cultive mes relations.',
    },
  ];

  const quotes = [
    "Le seul moyen de faire du bon travail est d'aimer ce que vous faites. - Steve Jobs",
    "La vie, c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre. - Einstein",
    "Il n'est jamais trop tard pour devenir ce que vous auriez dû être. - George Eliot",
    "Le succès, c'est d'aller d'échec en échec sans perdre son enthousiasme. - Churchill",
    "Votre temps est limité, ne le gâchez pas en menant une existence qui n'est pas la vôtre. - Steve Jobs",
    "La meilleure façon de prédire l'avenir est de le créer. - Peter Drucker",
    "Commencez là où vous êtes. Utilisez ce que vous avez. Faites ce que vous pouvez. - Arthur Ashe",
    "Ce n'est pas parce que les choses sont difficiles que nous n'osons pas, c'est parce que nous n'osons pas qu'elles sont difficiles. - Sénèque",
  ];

  // Sélectionner en fonction de la phase ou aléatoirement
  let planIndex = 0;
  if (currentPhase) {
    const phaseName = currentPhase.name.toLowerCase();
    if (phaseName.includes('règle')) planIndex = 1;
    else if (phaseName.includes('folliculaire')) planIndex = 2;
    else if (phaseName.includes('ovulation')) planIndex = 0;
    else if (phaseName.includes('lutéale')) planIndex = 3;
  } else {
    planIndex = Math.floor(Math.random() * plans.length);
  }

  const quoteIndex = Math.floor(Math.random() * quotes.length);

  return {
    ...plans[planIndex],
    quote: quotes[quoteIndex],
  };
};

/**
 * Calculer le score LifeNova
 */
export const calculateLifeScore = (userProfile, checkins = [], cycles = [], tasks = []) => {
  let score = 50; // Score de base

  // Facteur 1: Cohérence des check-ins (25 points max)
  const checkinConsistency = checkins.length > 0 ? Math.min(25, (checkins.length / 7) * 25) : 0;
  score += checkinConsistency;

  // Facteur 2: Activité / tâches complétées (25 points max)
  const taskCompletion = tasks.length > 0 ? Math.min(25, (tasks.filter(t => t.completed).length / Math.max(tasks.length, 5)) * 25) : 0;
  score += taskCompletion;

  // Facteur 3: Progression (25 points max)
  const progression = userProfile?.goalsCompleted ? Math.min(25, (userProfile.goalsCompleted / Math.max(userProfile.goalsTotal || 1, 1)) * 25) : 10;
  score += progression;

  // Facteur 4: Régularité (25 points max)
  const regularity = cycles.length > 0 ? cycleInsightsService.calculateRegularityScore(cycles).score / 4 : 10;
  score += regularity;

  return {
    score: Math.round(Math.max(0, Math.min(100, score))),
    breakdown: {
      consistency: Math.round(checkinConsistency),
      activity: Math.round(taskCompletion),
      progression: Math.round(progression),
      regularity: Math.round(regularity),
    },
    message: getScoreMessage(score),
  };
};

const getScoreMessage = (score) => {
  if (score >= 90) return "Excellent ! Vous êtes au top de votre forme LifeNova ! 🌟";
  if (score >= 75) return "Très bien ! Continuez sur cette lancée. 💪";
  if (score >= 50) return "Pas mal ! Quelques ajustements et ce sera parfait. 📈";
  if (score >= 25) return "En progression ! Petits pas, grands résultats. 🌱";
  return "Commencez doucement. Chaque jour compte. ✨";
};

/**
 * Export du service
 */
export const aiCoachService = {
  GOALS,
  MOOD_LEVELS,
  ENERGY_LEVELS,
  STRESS_LEVELS,
  SLEEP_QUALITY,
  coachResponse,
  generateDailyPlan,
  calculateLifeScore,
  getScoreMessage,
};

export default aiCoachService;