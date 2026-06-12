/**
 * LifeNova Cycle AI Service
 * Assistant IA éducatif pour le cycle menstruel
 * IMPORTANT: Ne fournit jamais de diagnostic médical
 */

import { cycleService } from './cycleService';
import { cycleInsightsService } from './cycleInsightsService';

/**
 * Base de connaissances pour l'assistant IA
 */
const knowledgeBase = {
  fatigue: {
    keywords: ['fatiguée', 'fatigue', 'épuisée', 'énergie', 'faible', 'épuisement'],
    response: (context) => {
      const phase = context?.currentPhase?.name?.toLowerCase() || '';
      if (phase.includes('règle')) {
        return "Pendant les règles, la fatigue est normale due aux changements hormonaux et à la perte de fer. Reposez-vous et mangez des aliments riches en fer (viande rouge, épinards, lentilles).";
      } else if (phase.includes('lutéale')) {
        return "En phase lutéale, la progestérone augmente et peut causer de la fatigue. C'est temporaire. Essayez un sommeil régulier et une alimentation équilibrée.";
      } else if (phase.includes('folliculaire')) {
        return "La phase folliculaire est généralement une période d'énergie croissante. Si vous vous sentez fatiguée, vérifiez votre sommeil et votre alimentation.";
      }
      return "La fatigue peut être liée à de nombreux facteurs : sommeil, alimentation, stress, ou votre cycle. Essayez de noter vos symptômes pour identifier des patterns.";
    },
  },
  ovulation: {
    keywords: ['ovulation', 'ovuler', 'fertile', 'fécondation'],
    response: (context) => {
      if (context?.ovulationDate) {
        const daysUntil = Math.ceil((new Date(context.ovulationDate) - new Date()) / (1000 * 60 * 60 * 24));
        if (daysUntil <= 0) {
          return "Votre ovulation est estimée autour d'aujourd'hui. C'est votre période la plus fertile. Vous pourriez remarquer une glaire cervicale transparente et élastique.";
        } else if (daysUntil <= 3) {
          return `Votre ovulation est estimée dans ${daysUntil} jours. Votre fenêtre fertile commence maintenant. C'est le moment idéal si vous essayez de concevoir.`;
        } else {
          return `Votre ovulation est estimée dans ${daysUntil} jours. Votre fenêtre fertile commencera environ 5 jours avant cette date.`;
        }
      }
      return "L'ovulation se produit généralement 14 jours avant les prochaines règles. Les signes incluent : glaire cervicale transparente, légère douleur d'un côté, libido augmentée.";
    },
  },
  cycle_length: {
    keywords: ['cycle', 'durée', 'jours', 'régulier', 'irrégulier'],
    response: (context) => {
      const avgCycle = context?.regularity?.averageCycleLength || 28;
      if (avgCycle >= 21 && avgCycle <= 35) {
        return `Un cycle de ${avgCycle} jours est dans la norme (21-35 jours). La régularité est plus importante que la durée exacte. Continuez à suivre pour observer vos patterns.`;
      } else if (avgCycle < 21) {
        return `Un cycle de ${avgCycle} jours est court. Des cycles irrégulièrement courts peuvent être liés au stress, à l'exercice intensif, ou à des déséquilibres hormonaux. Consultez si cela persiste.`;
      } else {
        return `Un cycle de ${avgCycle} jours est long. Des cycles >35 jours peuvent être normaux pour certaines femmes, mais consultez si c'est nouveau ou irrégulier.`;
      }
    },
  },
  pain: {
    keywords: ['douleur', 'crampes', 'règles douloureuses', 'mal au ventre', 'spasmes'],
    response: (context) => {
      const phase = context?.currentPhase?.name?.toLowerCase() || '';
      if (phase.includes('règle')) {
        return "Les crampes menstruelles sont causées par les contractions utérines. Essayez : bouillotte, exercice léger, infusion de camomille, magnésium. Si les douleurs sont invalidantes, consultez.";
      }
      return "Les douleurs pelviennes peuvent avoir diverses causes. Notez leur intensité et timing. Si elles sont sévères ou inhabituelles, consultez un professionnel de santé.";
    },
  },
  mood: {
    keywords: ['humeur', 'triste', 'déprimée', 'anxieuse', 'stress', 'émotion'],
    response: (context) => {
      const phase = context?.currentPhase?.name?.toLowerCase() || '';
      if (phase.includes('lutéale')) {
        return "Les changements d'humeur en phase lutéale sont courants dus aux fluctuations hormonales. Pratiquez l'auto-compassion, faites de l'exercice doux, et parlez-en si besoin.";
      } else if (phase.includes('règle')) {
        return "Pendant les règles, les hormones sont basses, ce qui peut affecter l'humeur. Reposez-vous et faites des activités qui vous font du bien.";
      }
      return "L'humeur peut être influencée by many facteurs dont le cycle. Tenir un journal peut aider à identifier des patterns. Si les symptômes sont sévères, parlez-en à un professionnel.";
    },
  },
  sleep: {
    keywords: ['sommeil', 'insomnie', 'dormir', 'nuit', 'réveillée'],
    response: (context) => {
      const phase = context?.currentPhase?.name?.toLowerCase() || '';
      if (phase.includes('lutéale')) {
        return "Les troubles du sommeil en phase lutéale sont fréquents à cause de l'augmentation de la température corporelle et de la progestérone. Essayez une chambre fraîche et une routine relaxante.";
      }
      return "Le sommeil peut être affecté par le cycle. Établissez une routine régulière, limitez les écrans avant de dormir, et évitez la caféine l'après-midi.";
    },
  },
  fertility: {
    keywords: ['enceinte', 'concevoir', 'bébé', 'fertile', 'grossesse'],
    response: () => {
      return "Votre fenêtre fertile comprend les 5 jours avant l'ovulation et le jour de l'ovulation. Les rapports tous les 2-3 jours pendant cette période maximisent les chances. La glaire cervicale transparente indique l'approche de l'ovulation.";
    },
  },
  symptoms: {
    keywords: ['symptôme', 'signe', 'ressentir', 'sensation'],
    response: (context) => {
      const phase = context?.currentPhase;
      if (phase) {
        return `Pendant la phase de ${phase.name.toLowerCase()}, il est courant de ressentir : ${phase.description.toLowerCase()}. Notez vos symptômes pour mieux comprendre votre corps.`;
      }
      return "Chaque phase du cycle apporte son lot de symptômes. Tenez un journal pour identifier vos patterns personnels.";
    },
  },
};

