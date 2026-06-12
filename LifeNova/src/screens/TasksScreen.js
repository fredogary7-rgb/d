/**
 * Écran Tâches - Gestion professionnelle des objectifs
 * Interface moderne avec catégories, priorités et statistiques
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  TextInput,
  FlatList,
  Animated,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, theme } from '../constants';
import { taskStorage } from '../services';
import { SafeContainer } from '../components';

// Catégories de tâches
const CATEGORIES = [
  { id: 'all', name: 'Toutes', icon: 'grid', color: colors.text.secondary },
  { id: 'work', name: 'Travail', icon: 'briefcase', color: '#3B82F6' },
  { id: 'personal', name: 'Personnel', icon: 'person', color: '#10B981' },
  { id: 'health', name: 'Santé', icon: 'heart', color: '#EF4444' },
  { id: 'learning', name: 'Apprentissage', icon: 'book', color: '#8B5CF6' },
  { id: 'finance', name: 'Finance', icon: 'wallet', color: '#F59E0B' },
];

// Priorités
const PRIORITIES = [
  { id: 'high', name: 'Urgent', color: '#EF4444' },
  { id: 'medium', name: 'Important', color: '#F59E0B' },
  { id: 'low', name: 'Normal', color: '#10B981' },
];

const TasksScreen = () => {
  const [tasks, setTasks] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('medium');
  const [selectedTaskCategory, setSelectedTaskCategory] = useState('personal');
  const [searchQuery, setSearchQuery] = useState('');
  const slideAnim = useState(new Animated.Value(300))[0];

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    const savedTasks = await taskStorage.getTasks();
    setTasks(savedTasks);
  };

  const addTask = async () => {
    if (!newTaskTitle.trim()) return;

    const newTask = {
      id: Date.now().toString(),
      title: newTaskTitle.trim(),
      description: newTaskDescription.trim(),
      category: selectedTaskCategory,
      priority: selectedPriority,
      completed: false,
      createdAt: new Date().toISOString(),
      dueDate: null,
    };

    await taskStorage.saveTasks([...tasks, newTask]);
    setTasks([...tasks, newTask]);
    resetForm();
  };

  const toggleTask = async (taskId) => {
    const updatedTasks = tasks.map((task) =>
      task.id === taskId ? { ...task, completed: !task.completed } : task
    );
    await taskStorage.saveTasks(updatedTasks);
    setTasks(updatedTasks);
  };

  const deleteTask = async (taskId) => {
    const updatedTasks = tasks.filter((task) => task.id !== taskId);
    await taskStorage.saveTasks(updatedTasks);
    setTasks(updatedTasks);
  };

  const resetForm = () => {
    setNewTaskTitle('');
    setNewTaskDescription('');
    setSelectedPriority('medium');
    setSelectedTaskCategory('personal');
    setShowAddModal(false);
  };

  const getFilteredTasks = () => {
    return tasks.filter((task) => {
      const matchesCategory = selectedCategory === 'all' || task.category === selectedCategory;
      const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (task.description && task.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesCategory && matchesSearch;
    });
  };

  const getStats = () => {
    const total = tasks.length;
    const completed = tasks.filter((t) => t.completed).length;
    const pending = total - completed;
    const highPriority = tasks.filter((t) => t.priority === 'high' && !t.completed).length;
    return { total, completed, pending, highPriority };
  };

  const getCategoryColor = (categoryId) => {
    const category = CATEGORIES.find((c) => c.id === categoryId);
    return category?.color || colors.text.secondary;
  };

  const getPriorityColor = (priorityId) => {
    const priority = PRIORITIES.find((p) => p.id === priorityId);
    return priority?.color || colors.text.secondary;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
    });
  };

  const stats = getStats();
  const filteredTasks = getFilteredTasks();

  const renderTask = ({ item }) => (
    <TouchableOpacity
      style={[
        styles.taskCard,
        { borderLeftColor: getCategoryColor(item.category) },
        item.completed && styles.taskCardCompleted,
      ]}
      onPress={() => toggleTask(item.id)}
      activeOpacity={0.7}
    >
      <View style={styles.taskLeft}>
        <View
          style={[
            styles.taskCheckbox,
            item.completed && styles.taskCheckboxChecked,
            { borderColor: getCategoryColor(item.category) },
          ]}
        >
          {item.completed && (
            <Ionicons name="checkmark" size={16} color={colors.primary.white} />
          )}
        </View>
        <View style={styles.taskContent}>
          <Text
            style={[
              styles.taskTitle,
              item.completed && styles.taskTitleCompleted,
            ]}
            numberOfLines={1}
          >
            {item.title}
          </Text>
          {item.description ? (
            <Text style={styles.taskDescription} numberOfLines={2}>
              {item.description}
            </Text>
          ) : null}
          <View style={styles.taskMeta}>
            <View style={styles.taskMetaRow}>
              <View
                style={[
                  styles.priorityDot,
                  { backgroundColor: getPriorityColor(item.priority) },
                ]}
              />
              <Text style={styles.taskCategory}>
                {CATEGORIES.find((c) => c.id === item.category)?.name}
              </Text>
            </View>
            <Text style={styles.taskDate}>{formatDate(item.createdAt)}</Text>
          </View>
        </View>
      </View>
      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => deleteTask(item.id)}
      >
        <Ionicons name="trash-outline" size={18} color={colors.status.error} />
      </TouchableOpacity>
    </TouchableOpacity>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <View style={styles.emptyIconContainer}>
        <Ionicons name="clipboard-outline" size={48} color={colors.text.light} />
      </View>
      <Text style={styles.emptyTitle}>Aucune tâche</Text>
      <Text style={styles.emptySubtitle}>
        Commencez par ajouter votre premier objectif
      </Text>
      <TouchableOpacity
        style={styles.emptyButton}
        onPress={() => setShowAddModal(true)}
      >
        <Ionicons name="add" size={20} color={colors.primary.white} />
        <Text style={styles.emptyButtonText}>Créer une tâche</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeContainer backgroundColor={colors.background.primary} statusBarStyle="dark">
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Mes Objectifs</Text>
          <Text style={styles.headerSubtitle}>
            {stats.pending} en attente • {stats.completed} terminées
          </Text>
        </View>
        <TouchableOpacity
          style={styles.addButtonHeader}
          onPress={() => setShowAddModal(true)}
        >
          <Ionicons name="add" size={24} color={colors.primary.white} />
        </TouchableOpacity>
      </View>

      {/* Stats Cards */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <View style={[styles.statIconContainer, { backgroundColor: `${colors.primary.blue}15` }]}>
            <Ionicons name="flag" size={18} color={colors.primary.blue} />
          </View>
          <View>
            <Text style={styles.statValue}>{stats.total}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
        </View>
        <View style={styles.statCard}>
          <View style={[styles.statIconContainer, { backgroundColor: `${colors.primary.orange}15` }]}>
            <Ionicons name="time" size={18} color={colors.primary.orange} />
          </View>
          <View>
            <Text style={styles.statValue}>{stats.pending}</Text>
            <Text style={styles.statLabel}>À faire</Text>
          </View>
        </View>
        <View style={styles.statCard}>
          <View style={[styles.statIconContainer, { backgroundColor: `${colors.primary.rose}15` }]}>
            <Ionicons name="checkmark-circle" size={18} color={colors.primary.rose} />
          </View>
          <View>
            <Text style={styles.statValue}>{stats.completed}</Text>
            <Text style={styles.statLabel}>Fait</Text>
          </View>
        </View>
        {stats.highPriority > 0 && (
          <View style={styles.statCard}>
            <View style={[styles.statIconContainer, { backgroundColor: `${'#EF4444'}15` }]}>
              <Ionicons name="warning" size={18} color="#EF4444" />
            </View>
            <View>
              <Text style={styles.statValue}>{stats.highPriority}</Text>
              <Text style={styles.statLabel}>Urgent</Text>
            </View>
          </View>
        )}
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Ionicons name="search" size={18} color={colors.text.light} style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Rechercher une tâche..."
          placeholderTextColor={colors.text.light}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Ionicons name="close-circle" size={18} color={colors.text.light} />
          </TouchableOpacity>
        )}
      </View>

      {/* Category Tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.categoriesContainer}
      >
        {CATEGORIES.map((category) => (
          <TouchableOpacity
            key={category.id}
            style={[
              styles.categoryTab,
              selectedCategory === category.id && styles.categoryTabActive,
              { backgroundColor: selectedCategory === category.id ? `${category.color}15` : colors.background.secondary },
            ]}
            onPress={() => setSelectedCategory(category.id)}
          >
            <Ionicons
              name={category.icon}
              size={16}
              color={selectedCategory === category.id ? category.color : colors.text.light}
            />
            <Text
              style={[
                styles.categoryTabText,
                selectedCategory === category.id && { color: category.color, fontWeight: '600' },
              ]}
            >
              {category.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Tasks List */}
      <FlatList
        data={filteredTasks}
        renderItem={renderTask}
        keyExtractor={(item) => item.id}
        style={styles.tasksList}
        contentContainerStyle={
          filteredTasks.length === 0 ? styles.emptyContainer : styles.tasksContent
        }
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={renderEmptyState}
      />

      {/* Add Task Modal */}
      <Modal
        visible={showAddModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowAddModal(false)}
      >
        <View style={styles.modalOverlay}>
          <Animated.View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Nouvel objectif</Text>
              <TouchableOpacity onPress={() => setShowAddModal(false)}>
                <Ionicons name="close" size={24} color={colors.text.secondary} />
              </TouchableOpacity>
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.formLabel}>Titre *</Text>
              <TextInput
                style={styles.formInput}
                placeholder="Que voulez-vous accomplir ?"
                placeholderTextColor={colors.text.light}
                value={newTaskTitle}
                onChangeText={setNewTaskTitle}
                autoFocus
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.formLabel}>Description</Text>
              <TextInput
                style={[styles.formInput, styles.formTextarea]}
                placeholder="Détails supplémentaires (optionnel)"
                placeholderTextColor={colors.text.light}
                value={newTaskDescription}
                onChangeText={setNewTaskDescription}
                multiline
                numberOfLines={3}
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.formLabel}>Catégorie</Text>
              <View style={styles.categorySelector}>
                {CATEGORIES.filter((c) => c.id !== 'all').map((category) => (
                  <TouchableOpacity
                    key={category.id}
                    style={[
                      styles.categoryOption,
                      selectedTaskCategory === category.id && {
                        backgroundColor: `${category.color}15`,
                        borderColor: category.color,
                      },
                    ]}
                    onPress={() => setSelectedTaskCategory(category.id)}
                  >
                    <Ionicons
                      name={category.icon}
                      size={18}
                      color={selectedTaskCategory === category.id ? category.color : colors.text.light}
                    />
                    <Text
                      style={[
                        styles.categoryOptionText,
                        selectedTaskCategory === category.id && { color: category.color },
                      ]}
                    >
                      {category.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.formLabel}>Priorité</Text>
              <View style={styles.prioritySelector}>
                {PRIORITIES.map((priority) => (
                  <TouchableOpacity
                    key={priority.id}
                    style={[
                      styles.priorityOption,
                      selectedPriority === priority.id && {
                        backgroundColor: `${priority.color}15`,
                        borderColor: priority.color,
                      },
                    ]}
                    onPress={() => setSelectedPriority(priority.id)}
                  >
                    <View
                      style={[
                        styles.priorityDotLarge,
                        { backgroundColor: selectedPriority === priority.id ? priority.color : colors.text.light },
                      ]}
                    />
                    <Text
                      style={[
                        styles.priorityOptionText,
                        selectedPriority === priority.id && { color: priority.color },
                      ]}
                    >
                      {priority.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <TouchableOpacity
              style={[styles.submitButton, !newTaskTitle.trim() && styles.submitButtonDisabled]}
              onPress={addTask}
              disabled={!newTaskTitle.trim()}
            >
              <Ionicons name="checkmark-circle" size={20} color={colors.primary.white} />
              <Text style={styles.submitButtonText}>Créer l'objectif</Text>
            </TouchableOpacity>
          </Animated.View>
        </View>
      </Modal>
    </SafeContainer>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background.primary,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  headerTitle: {
    fontSize: theme.typography.sizes.xxl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  headerSubtitle: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    marginTop: theme.spacing.xs,
  },
  addButtonHeader: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary.rose,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statsContainer: {
    flexDirection: 'row',
    paddingHorizontal: theme.spacing.lg,
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    alignItems: 'center',
    ...theme.shadows.sm,
  },
  statIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  statValue: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  statLabel: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.secondary,
    marginTop: 2,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.xl,
    marginHorizontal: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    ...theme.shadows.sm,
  },
  searchIcon: {
    marginRight: theme.spacing.sm,
  },
  searchInput: {
    flex: 1,
    paddingVertical: theme.spacing.md,
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
  },
  categoriesContainer: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.sm,
    gap: theme.spacing.sm,
  },
  categoryTab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.xl,
    marginRight: theme.spacing.sm,
  },
  categoryTabActive: {
    borderWidth: 1,
  },
  categoryTabText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  tasksList: {
    flex: 1,
  },
  tasksContent: {
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.xxl,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    paddingTop: theme.spacing.xxl,
  },
  taskCard: {
    flexDirection: 'row',
    backgroundColor: colors.primary.white,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    borderLeftWidth: 4,
    ...theme.shadows.sm,
  },
  taskCardCompleted: {
    opacity: 0.6,
  },
  taskLeft: {
    flex: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
  },
  taskCheckbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  taskCheckboxChecked: {
    backgroundColor: colors.primary.rose,
    borderColor: colors.primary.rose,
  },
  taskContent: {
    flex: 1,
  },
  taskTitle: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: 2,
  },
  taskTitleCompleted: {
    textDecorationLine: 'line-through',
    color: colors.text.light,
  },
  taskDescription: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    lineHeight: 18,
    marginBottom: theme.spacing.sm,
  },
  taskMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  taskMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  priorityDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  taskCategory: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
    fontWeight: theme.typography.weights.medium,
  },
  taskDate: {
    fontSize: theme.typography.sizes.xs,
    color: colors.text.light,
  },
  deleteButton: {
    padding: theme.spacing.sm,
    justifyContent: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xxl,
    paddingHorizontal: theme.spacing.xl,
  },
  emptyIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.background.secondary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  emptyTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  emptySubtitle: {
    fontSize: theme.typography.sizes.md,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: theme.spacing.lg,
  },
  emptyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary.rose,
    borderRadius: theme.borderRadius.xl,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  emptyButtonText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.primary.white,
    borderTopLeftRadius: theme.borderRadius.xl,
    borderTopRightRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    maxHeight: '90%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  modalTitle: {
    fontSize: theme.typography.sizes.xl,
    fontWeight: theme.typography.weights.bold,
    color: colors.text.primary,
  },
  formGroup: {
    marginBottom: theme.spacing.lg,
  },
  formLabel: {
    fontSize: theme.typography.sizes.sm,
    fontWeight: theme.typography.weights.semibold,
    color: colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  formInput: {
    backgroundColor: colors.background.secondary,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
    fontSize: theme.typography.sizes.md,
    color: colors.text.primary,
  },
  formTextarea: {
    paddingTop: theme.spacing.md,
    textAlignVertical: 'top',
    minHeight: 80,
  },
  categorySelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  categoryOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: colors.background.tertiary,
    backgroundColor: colors.background.secondary,
  },
  categoryOptionText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  prioritySelector: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  priorityOption: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
    paddingVertical: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: colors.background.tertiary,
    backgroundColor: colors.background.secondary,
  },
  priorityDotLarge: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  priorityOptionText: {
    fontSize: theme.typography.sizes.sm,
    color: colors.text.secondary,
    fontWeight: theme.typography.weights.medium,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary.rose,
    borderRadius: theme.borderRadius.xl,
    paddingVertical: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  submitButtonDisabled: {
    backgroundColor: colors.background.tertiary,
  },
  submitButtonText: {
    fontSize: theme.typography.sizes.md,
    fontWeight: theme.typography.weights.semibold,
    color: colors.primary.white,
  },
});

export default TasksScreen;