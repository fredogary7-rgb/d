/**
 * Écran Splash LifeNova - Version Premium App Store
 * Design inspiré de Notion, Calm, Duolingo, Airbnb
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  Image,
} from 'react-native';
import { SafeContainer } from '../components';

const { width, height } = Dimensions.get('window');

const SplashScreen = ({ navigation }) => {
  // Animations
  const logoFadeAnim = useRef(new Animated.Value(0)).current;
  const logoScaleAnim = useRef(new Animated.Value(0.8)).current;
  const textFadeAnim = useRef(new Animated.Value(0)).current;
  const sloganFadeAnim = useRef(new Animated.Value(0)).current;
  const starRotateAnim = useRef(new Animated.Value(0)).current;
  const starOpacityAnim = useRef(new Animated.Value(0.6)).current;

  // Animations des points de chargement
  const dot1Scale = useRef(new Animated.Value(1)).current;
  const dot2Scale = useRef(new Animated.Value(1)).current;
  const dot3Scale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const prepareApp = async () => {
      // 1. Fade-in et scale du logo (effet premium)
      Animated.parallel([
        Animated.timing(logoFadeAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.spring(logoScaleAnim, {
          toValue: 1,
          tension: 40,
          friction: 5,
          useNativeDriver: true,
        }),
      ]).start();

      // 2. Rotation subtile de l'étoile (en continu)
      Animated.loop(
        Animated.timing(starRotateAnim, {
          toValue: 1,
          duration: 6000,
          useNativeDriver: true,
        })
      ).start();

      // 3. Scintillement de l'étoile
      Animated.loop(
        Animated.sequence([
          Animated.timing(starOpacityAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(starOpacityAnim, {
            toValue: 0.4,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Attendre avant d'afficher le texte
      await new Promise((resolve) => setTimeout(resolve, 800));

      // 4. Apparition élégante du titre LifeNova
      Animated.timing(textFadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }).start();

      await new Promise((resolve) => setTimeout(resolve, 400));

      // 5. Apparition du slogan
      Animated.timing(sloganFadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }).start();

      await new Promise((resolve) => setTimeout(resolve, 600));

      // 6. Animation des points - pulser en séquence (grossir/rétrécir)
      const animateDots = () => {
        Animated.sequence([
          // Point 1
          Animated.sequence([
            Animated.parallel([
              Animated.timing(dot1Scale, {
                toValue: 1.6,
                duration: 400,
                useNativeDriver: true,
              }),
            ]),
            Animated.timing(dot1Scale, {
              toValue: 1,
              duration: 400,
              useNativeDriver: true,
            }),
          ]),
          // Point 2
          Animated.sequence([
            Animated.timing(dot2Scale, {
              toValue: 1.6,
              duration: 400,
              useNativeDriver: true,
            }),
            Animated.timing(dot2Scale, {
              toValue: 1,
              duration: 400,
              useNativeDriver: true,
            }),
          ]),
          // Point 3
          Animated.sequence([
            Animated.timing(dot3Scale, {
              toValue: 1.6,
              duration: 400,
              useNativeDriver: true,
            }),
            Animated.timing(dot3Scale, {
              toValue: 1,
              duration: 400,
              useNativeDriver: true,
            }),
          ]),
        ]).start(() => animateDots());
      };

      animateDots();

      // Attendre avant la transition
      await new Promise((resolve) => setTimeout(resolve, 1200));

      // 7. Transition de sortie fluide
      Animated.parallel([
        Animated.timing(logoFadeAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(textFadeAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(sloganFadeAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
      ]).start(() => {
        navigation.replace('MainTabs');
      });
    };

    prepareApp();
  }, []);

  const starSpin = starRotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <SafeContainer backgroundColor="#FFFFFF" statusBarStyle="dark">
      {/* Cercle décoratif rose transparent en haut à droite (opacité 0.08) */}
      <View style={styles.decorCircle} />

      {/* Vague premium dégradée en bas (20% inférieur) */}
      <View style={styles.waveContainer}>
        <View style={styles.waveGradient} />
        <View style={styles.waveOverlay} />
      </View>

      {/* Contenu principal centré */}
      <View style={styles.content}>
        {/* Logo avec animations */}
        <Animated.View
          style={[
            styles.logoContainer,
            {
              opacity: logoFadeAnim,
              transform: [{ scale: logoScaleAnim }],
            },
          ]}
        >
          {/* Image du logo avec ombre légère */}
          <View style={styles.logoShadowContainer}>
            <Image
              source={require('../../assets/li.png')}
              style={styles.logoImage}
              resizeMode="contain"
            />
          </View>

          {/* Étoile brillante qui tourne */}
          <Animated.View
            style={[
              styles.starContainer,
              {
                transform: [{ rotate: starSpin }],
                opacity: starOpacityAnim,
              },
            ]}
          >
            <View style={styles.starInner} />
          </Animated.View>
        </Animated.View>

        {/* Titre LifeNova - Typographie élégante */}
        <Animated.View
          style={[
            styles.textContainer,
            { opacity: textFadeAnim },
          ]}
        >
          <Text style={styles.appName}>
            <Text style={styles.appNameLife}>Life</Text>
            <Text style={styles.appNameNova}>Nova</Text>
          </Text>
        </Animated.View>

        {/* Slogan - Lisibilité parfaite */}
        <Animated.View
          style={[
            styles.sloganContainer,
            { opacity: sloganFadeAnim },
          ]}
        >
          <Text style={styles.slogan}>
            Votre compagnon intelligent pour une vie meilleure
          </Text>
        </Animated.View>

        {/* Indicateur de chargement - 3 points qui pulsent */}
        <View style={styles.loaderContainer}>
          <Animated.View
            style={[
              styles.loaderDot,
              styles.dot1,
              { transform: [{ scale: dot1Scale }] },
            ]}
          />
          <Animated.View
            style={[
              styles.loaderDot,
              styles.dot2,
              { transform: [{ scale: dot2Scale }] },
            ]}
          />
          <Animated.View
            style={[
              styles.loaderDot,
              styles.dot3,
              { transform: [{ scale: dot3Scale }] },
            ]}
          />
        </View>
      </View>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },

  // Cercle décoratif rose transparent (opacité 0.08)
  decorCircle: {
    position: 'absolute',
    top: -120,
    right: -120,
    width: 350,
    height: 350,
    borderRadius: 175,
    backgroundColor: 'rgba(255, 79, 163, 0.08)',
  },

  // Vague premium en bas (20% de l'écran)
  waveContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: height * 0.2,
    overflow: 'hidden',
  },

  // Dégradé de la vague (rose → orange → violet → bleu)
  waveGradient: {
    position: 'absolute',
    bottom: -30,
    left: -50,
    right: -50,
    height: height * 0.2 + 60,
    borderRadius: 9999,
    backgroundColor: '#FFFFFF',
    shadowColor: '#FF4FA3',
    shadowOffset: { width: 0, height: -15 },
    shadowOpacity: 0.15,
    shadowRadius: 40,
    elevation: 15,
  },

  // Overlay pour effet de profondeur
  waveOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: height * 0.2,
    backgroundColor: '#FFFFFF',
  },

  // Contenu principal centré
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },

  // Conteneur du logo
  logoContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 40,
    position: 'relative',
  },

  // Ombre légère autour du logo
  logoShadowContainer: {
    width: 200,
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 100,
    backgroundColor: 'transparent',
    shadowColor: 'rgba(0, 0, 0, 0.08)',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 1,
    shadowRadius: 30,
    elevation: 8,
  },

  // Logo image (taille augmentée de 40%)
  logoImage: {
    width: 180,
    height: 180,
    borderRadius: 90,
  },

  // Étoile brillante
  starContainer: {
    position: 'absolute',
    top: -5,
    right: 5,
    width: 36,
    height: 36,
  },

  starInner: {
    width: 36,
    height: 36,
    backgroundColor: '#FF8A3D',
    borderRadius: 8,
    transform: [{ rotate: '45deg' }],
    shadowColor: '#FF8A3D',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 15,
    elevation: 8,
  },

  // Conteneur du titre
  textContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },

  // Titre LifeNova - 42px, FontWeight 800
  appName: {
    fontSize: 42,
    fontWeight: '800',
    letterSpacing: -1.5,
  },

  appNameLife: {
    color: '#1A1A2E',
  },

  appNameNova: {
    color: '#2D7CFF',
  },

  // Slogan - 18px, couleur #6B7280
  sloganContainer: {
    alignItems: 'center',
    marginBottom: 48,
    paddingHorizontal: 20,
  },

  slogan: {
    fontSize: 18,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 28,
    fontWeight: '400',
    maxWidth: 340,
  },

  // Conteneur des points de chargement
  loaderContainer: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
  },

  // Points de chargement
  loaderDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },

  dot1: {
    backgroundColor: '#FF4FA3',
  },

  dot2: {
    backgroundColor: '#FF8A3D',
  },

  dot3: {
    backgroundColor: '#2D7CFF',
  },
});

export default SplashScreen;