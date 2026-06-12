/**
 * Service de suivi du cycle menstruel
 * Calcul des règles, ovulation, et informations éducatives
 */

// Durée moyenne du cycle (peut être personnalisée)
const AVERAGE_CYCLE_LENGTH = 28;
const AVERAGE_LUTEAL_PHASE = 14; // Phase lutéale (après ovulation)
const AVERAGE_PERIOD_LENGTH = 5; // Durée moyenne des règles

/**
 * Calculer la date d'ovulation estimée
 * L'ovulation se produit généralement 14 jours avant les prochaines règles
 */
const calculateOvulation = (lastPeriodDate, cycleLength = AVERAGE_CYCLE_LENGTH) => {
  const lastPeriod = new Date(lastPeriodDate);
  const ovulationDay = cycleLength - AVERAGE_LUTEAL_PHASE;
  const ovulationDate = new Date(lastPeriod);
  ovulationDate.setDate(lastPeriod.getDate() + ovulationDay);
  return ovulationDate;
};

/**
 * Calculer la date des prochaines règles
 */
const calculateNextPeriod = (lastPeriodDate, cycleLength = AVERAGE_CYCLE_LENGTH) => {
  const lastPeriod = new Date(lastPeriodDate);
  const nextPeriod = new Date(lastPeriod);
  nextPeriod.setDate(lastPeriod.getDate() + cycleLength);
  return nextPeriod;
};

/**
 * Calculer la fenêtre de fertilité
 * Les 5 jours avant l'ovulation + jour de l'ovulation
 */
const calculateFertileWindow = (lastPeriodDate, cycleLength = AVERAGE_CYCLE_LENGTH) => {
  const ovulationDate = calculateOvulation(lastPeriodDate, cycleLength);
  
  const fertileStart = new Date(ovulationDate);
  fertileStart.setDate(ovulationDate.getDate() - 5);
  
  const fertileEnd = new Date(ovulationDate);
  fertileEnd.setDate(ovulationDate.getDate() + 1);
  
  return {
    start: fertileStart,
    end: fertileEnd,
    ovulation: ovulationDate,
  };
};

/**
 * Déterminer la phase actuelle du cycle
 */
const getCyclePhase = (lastPeriodDate, cycleLength = AVERAGE_CYCLE_LENGTH) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const lastPeriod = new Date(lastPeriodDate);
  lastPeriod.setHours(0, 0, 0, 0);
  
  const daysSinceLastPeriod = Math.floor((today - lastPeriod) / (1000 * 60 * 60 * 24));
  const dayOfCycle = (daysSinceLastPeriod % cycleLength) + 1;
  
  // Phases du cycle
  if (dayOfCycle <= AVERAGE_PERIOD_LENGTH) {
    return {
      name: 'Règles',
      description: 'Votre corps élimine la muqueuse utérine. Il est normal de se sentir fatiguée.',
      tips: [
        'Reposez-vous suffisamment',
        'Mangez des aliments riches en fer',
        'Faites de l\'exercice léger',
        'Utilisez des bouillottes pour soulager les crampes',
      ],
      icon: 'droplet',
      color: '#FF4FA3',
    };
  } else if (dayOfCycle <= 13) {
    return {
      name: 'Phase folliculaire',
      description: 'Vos niveaux d\'œstrogène augmentent. Vous pouvez vous sentir plus énergique.',
      tips: [
        'Profitez de votre énergie pour faire du sport',
        'C\'est un bon moment pour les projets créatifs',
        'Mangez des aliments riches en vitamines',
        'Hydratez-vous bien',
      ],
      icon: 'flower',
      color: '#FF8A3D',
    };
  } else if (dayOfCycle <= 15) {
    return {
      name: 'Ovulation',
      description: 'Votre période la plus fertile ! Un ovule est libéré.',
      tips: [
        'Si vous voulez tomber enceinte, c\'est le moment idéal',
        'Votre libido peut être plus élevée',
        'Vous pouvez remarquer une glaire cervicale claire',
        'Certaines femmes ressentent une légère douleur',
      ],
      icon: 'heart',
      color: '#E91E63',
    };
  } else {
    return {
      name: 'Phase lutéale',
      description: 'Votre corps se prépare pour les prochaines règles. Le SPM peut apparaître.',
      tips: [
        'Faites attention à votre alimentation',
        'Réduisez la caféine et le sel',
        'Pratiquez la relaxation et le yoga',
        'Dormez suffisamment',
      ],
      icon: 'moon',
      color: '#2D7CFF',
    };
  }
};

/**
 * Calculer tous les cycles futurs pour une année
 */
const calculateYearCycles = (lastPeriodDate, cycleLength = AVERAGE_CYCLE_LENGTH) => {
  const cycles = [];
  const startDate = new Date(lastPeriodDate);
  
  for (let i = 0; i < 12; i++) {
    const cycleStart = new Date(startDate);
    cycleStart.setDate(startDate.getDate() + (i * cycleLength));
    
    const ovulation = calculateOvulation(cycleStart, cycleLength);
    const nextPeriod = calculateNextPeriod(cycleStart, cycleLength);
    const fertileWindow = calculateFertileWindow(cycleStart, cycleLength);
    
    cycles.push({
      number: i + 1,
      start: cycleStart,
      ovulation: ovulation,
      nextPeriod: nextPeriod,
      fertileWindow: fertileWindow,
    });
  }
  
  return cycles;
};

