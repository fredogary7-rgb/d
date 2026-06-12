/**
 * Configuration de l'API
 * Prépare la structure pour le backend futur
 * 
 * NOTE: Les variables d'environnement sont chargées depuis .env
 */

// Configuration de base
const API_CONFIG = {
  // URL de base de l'API (à partir de .env)
  baseUrl: process.env.API_BASE_URL || 'https://api.lifenova.com',
  
  // Timeout des requêtes (en ms)
  timeout: 30000,
  
  // Version de l'API
  version: 'v1',
};

// Endpoints de l'API (structure future)
export const API_ENDPOINTS = {
  // Authentification
  auth: {
    login: '/auth/login',
    register: '/auth/register',
    logout: '/auth/logout',
    refreshToken: '/auth/refresh',
  },
  
  // Utilisateurs
  users: {
    profile: '/users/profile',
    update: '/users/update',
    delete: '/users/delete',
  },
  
  // Objectifs
  goals: {
    list: '/goals',
    create: '/goals',
    update: '/goals/:id',
    delete: '/goals/:id',
    complete: '/goals/:id/complete',
  },
  
  // Statistiques
  stats: {
    overview: '/stats/overview',
    progress: '/stats/progress',
    achievements: '/stats/achievements',
  },
};

// Headers par défaut
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

export default API_CONFIG;