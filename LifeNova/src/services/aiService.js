/**
 * Service IA
 * Gère les interactions avec l'IA (simulation pour le MVP)
 * 
 * NOTE: Pour la production, remplacer par un vrai appel API vers OpenAI/Anthropic
 */

// Réponses simulées pour le MVP (à remplacer par de vrais appels API)
const AI_RESPONSES = {
  default: [
    "Je comprends votre demande. LifeNova est là pour vous aider à organiser votre vie et atteindre vos objectifs. Comment puis-je vous assister aujourd'hui ?",
    "C'est une excellente question ! Je vous recommande de commencer par définir vos priorités. Voulez-vous que je vous aide à créer un plan d'action ?",
    "Merci de partager cela avec moi. N'oubliez pas que chaque petit pas compte. Quelle est la prochaine action que vous pouvez faire dès aujourd'hui ?",
    "Je suis là pour vous accompagner. Prenons un moment pour réfléchir à votre situation. Quels sont les obstacles que vous rencontrez ?",
    "Votre bien-être est important. Avez-vous pris le temps de faire une pause aujourd'hui ? La productivité passe aussi par le repos.",
  ],
  
  motivation: [
    "🌟 Vous êtes capable de grandes choses ! Chaque jour est une nouvelle opportunité de progresser vers vos objectifs.",
    "💪 Rappelez-vous : le succès n'est pas une destination, mais un voyage. Continuez à avancer, même à petit pas !",
    "✨ Votre détermination est admirable. Gardez le cap, vos efforts porteront leurs fruits !",
    "🎯 Concentrez-vous sur ce que vous pouvez contrôler. Laissez aller ce qui ne dépend pas de vous.",
    "🚀 Aujourd'hui est le jour parfait pour commencer quelque chose de nouveau. Quelle est votre première étape ?",
  ],
  
  productivity: [
    "📋 Pour booster votre productivité, essayez la technique Pomodoro : 25 min de travail focalisé, puis 5 min de pause.",
    "🎯 Commencez par la tâche la plus importante de la journée. Le reste semblera plus facile ensuite !",
    "📊 Divisez vos grands projets en petites étapes réalisables. La progression devient ainsi plus tangible.",
    "⏰ Planifiez vos journées la veille au soir. Vous gagnerez un temps précieux le matin.",
    "🧹 Éliminez les distractions : mettez votre téléphone en mode silencieux et fermez les onglets inutiles.",
  ],
  
  greeting: [
    "Bonjour ! 👋 Je suis votre assistant LifeNova. Comment puis-je vous aider à organiser votre journée ?",
    "Salut ! 🌟 Prêt à faire de cette journée une réussite ? Je suis là pour vous accompagner.",
    "Bienvenue ! 💫 Que souhaitez-vous accomplir aujourd'hui ? Je peux vous aider avec vos tâches, votre organisation, ou simplement discuter.",
  ],
};

// Détection d'intention simple
const detectIntent = (message) => {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('bonjour') || lowerMessage.includes('salut') || lowerMessage.includes('hello')) {
    return 'greeting';
  }
  if (lowerMessage.includes('motivation') || lowerMessage.includes('encouragement') || lowerMessage.includes('motiver')) {
    return 'motivation';
  }
  if (lowerMessage.includes('productivité') || lowerMessage.includes('productif') || lowerMessage.includes('travail') || lowerMessage.includes('tâche')) {
    return 'productivity';
  }
  
  return 'default';
};

// Obtenir une réponse aléatoire selon l'intention
const getRandomResponse = (intent) => {
  const responses = AI_RESPONSES[intent] || AI_RESPONSES.default;
  const randomIndex = Math.floor(Math.random() * responses.length);
  return responses[randomIndex];
};

/**
 * Service IA
 */
export const aiService = {
  /**
   * Envoyer un message et obtenir une réponse
   * @param {string} message - Le message de l'utilisateur
   * @returns {Promise<string>} - La réponse de l'IA
   */
  sendMessage: async (message) => {
    // Simulation d'un délai de réflexion
    await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000));
    
    // Détection d'intention et réponse
    const intent = detectIntent(message);
    const response = getRandomResponse(intent);
    
    return response;
  },

  /**
   * Obtenir une réponse contextuelle basée sur l'historique
   * @param {string} message - Le message de l'utilisateur
   * @param {Array} history - L'historique de conversation
   * @returns {Promise<string>} - La réponse de l'IA
   */
  sendMessageWithContext: async (message, history = []) => {
    // Pour le MVP, on utilise la même logique
    // Dans la version production, on enverrait l'historique à l'API
    return aiService.sendMessage(message);
  },

  /**
   * Générer un conseil du jour
   * @returns {Promise<Object>} - Le conseil du jour
   */
  getDailyAdvice: async () => {
    const adviceTypes = [
      {
        type: 'motivation',
        text: '🌟 Aujourd\'hui, concentrez-vous sur une seule chose à la fois. La qualité prime sur la quantité.',
        action: 'Choisissez votre priorité absolue du jour',
      },
      {
        type: 'productivity',
        text: '📋 Commencez votre journée par la tâche la plus difficile. Le reste sera plus facile.',
        action: 'Identifiez votre "grenouille" à avaler en premier',
      },
      {
        type: 'wellness',
        text: '🧘 N\'oubliez pas de faire des pauses. Votre cerveau a besoin de repos pour être performant.',
        action: 'Programmez 3 pauses de 5 minutes dans votre journée',
      },
      {
        type: 'growth',
        text: '📚 Apprenez quelque chose de nouveau aujourd\'hui, même petit. La croissance continue est la clé.',
        action: 'Lisez 10 pages d\'un livre ou regardez un tutoriel',
      },
    ];

    const dayIndex = new Date().getDay() % adviceTypes.length;
    return adviceTypes[dayIndex];
  },

  /**
   * Analyser une tâche et suggérer des sous-étapes
   * @param {string} task - La tâche à analyser
   * @returns {Promise<Array>} - Liste de sous-étapes suggérées
   */
  analyzeTask: async (task) => {
    // Suggestions génériques pour le MVP
    const suggestions = [
      'Définir l\'objectif final clairement',
      'Identifier les ressources nécessaires',
      'Estimer le temps requis',
      'Planifier une échéance',
      'Commencer par la première étape simple',
    ];

    await new Promise((resolve) => setTimeout(resolve, 800));
    
    return suggestions.slice(0, 3); // Retourner 3 suggestions
  },
};

export default aiService;