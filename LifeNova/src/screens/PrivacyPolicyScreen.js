/**
 * Écran Politique de Confidentialité
 * Document professionnel type App Store
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { SafeContainer } from '../components';
import { useTranslation } from '../i18n/useTranslation';

const PrivacyPolicyScreen = ({ navigation }) => {
  const { t } = useTranslation();

  const openEmail = () => {
    Linking.openURL('mailto:privacy@lifenova.com');
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Politique de Confidentialité</Text>
          <View style={styles.placeholder} />
        </View>

        {/* Date de mise à jour */}
        <View style={styles.updateInfo}>
          <Ionicons name="calendar-outline" size={16} color={colors.text.light} />
          <Text style={styles.updateText}>Dernière mise à jour : 1er Décembre 2024</Text>
        </View>

        {/* Introduction */}
        <View style={styles.section}>
          <Text style={styles.introText}>
            Bienvenue sur LifeNova. Nous sommes engagés à protéger vos données personnelles et votre vie privée. Cette politique explique comment nous collectons, utilisons et protégeons vos informations lorsque vous utilisez notre application.
          </Text>
        </View>

        {/* 1. Données collectées */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Données que nous collectons</Text>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Données que vous nous fournissez :</Text>
            <Text style={styles.bulletPoint}>• Compte utilisateur (nom, email)</Text>
            <Text style={styles.bulletPoint}>• Contenu généré (objectifs, tâches, notes)</Text>
            <Text style={styles.bulletPoint}>• Préférences et paramètres</Text>
          </View>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Données collectées automatiquement :</Text>
            <Text style={styles.bulletPoint}>• Données d'utilisation et d'analytics</Text>
            <Text style={styles.bulletPoint}>• Informations sur l'appareil</Text>
            <Text style={styles.bulletPoint}>• Identifiants publicitaires</Text>
          </View>
        </View>

        {/* 2. Utilisation des données */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>2. Comment nous utilisons vos données</Text>
          <View style={styles.card}>
            <Text style={styles.bulletPoint}>• Fournir et améliorer nos services</Text>
            <Text style={styles.bulletPoint}>• Personnaliser votre expérience</Text>
            <Text style={styles.bulletPoint}>• Envoyer des notifications et rappels</Text>
            <Text style={styles.bulletPoint}>• Analyser l'utilisation de l'application</Text>
            <Text style={styles.bulletPoint}>• Respecter nos obligations légales</Text>
          </View>
        </View>

        {/* 3. Partage des données */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3. Partage des données</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous ne vendons pas vos données personnelles. Nous pouvons partager vos informations avec :
            </Text>
            <Text style={styles.bulletPoint}>• Prestataires de services (hébergement, analytics)</Text>
            <Text style={styles.bulletPoint}>• Autorités légales si requis par la loi</Text>
            <Text style={styles.bulletPoint}>• Partenaires avec votre consentement explicite</Text>
          </View>
        </View>

        {/* 4. Sécurité */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>4. Sécurité des données</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous mettons en œuvre des mesures de sécurité techniques et organisationnelles pour protéger vos données contre tout accès non autorisé, perte ou altération. Vos données sont chiffrées en transit et au repos.
            </Text>
          </View>
        </View>

        {/* 5. Vos droits */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>5. Vos droits (RGPD)</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>Vous disposez des droits suivants :</Text>
            <Text style={styles.bulletPoint}>• Droit d'accès à vos données</Text>
            <Text style={styles.bulletPoint}>• Droit de rectification</Text>
            <Text style={styles.bulletPoint}>• Droit à l'effacement ("droit à l'oubli")</Text>
            <Text style={styles.bulletPoint}>• Droit à la limitation du traitement</Text>
            <Text style={styles.bulletPoint}>• Droit à la portabilité des données</Text>
            <Text style={styles.bulletPoint}>• Droit d'opposition</Text>
          </View>
        </View>

        {/* 6. Conservation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>6. Conservation des données</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous conservons vos données tant que votre compte est actif. Vous pouvez supprimer votre compte à tout moment depuis les paramètres, ce qui entraînera la suppression de toutes vos données sous 30 jours.
            </Text>
          </View>
        </View>

        {/* 7. Cookies */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>7. Cookies et technologies similaires</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous utilisons des cookies et technologies similaires pour améliorer votre expérience, analyser l'utilisation et personnaliser le contenu. Vous pouvez contrôler ces paramètres dans les options de votre appareil.
            </Text>
          </View>
        </View>

        {/* 8. Enfants */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>8. Protection des mineurs</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Notre application n'est pas destinée aux enfants de moins de 13 ans. Nous ne collectons pas sciemment de données personnelles auprès d'enfants de moins de 13 ans.
            </Text>
          </View>
        </View>

        {/* 9. Modifications */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>9. Modifications de la politique</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous pouvons mettre à jour cette politique de temps en temps. Nous vous notifierons des changements significatifs via l'application ou par email. L'utilisation continue de l'application après modification constitue votre acceptation.
            </Text>
          </View>
        </View>

        {/* 10. Contact */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>10. Nous contacter</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Pour toute question concernant cette politique ou pour exercer vos droits, contactez-nous :
            </Text>
            <TouchableOpacity style={styles.contactButton} onPress={openEmail}>
              <Ionicons name="mail-outline" size={18} color={colors.primary.blue} />
              <Text style={styles.contactText}>privacy@lifenova.com</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>LifeNova © 2024 - Tous droits réservés</Text>
        </View>
      </ScrollView>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background.primary,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.lg,
    paddingBottom: theme.spacing.xxl,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.lg,
  },
  backButton: {
    padding: theme.spacing.sm,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  placeholder: {
    width: 48,
  },
  updateInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xl,
    paddingVertical: theme.spacing.sm,
  },
  updateText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
  },
  section: {
    marginBottom: theme.spacing.xl,
  },
  sectionTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.md,
  },
  introText: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 24,
  },
  card: {
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    ...theme.shadows.sm,
  },
  cardTitle: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  paragraph: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 24,
    marginBottom: theme.spacing.sm,
  },
  bulletPoint: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    lineHeight: 24,
    marginLeft: theme.spacing.sm,
  },
  contactButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
    padding: theme.spacing.md,
    backgroundColor: `${colors.primary.blue}10`,
    borderRadius: theme.borderRadius.md,
    alignSelf: 'flex-start',
  },
  contactText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.medium,
    color: colors.primary.blue,
  },
  footer: {
    marginTop: theme.spacing.xl,
    paddingTop: theme.spacing.lg,
    alignItems: 'center',
  },
  footerText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.light,
  },
});

export default PrivacyPolicyScreen;