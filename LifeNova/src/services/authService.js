/**
 * LifeNova Auth Service
 * Service d'authentification (mock pour le moment)
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock user data for demonstration
const MOCK_USER = {
  id: '1',
  email: 'demo@lifenova.com',
  firstName: 'Marie',
  token: 'mock-jwt-token',
};

/**
 * Login with email and password
 * In production, this would call the FastAPI backend
 */
export const login = async (email, password) => {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // For demo purposes, accept any credentials
  // In production, validate against backend
  if (email && password) {
    const user = { ...MOCK_USER, email };
    
    // Store auth data
    await AsyncStorage.setItem('user', JSON.stringify(user));
    await AsyncStorage.setItem('token', user.token);
    
    return {
      success: true,
      user,
    };
  }
  
  return {
    success: false,
    error: 'Invalid credentials',
  };
};

/**
 * Register a new user
 */
export const register = async (firstName, email, password) => {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // For demo purposes, accept any registration
  // In production, validate and create user in backend
  if (firstName && email && password) {
    const user = {
      id: Date.now().toString(),
      email,
      firstName,
      token: 'mock-jwt-token-' + Date.now(),
    };
    
    // Store auth data
    await AsyncStorage.setItem('user', JSON.stringify(user));
    await AsyncStorage.setItem('token', user.token);
    
    return {
      success: true,
      user,
    };
  }
  
  return {
    success: false,
    error: 'Registration failed',
  };
};

/**
 * Logout user
 */
export const logout = async () => {
  await AsyncStorage.removeItem('user');
  await AsyncStorage.removeItem('token');
  return { success: true };
};

/**
 * Get current user
 */
export const getCurrentUser = async () => {
  try {
    const userJson = await AsyncStorage.getItem('user');
    if (userJson) {
      return JSON.parse(userJson);
    }
    return null;
  } catch (error) {
    return null;
  }
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = async () => {
  const token = await AsyncStorage.getItem('token');
  return !!token;
};

/**
 * Refresh auth token
 */
export const refreshToken = async () => {
  // In production, call backend to refresh token
  const user = await getCurrentUser();
  if (user) {
    const newToken = 'mock-jwt-token-' + Date.now();
    await AsyncStorage.setItem('token', newToken);
    return { success: true, token: newToken };
  }
  return { success: false, error: 'Not authenticated' };
};

/**
 * Export authService
 */
export const authService = {
  login,
  register,
  logout,
  getCurrentUser,
  isAuthenticated,
  refreshToken,
};

export default authService;