/**
 * Traiter une question de l'utilisatrice
 */
export const processQuestion = (question, context = {}) => {
  const lowerQuestion = question.toLowerCase();
  
  // Trouver la catégorie la plus pertinente
  let bestMatch = null;
  let bestScore = 0;

  for (const [category, data] of Object.entries(knowledgeBase)) {
    const matchCount = data.keywords.filter(keyword => 
      lowerQuestion.includes(keyword)
    ).length;
    
    if (matchCount > bestScore) {
      bestScore = matchCount;
      bestMatch = data;
    }
  }

  // Si aucune correspondance, réponse générique
  if (!bestMatch || bestScore === 0) {
    return {
      answer: "Je n'ai pas assez d'informations pour répondre précisément à cette question. Je peux vous aider avec : la fatigue, l'ovulation, la durée du cycle, les douleurs, l'humeur, le sommeil, ou la fertilité. N'hésitez pas à reformuler.",
      disclaimer: true,
    };
  }

  // Générer la réponse avec le contexte
  const answer = bestMatch.response(context);

  return {
    answer,
    disclaimer: true, // Toujours ajouter le disclaimer
  };
};

/**
 * Préparer le contexte pour l'assistant
 */
export const buildContext = (cycleData, symptoms = [], regularity = null) => {
  const today = new Date();
  const lastPeriod = cycleData?.lastPeriodDate ? new Date(cycleData.lastPeriodDate) : null;
  
  const context = {
    currentPhase: lastPeriod ? cycleService.getCyclePhase(cycleData.lastPeriodDate, cycleData.cycleLength) : null,
    ovulationDate: lastPeriod ? cycleService.calculateOvulation(cycleData.lastPeriodDate, cycleData.cycleLength) : null,
    nextPeriod: lastPeriod ? cycleService.calculateNextPeriod(cycleData.lastPeriodDate, cycleData.cycleLength) : null,
    regularity: regularity || cycleInsightsService.calculateRegularityScore(cycleData.cycles || []),
    symptoms: symptoms,
  };

  return context;
};

/**
 * Réponses rapides suggérées
 */
export const getQuickQuestions = (currentPhase) => {
  const questions = [
    "Pourquoi suis-je fatiguée aujourd'hui ?",
    "Quand aura lieu mon ovulation ?",
    "Que signifie un cycle de 28 jours ?",
    "Comment soulager les douleurs menstruelles ?",
  ];

  // Ajouter des questions contextuelles basées sur la phase
  if (currentPhase) {
    const phaseName = currentPhase.name.toLowerCase();
    if (phaseName.includes('règle')) {
      questions.push("Pourquoi ai-je des crampes ?");
      questions.push("Comment gérer la fatigue des règles ?");
    } else if (phaseName.includes('ovulation')) {
      questions.push("Suis-je dans ma fenêtre fertile ?");
      questions.push("Comment savoir si j'ovule ?");
    } else if (phaseName.includes('lutéale')) {
      questions.push("Pourquoi suis-je plus sensible ?");
      questions.push("Comment mieux dormir en phase lutéale ?");
    }
  }

  return questions.slice(0, 5);
};

/**
 * Disclaimer médical obligatoire
 */
export const MEDICAL_DISCLAIMER = "⚠️ Cette information est fournie à titre éducatif uniquement et ne remplace pas un avis médical professionnel. Consultez toujours un professionnel de santé pour des préoccupations médicales.";

/**
 * Export du service
 */
export const cycleAiService = {
  processQuestion,
  buildContext,
  getQuickQuestions,
  MEDICAL_DISCLAIMER,
  knowledgeBase,
};

export default cycleAiService;