/**
 * Écran Conditions d'Utilisation
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

const TermsOfServiceScreen = ({ navigation }) => {
  const openEmail = () => {
    Linking.openURL('mailto:legal@lifenova.com');
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
          <Text style={styles.headerTitle}>Conditions d'Utilisation</Text>
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
            Bienvenue sur LifeNova. En téléchargeant, en accédant ou en utilisant notre application, vous acceptez d'être lié par ces conditions d'utilisation. Veuillez les lire attentivement.
          </Text>
        </View>

        {/* 1. Acceptation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Acceptation des conditions</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              En utilisant LifeNova, vous acceptez ces Conditions d'Utilisation et notre Politique de Confidentialité. Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser notre application.
            </Text>
          </View>
        </View>

        {/* 2. Description du service */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>2. Description du service</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              LifeNova est une application de développement personnel qui vous aide à :
            </Text>
            <Text style={styles.bulletPoint}>• Définir et suivre vos objectifs personnels</Text>
            <Text style={styles.bulletPoint}>• Gérer vos tâches quotidiennes</Text>
            <Text style={styles.bulletPoint}>• Recevoir de la motivation et des conseils</Text>
            <Text style={styles.bulletPoint}>• Suivre votre progression avec des statistiques</Text>
            <Text style={styles.bulletPoint}>• Interagir avec un assistant IA</Text>
          </View>
        </View>

        {/* 3. Compte utilisateur */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3. Compte utilisateur</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Pour accéder à certaines fonctionnalités, vous devez créer un compte. Vous vous engagez à :
            </Text>
            <Text style={styles.bulletPoint}>• Fournir des informations exactes et complètes</Text>
            <Text style={styles.bulletPoint}>• Maintenir la sécurité de vos identifiants</Text>
            <Text style={styles.bulletPoint}>• Ne pas créer plusieurs comptes frauduleux</Text>
            <Text style={styles.bulletPoint}>• Nous informer immédiatement de tout accès non autorisé</Text>
          </View>
        </View>

        {/* 4. Règles d'utilisation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>4. Règles d'utilisation</Text>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Vous ne devez pas :</Text>
            <Text style={styles.bulletPoint}>• Utiliser l'application à des fins illégales</Text>
            <Text style={styles.bulletPoint}>• Tenter d'accéder aux systèmes techniques de manière non autorisée</Text>
            <Text style={styles.bulletPoint}>• Distribuer des virus ou code malveillant</Text>
            <Text style={styles.bulletPoint}>• Harceler, intimider ou nuire à autrui</Text>
            <Text style={styles.bulletPoint}>• Contourner les mesures de sécurité</Text>
            <Text style={styles.bulletPoint}>• Utiliser des bots, scrapers ou outils automatisés</Text>
          </View>
        </View>

        {/* 5. Contenu généré */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>5. Contenu généré par l'utilisateur</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Vous conservez la propriété de votre content. En l'utilisant, vous nous accordez une licence mondiale, non exclusive et gratuite pour stocker et traiter vos données afin de fournir le service.
            </Text>
          </View>
        </View>

        {/* 6. Propriété intellectuelle */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>6. Propriété intellectuelle</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              LifeNova et son contenu (logo, design, code, textes) sont protégés par les droits d'auteur et marques déposées. Vous ne pouvez pas reproduire, distribuer ou créer des œuvres dérivées sans notre autorisation écrite.
            </Text>
          </View>
        </View>

        {/* 7. Abonnements et paiements */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>7. Abonnements et paiements</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Certaines fonctionnalités peuvent nécessiter un abonnement payant. Les conditions spécifiques seront présentées avant tout achat. Les abonnements se renouvellent automatiquement sauf résiliation.
            </Text>
            <Text style={styles.bulletPoint}>• Prix affichés en devise locale</Text>
            <Text style={styles.bulletPoint}>• Annulation possible à tout moment</Text>
            <Text style={styles.bulletPoint}>• Remboursements selon les lois locales</Text>
          </View>
        </View>

        {/* 8. Disponibilité */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>8. Disponibilité du service</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous nous efforçons de maintenir LifeNova disponible 24h/24 et 7j/7, mais nous ne garantissons pas un accès ininterrompu. Nous pouvons suspendre l'accès pour maintenance ou raisons techniques.
            </Text>
          </View>
        </View>

        {/* 9. Responsabilité */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>9. Limitation de responsabilité</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              LifeNova est fourni "tel quel". Nous ne sommes pas responsables des dommages indirects, incidents ou consécutifs. Notre responsabilité totale est limitée au montant payé pour le service au cours des 12 derniers mois.
            </Text>
          </View>
        </View>

        {/* 10. Résiliation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>10. Résiliation</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous pouvons suspendre ou résilier votre compte en cas de violation de ces conditions. Vous pouvez fermer votre compte à tout moment depuis les paramètres.
            </Text>
          </View>
        </View>

        {/* 11. Modifications */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>11. Modifications des conditions</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Nous pouvons modifier ces conditions. Nous vous notifierons des changements importants. L'utilisation continue après modification constitue votre acceptation.
            </Text>
          </View>
        </View>

        {/* 12. Loi applicable */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>12. Loi applicable</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Ces conditions sont régies par le droit français. Tout litige sera soumis aux tribunaux compétents de Paris, sauf dispositions légales contraires dans votre pays de résidence.
            </Text>
          </View>
        </View>

        {/* 13. Contact */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>13. Nous contacter</Text>
          <View style={styles.card}>
            <Text style={styles.paragraph}>
              Pour toute question concernant ces conditions, contactez-nous :
            </Text>
            <TouchableOpacity style={styles.contactButton} onPress={openEmail}>
              <Ionicons name="mail-outline" size={18} color={colors.primary.blue} />
              <Text style={styles.contactText}>legal@lifenova.com</Text>
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

export default TermsOfServiceScreen;