/**
 * Informations éducatives sur le cycle menstruel
 */
export const cycleEducation = {
  phases: [
    {
      name: 'Menstruations',
      duration: '3-7 jours',
      description: 'Élimination de la muqueuse utérine. Les niveaux d\'hormones sont bas.',
      whatHappens: [
        'La muqueuse utérine se détache',
        'Les niveaux d\'œstrogène et de progestérone sont bas',
        'Le corps commence à préparer un nouveau cycle',
      ],
      symptoms: [
        'Saignements vaginaux',
        'Crampes abdominales',
        'Fatigue',
        'Maux de tête',
        'Sensibilité des seins',
      ],
      tips: [
        'Reposez-vous',
        'Appliquez de la chaleur sur le ventre',
        'Mangez des aliments riches en fer',
        'Faites de l\'exercice léger',
      ],
    },
    {
      name: 'Phase folliculaire',
      duration: '7-10 jours',
      description: 'Préparation d\'un ovule pour l\'ovulation. Les niveaux d\'œstrogène augmentent.',
      whatHappens: [
        'Le cerveau libère de la FSH (hormone folliculo-stimulante)',
        'Les follicules ovariens se développent',
        'La muqueuse utérine s\'épaissit',
        'Les niveaux d\'œstrogène augmentent',
      ],
      symptoms: [
        'Plus d\'énergie',
        'Meilleure humeur',
        'Peau plus claire',
        'Libido qui augmente',
      ],
      tips: [
        'Profitez de votre énergie',
        'Faites du sport intensif',
        'Travaillez sur vos projets importants',
      ],
    },
    {
      name: 'Ovulation',
      duration: '12-24 heures',
      description: 'Libération d\'un ovule par l\'ovaire. Période la plus fertile.',
      whatHappens: [
        'Pic de LH (hormone lutéinisante)',
        'Libération d\'un ovule mature',
        'La glaire cervicale devient claire et élastique',
        'La température basale augmente légèrement',
      ],
      symptoms: [
        'Glaire cervicale transparente (blanc d\'œuf)',
        'Légère douleur d\'un côté du bas-ventre',
        'Libido augmentée',
        'Seins sensibles',
      ],
      tips: [
        'Moment idéal pour concevoir',
        'Observez votre glaire cervicale',
        'Notez vos symptômes',
      ],
    },
    {
      name: 'Phase lutéale',
      duration: '10-14 jours',
      description: 'Préparation de l\'utérus pour une éventuelle grossesse.',
      whatHappens: [
        'Le follicule se transforme en corps jaune',
        'Production de progestérone',
        'La muqueuse utérine continue de s\'épaissir',
        'Si pas de fécondation, le corps jaune dégénère',
      ],
      symptoms: [
        'Syndrome prémenstruel (SPM)',
        'Ballonnements',
        'Sensibilité des seins',
        'Changements d\'humeur',
        'Envies alimentaires',
      ],
      tips: [
        'Réduisez le sel et la caféine',
        'Faites du yoga ou de la méditation',
        'Dormez suffisamment',
        'Mangez des aliments riches en magnésium',
      ],
    },
  ],
  
  faq: [
    {
      question: 'Quelle est la durée normale d\'un cycle ?',
      answer: 'Un cycle normal dure entre 21 et 35 jours, avec une moyenne de 28 jours. La régularité est plus importante que la durée exacte.',
    },
    {
      question: 'Quand suis-je la plus fertile ?',
      answer: 'Vous êtes la plus fertile pendant les 5 jours avant l\'ovulation et le jour de l\'ovulation elle-même. L\'ovulation se produit généralement 14 jours avant les prochaines règles.',
    },
    {
      question: 'Comment savoir si j\'ovule ?',
      answer: 'Signes d\'ovulation : glaire cervicale transparente et élastique, légère augmentation de la température basale, douleur d\'un côté du bas-ventre, libido augmentée.',
    },
    {
      question: 'Pourquoi mon cycle est-il irrégulier ?',
      answer: 'Le stress, les changements de poids, l\'exercice intensif, les voyages, et certaines conditions médicales peuvent affecter la régularité du cycle.',
    },
    {
      question: 'Quand consulter un médecin ?',
      answer: 'Consultez si : cycles très irréguliers, règles très douloureuses, saignements abondants, absence de règles pendant 3 mois (sans grossesse), ou si vous essayez de concevoir depuis 1 an sans succès.',
    },
  ],
};

/**
 * Export du service complet
 */
export const cycleService = {
  calculateOvulation,
  calculateNextPeriod,
  calculateFertileWindow,
  getCyclePhase,
  calculateYearCycles,
  cycleEducation,
  AVERAGE_CYCLE_LENGTH,
  AVERAGE_PERIOD_LENGTH,
};

export default cycleService;