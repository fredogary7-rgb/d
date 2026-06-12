/**
 * Service de stockage local
 * Gère la persistance des données avec AsyncStorage
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Clés de stockage
const STORAGE_KEYS = {
  TASKS: '@lifenova:tasks',
  CONVERSATIONS: '@lifenova:conversations',
  MOTIVATION_DATE: '@lifenova:motivation_date',
  CYCLE_DATA: '@lifenova:cycle_data',
  CYCLES: '@lifenova:cycles',
};

/**
 * Gestion des tâches (To-Do)
 */
export const taskStorage = {
  // Récupérer toutes les tâches
  getTasks: async () => {
    try {
      const tasksJson = await AsyncStorage.getItem(STORAGE_KEYS.TASKS);
      return tasksJson ? JSON.parse(tasksJson) : [];
    } catch (error) {
      console.error('Error getting tasks:', error);
      return [];
    }
  },

  // Sauvegarder toutes les tâches
  saveTasks: async (tasks) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.TASKS, JSON.stringify(tasks));
    } catch (error) {
      console.error('Error saving tasks:', error);
    }
  },

  // Ajouter une tâche
  addTask: async (task) => {
    try {
      const tasks = await taskStorage.getTasks();
      const newTask = {
        id: Date.now().toString(),
        text: task.text,
        completed: false,
        createdAt: new Date().toISOString(),
      };
      await taskStorage.saveTasks([...tasks, newTask]);
      return newTask;
    } catch (error) {
      console.error('Error adding task:', error);
      return null;
    }
  },

  // Mettre à jour une tâche
  updateTask: async (taskId, updates) => {
    try {
      const tasks = await taskStorage.getTasks();
      const updatedTasks = tasks.map((task) =>
        task.id === taskId ? { ...task, ...updates } : task
      );
      await taskStorage.saveTasks(updatedTasks);
      return updatedTasks;
    } catch (error) {
      console.error('Error updating task:', error);
      return null;
    }
  },

  // Supprimer une tâche
  deleteTask: async (taskId) => {
    try {
      const tasks = await taskStorage.getTasks();
      const filteredTasks = tasks.filter((task) => task.id !== taskId);
      await taskStorage.saveTasks(filteredTasks);
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  },

  // Supprimer toutes les tâches
  clearTasks: async () => {
    try {
      await AsyncStorage.removeItem(STORAGE_KEYS.TASKS);
    } catch (error) {
      console.error('Error clearing tasks:', error);
    }
  },
};

/**
 * Gestion des conversations IA
 */
export const conversationStorage = {
  // Récupérer une conversation
  getConversation: async (conversationId = 'default') => {
    try {
      const key = `${STORAGE_KEYS.CONVERSATIONS}:${conversationId}`;
      const convJson = await AsyncStorage.getItem(key);
      return convJson ? JSON.parse(convJson) : [];
    } catch (error) {
      console.error('Error getting conversation:', error);
      return [];
    }
  },

  // Sauvegarder un message dans la conversation
  addMessage: async (message, conversationId = 'default') => {
    try {
      const key = `${STORAGE_KEYS.CONVERSATIONS}:${conversationId}`;
      const messages = await conversationStorage.getConversation(conversationId);
      const newMessage = {
        ...message,
        id: Date.now().toString(),
        createdAt: new Date().toISOString(),
      };
      const updatedMessages = [...messages, newMessage];
      
      // Garder seulement les 50 derniers messages
      const limitedMessages = updatedMessages.slice(-50);
      
      await AsyncStorage.setItem(key, JSON.stringify(limitedMessages));
      return newMessage;
    } catch (error) {
      console.error('Error adding message:', error);
      return null;
    }
  },

  // Effacer la conversation
  clearConversation: async (conversationId = 'default') => {
    try {
      const key = `${STORAGE_KEYS.CONVERSATIONS}:${conversationId}`;
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error('Error clearing conversation:', error);
    }
  },
};

/**
 * Gestion de la motivation quotidienne
 */
export const motivationStorage = {
  // Sauvegarder la date de la dernière motivation
  setMotivationDate: async (date) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.MOTIVATION_DATE, date);
    } catch (error) {
      console.error('Error setting motivation date:', error);
    }
  },

  // Récupérer la date de la dernière motivation
  getMotivationDate: async () => {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.MOTIVATION_DATE);
    } catch (error) {
      console.error('Error getting motivation date:', error);
      return null;
    }
  },
};

/**
 * Gestion des cycles menstruels
 */
export const cycleStorage = {
  // Sauvegarder les données du cycle
  saveCycleData: async (data) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.CYCLE_DATA, JSON.stringify(data));
    } catch (error) {
      console.error('Error saving cycle data:', error);
    }
  },

  // Récupérer les données du cycle
  getCycleData: async () => {
    try {
      const data = await AsyncStorage.getItem(STORAGE_KEYS.CYCLE_DATA);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error getting cycle data:', error);
      return null;
    }
  },

  // Ajouter un cycle à l'historique
  addCycle: async (cycle) => {
    try {
      const cycles = await cycleStorage.getCycles();
      const newCycle = {
        ...cycle,
        id: Date.now().toString(),
      };
      const updatedCycles = [newCycle, ...cycles].slice(0, 24); // Garder 24 cycles max
      await AsyncStorage.setItem(STORAGE_KEYS.CYCLES, JSON.stringify(updatedCycles));
    } catch (error) {
      console.error('Error adding cycle:', error);
    }
  },

  // Récupérer l'historique des cycles
  getCycles: async () => {
    try {
      const cycles = await AsyncStorage.getItem(STORAGE_KEYS.CYCLES);
      return cycles ? JSON.parse(cycles) : [];
    } catch (error) {
      console.error('Error getting cycles:', error);
      return [];
    }
  },
};

export default {
  taskStorage,
  conversationStorage,
  motivationStorage,
  cycleStorage,
  STORAGE_KEYS,
};
