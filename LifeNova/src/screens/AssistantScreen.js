/**
 * Écran Assistant IA
 * Chat interface style ChatGPT avec historique de conversation
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  FlatList,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { aiService, conversationStorage } from '../services';
import { SafeContainer } from '../components';

const AssistantScreen = () => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Charger l'historique au démarrage
  useEffect(() => {
    loadConversation();
  }, []);

  const loadConversation = async () => {
    const savedMessages = await conversationStorage.getConversation();
    if (savedMessages.length > 0) {
      setMessages(savedMessages);
    } else {
      // Message de bienvenue par défaut
      const welcomeMessage = {
        _id: 'welcome',
        text: "Bonjour ! 👋 Je suis votre assistant LifeNova. Je suis là pour vous aider à organiser votre vie, définir vos objectifs et rester motivé. Comment puis-je vous aider aujourd'hui ?",
        user: { _id: 2 },
        createdAt: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = {
      _id: Date.now().toString(),
      text: inputText.trim(),
      user: { _id: 1 },
      createdAt: new Date(),
    };

    // Ajouter le message utilisateur
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    await conversationStorage.addMessage(userMessage);
    setInputText('');
    setIsLoading(true);

    try {
      // Obtenir la réponse de l'IA
      const responseText = await aiService.sendMessage(userMessage.text);

      const aiMessage = {
        _id: (Date.now() + 1).toString(),
        text: responseText,
        user: { _id: 2 },
        createdAt: new Date(),
      };

      const finalMessages = [...updatedMessages, aiMessage];
      setMessages(finalMessages);
      await conversationStorage.addMessage(aiMessage);
    } catch (error) {
      console.error('Error getting AI response:', error);
      const errorMessage = {
        _id: (Date.now() + 1).toString(),
        text: "Désolé, j'ai rencontré un problème. Veuillez réessayer dans un instant.",
        user: { _id: 2 },
        createdAt: new Date(),
      };
      setMessages([...updatedMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearConversation = async () => {
    await conversationStorage.clearConversation();
    const welcomeMessage = {
      _id: 'welcome-new',
      text: "Conversation réinitialisée. 🔄 Comment puis-je vous aider ?",
      user: { _id: 2 },
      createdAt: new Date(),
    };
    setMessages([welcomeMessage]);
  };

  const renderMessage = ({ item }) => {
    const isUser = item.user._id === 1;

    return (
      <View
        style={[
          styles.messageContainer,
          isUser ? styles.userMessageContainer : styles.aiMessageContainer,
        ]}
      >
        <View
          style={[
            styles.messageBubble,
            isUser ? styles.userBubble : styles.aiBubble,
          ]}
        >
          <Text
            style={[
              styles.messageText,
              isUser ? styles.userMessageText : styles.aiMessageText,
            ]}
          >
            {item.text}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Ionicons name="sparkles" size={20} color={colors.primary.white} />
            </View>
            <View>
              <Text style={styles.headerTitle}>Assistant IA</Text>
              <Text style={styles.headerSubtitle}>Toujours là pour vous aider</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.clearButton} onPress={clearConversation}>
            <Ionicons name="trash-outline" size={20} color={colors.text.light} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Messages List */}
      <FlatList
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item._id}
        style={styles.messagesList}
        contentContainerStyle={styles.messagesContent}
        showsVerticalScrollIndicator={false}
        onContentSizeChange={() => {}}
      />

      {/* Input Area */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <View style={styles.inputContainer}>
          {/* Quick suggestions */}
          <View style={styles.suggestionsContainer}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.suggestionsContent}
            >
              {['Motivation', 'Productivité', 'Organisation'].map((suggestion) => (
                <TouchableOpacity
                  key={suggestion}
                  style={styles.suggestionChip}
                  onPress={() => setInputText(`Donne-moi des conseils sur la ${suggestion.toLowerCase()}`)}
                >
                  <Text style={styles.suggestionText}>{suggestion}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder="Posez-moi une question..."
              placeholderTextColor={colors.text.light}
              value={inputText}
              onChangeText={setInputText}
              multiline
              maxLength={500}
            />
            <TouchableOpacity
              style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
              onPress={sendMessage}
              disabled={!inputText.trim() || isLoading}
            >
              {isLoading ? (
                <ActivityIndicator size="small" color={colors.primary.white} />
              ) : (
                <Ionicons name="send" size={20} color={colors.primary.white} />
              )}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background.primary,
  },
  header: {
    backgroundColor: colors.primary.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.background.tertiary,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  avatarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.sm,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.lg,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
  },
  headerSubtitle: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
  },
  clearButton: {
    padding: theme.spacing.sm,
  },
  messagesList: {
    flex: 1,
  },
  messagesContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
  },
  messageContainer: {
    marginBottom: theme.spacing.md,
    maxWidth: '85%',
  },
  userMessageContainer: {
    alignSelf: 'flex-end',
    alignItems: 'flex-end',
  },
  aiMessageContainer: {
    alignSelf: 'flex-start',
    alignItems: 'flex-start',
  },
  messageBubble: {
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
  },
  userBubble: {
    backgroundColor: colors.primary.rose,
    borderBottomRightRadius: theme.borderRadius.sm,
  },
  aiBubble: {
    backgroundColor: colors.background.secondary,
    borderBottomLeftRadius: theme.borderRadius.sm,
  },
  messageText: {
    fontSize: theme.typography.sizes.md,
    lineHeight: 22,
  },
  userMessageText: {
    color: colors.primary.white,
  },
  aiMessageText: {
    color: colors.text.primary,
  },
  inputContainer: {
    backgroundColor: colors.primary.white,
    borderTopWidth: 1,
    borderTopColor: colors.background.tertiary,
    paddingBottom: Platform.OS === 'ios' ? theme.spacing.md : 0,
  },
  suggestionsContainer: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  suggestionsContent: {
    flexDirection: 'row',
  },
  suggestionChip: {
    backgroundColor: colors.background.secondary,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
    marginRight: theme.spacing.sm,
    borderWidth: 1,
    borderColor: colors.background.tertiary,
  },
  suggestionText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.primary.rose,
    fontWeight: theme.typography.weights.medium,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    gap: theme.spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.xl,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: Platform.OS === 'ios' ? theme.spacing.md : theme.spacing.sm,
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
    minHeight: 44,
    maxHeight: 100,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: colors.background.tertiary,
  },
});

export default AssistantScreen;
