/**
 * LifeNova Login Screen
 * Page de connexion sécurisée
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { colors, theme } from '../constants';
import { SafeContainer } from '../components';
import { authService } from '../services/authService';

const LoginScreen = () => {
  const navigation = useNavigation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Erreur', 'Veuillez remplir tous les champs');
      return;
    }

    setLoading(true);
    try {
      const result = await authService.login(email, password);
      if (result.success) {
        navigation.replace('MainTabs');
      } else {
        Alert.alert('Erreur', result.error || 'Échec de la connexion');
      }
    } catch (error) {
      Alert.alert('Erreur', 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Logo */}
          <View style={styles.logoContainer}>
            <View style={styles.logo}>
              <Ionicons name="leaf" size={40} color={colors.primary.rose} />
            </View>
            <Text style={styles.appName}>LifeNova</Text>
            <Text style={styles.tagline}>Votre vie, réinventée</Text>
          </View>

          {/* Formulaire */}
          <View style={styles.formContainer}>
            <Text style={styles.title}>Bon retour ! 👋</Text>
            <Text style={styles.subtitle}>Connectez-vous pour continuer</Text>

            {/* Email */}
            <View style={styles.inputContainer}>
              <View style={styles.inputWrapper}>
                <Ionicons name="mail-outline" size={20} color={colors.text.light} />
                <TextInput
                  style={styles.input}
                  placeholder="Email"
                  placeholderTextColor={colors.text.light}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  autoComplete="email"
                />
              </View>
            </View>

            {/* Mot de passe */}
            <View style={styles.inputContainer}>
              <View style={styles.inputWrapper}>
                <Ionicons name="lock-closed-outline" size={20} color={colors.text.light} />
                <TextInput
                  style={styles.input}
                  placeholder="Mot de passe"
                  placeholderTextColor={colors.text.light}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoComplete="password"
                />
                <TouchableOpacity
                  style={styles.eyeButton}
                  onPress={() => setShowPassword(!showPassword)}
                >
                  <Ionicons
                    name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                    size={20}
                    color={colors.text.light}
                  />
                </TouchableOpacity>
              </View>
            </View>

            {/* Mot de passe oublié */}
            <TouchableOpacity
              style={styles.forgotPassword}
              onPress={() => Alert.alert('Bientôt', 'La fonctionnalité de réinitialisation de mot de passe sera disponible bientôt.')}
            >
              <Text style={styles.forgotPasswordText}>Mot de passe oublié ?</Text>
            </TouchableOpacity>

            {/* Bouton de connexion */}
            <TouchableOpacity
              style={[styles.loginButton, loading && styles.loginButtonDisabled]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={colors.primary.white} />
              ) : (
                <Text style={styles.loginButtonText}>Se connecter</Text>
              )}
            </TouchableOpacity>

            {/* Séparateur */}
            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>ou</Text>
              <View style={styles.dividerLine} />
            </View>

            {/* Bouton inscription */}
            <TouchableOpacity
              style={styles.signupButton}
              onPress={() => Alert.alert('Bientôt', 'La création de compte sera disponible bientôt. Pour l\'instant, utilisez n\'importe quel email et mot de passe pour vous connecter.')}
            >
              <Ionicons name="person-add-outline" size={20} color={colors.primary.rose} />
              <Text style={styles.signupButtonText}>Créer un compte</Text>
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>
              En vous connectant, vous acceptez nos{' '}
              <Text
                style={styles.linkText}
                onPress={() => navigation.navigate('Terms')}
              >
                Conditions d'utilisation
              </Text>
              {' '}et{' '}
              <Text
                style={styles.linkText}
                onPress={() => navigation.navigate('Privacy')}
              >
                Politique de confidentialité
              </Text>
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  keyboardView: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: theme.spacing.xl,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: theme.spacing.xxl,
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: `${colors.primary.rose}15`,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  appName: {
    fontSize: theme.typography.sizes.xxl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  tagline: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    marginTop: theme.spacing.xs,
  },
  formContainer: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.xl,
    ...theme.shadows.md,
  },
  title: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    marginBottom: theme.spacing.xl,
  },
  inputContainer: {
    marginBottom: theme.spacing.md,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: theme.spacing.md,
    height: 50,
  },
  input: {
    flex: 1,
    marginLeft: theme.spacing.sm,
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
  },
  eyeButton: {
    padding: theme.spacing.xs,
  },
  forgotPassword: {
    alignSelf: 'flex-end',
    marginBottom: theme.spacing.xl,
  },
  forgotPasswordText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.primary.blue,
    fontWeight: theme.typography.weights.medium,
  },
  loginButton: {
    backgroundColor: colors.primary.rose,
    borderRadius: theme.borderRadius.md,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonText: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: theme.spacing.xl,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.background.tertiary,
  },
  dividerText: {
    marginHorizontal: theme.spacing.md,
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
  },
  signupButton: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: `${colors.primary.rose}10`,
    borderRadius: theme.borderRadius.md,
    height: 50,
    gap: theme.spacing.sm,
  },
  signupButtonText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.rose,
  },
  footer: {
    marginTop: theme.spacing.xl,
    paddingHorizontal: theme.spacing.md,
  },
  footerText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
    textAlign: 'center',
    lineHeight: 20,
  },
  linkText: {
    color: colors.primary.blue,
    fontWeight: theme.typography.weights.medium,
    textDecorationLine: 'underline',
  },
});

export default LoginScreen;