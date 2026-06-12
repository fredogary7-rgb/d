/**
 * Navigateur principal de l'application LifeNova
 * Architecture: Splash -> Tab Navigator (Home, Assistant, Tasks, Motivation, Cycle)
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { NavigationContainer } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import {
  SplashScreen,
  HomeScreen,
  AssistantScreen,
  TasksScreen,
  MotivationScreen,
  CycleScreen,
  ProgressScreen,
  SettingsScreen,
  LoginScreen,
  PrivacyPolicyScreen,
  TermsOfServiceScreen,
} from '../screens';
import { colors } from '../constants';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

/**
 * Navigateur par onglets principal
 * Contient les 5 écrans principaux de l'application
 */
const MainTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Accueil') {
            iconName = focused ? 'home' : 'home-outline';
          } else if (route.name === 'Assistant') {
            iconName = focused ? 'sparkles' : 'sparkles-outline';
          } else if (route.name === 'Tâches') {
            iconName = focused ? 'checkbox' : 'checkbox-outline';
          } else if (route.name === 'Motivation') {
            iconName = focused ? 'heart' : 'heart-outline';
          } else if (route.name === 'Cycle') {
            iconName = focused ? 'flower' : 'flower-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: colors.primary.rose,
        tabBarInactiveTintColor: colors.text.light,
        tabBarStyle: {
          backgroundColor: colors.primary.white,
          borderTopWidth: 1,
          borderTopColor: colors.background.tertiary,
          paddingTop: 8,
          paddingBottom: 8,
          height: 65,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
      })}
    >
      <Tab.Screen
        name="Accueil"
        component={HomeScreen}
        options={{
          tabBarLabel: 'Accueil',
        }}
      />
      <Tab.Screen
        name="Assistant"
        component={AssistantScreen}
        options={{
          tabBarLabel: 'Assistant',
        }}
      />
      <Tab.Screen
        name="Tâches"
        component={TasksScreen}
        options={{
          tabBarLabel: 'Tâches',
        }}
      />
      <Tab.Screen
        name="Motivation"
        component={MotivationScreen}
        options={{
          tabBarLabel: 'Motivation',
        }}
      />
      <Tab.Screen
        name="Cycle"
        component={CycleScreen}
        options={{
          tabBarLabel: 'Cycle',
        }}
      />
    </Tab.Navigator>
  );
};

/**
 * Navigateur principal avec Stack
 * Splash -> MainTabs -> Progress (accessible depuis Motivation)
 */
const AppNavigator = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Splash"
        screenOptions={{
          headerShown: false,
        }}
      >
        <Stack.Screen
          name="Splash"
          component={SplashScreen}
          options={{
            animation: 'fade',
          }}
        />
        <Stack.Screen
          name="MainTabs"
          component={MainTabs}
          options={{
            animation: 'slide_from_bottom',
            gestureEnabled: false,
          }}
        />
        <Stack.Screen
          name="Progress"
          component={ProgressScreen}
          options={{
            animation: 'slide_from_bottom',
            headerShown: true,
            title: 'Mes Progrès',
            headerStyle: {
              backgroundColor: colors.primary.white,
            },
            headerTintColor: colors.text.primary,
            headerTitleStyle: {
              fontWeight: 'bold',
            },
          }}
        />
        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{
            animation: 'slide_from_bottom',
            headerShown: true,
            title: 'Paramètres',
            headerStyle: {
              backgroundColor: colors.primary.white,
            },
            headerTintColor: colors.text.primary,
            headerTitleStyle: {
              fontWeight: 'bold',
            },
          }}
        />
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{
            animation: 'slide_from_bottom',
            headerShown: false,
          }}
        />
        <Stack.Screen
          name="Privacy"
          component={PrivacyPolicyScreen}
          options={{
            animation: 'slide_from_bottom',
            headerShown: true,
            title: 'Politique de confidentialité',
            headerStyle: {
              backgroundColor: colors.primary.white,
            },
            headerTintColor: colors.text.primary,
            headerTitleStyle: {
              fontWeight: 'bold',
            },
          }}
        />
        <Stack.Screen
          name="Terms"
          component={TermsOfServiceScreen}
          options={{
            animation: 'slide_from_bottom',
            headerShown: true,
            title: 'Conditions d\'utilisation',
            headerStyle: {
              backgroundColor: colors.primary.white,
            },
            headerTintColor: colors.text.primary,
            headerTitleStyle: {
              fontWeight: 'bold',
            },
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;