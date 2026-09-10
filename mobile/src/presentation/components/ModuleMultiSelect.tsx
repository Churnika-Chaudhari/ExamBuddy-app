import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, spacing, typography } from '@/core/theme';
import type { SubjectModule } from '@/domain/types';
import AppButton from '@/presentation/components/AppButton';
import AppCard from '@/presentation/components/AppCard';

type Props = {
  modules: SubjectModule[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  onApply: () => void;
  applying?: boolean;
  includeUnmapped: boolean;
  onIncludeUnmappedChange: (value: boolean) => void;
  error?: string | null;
};

function moduleLabel(mod: SubjectModule): string {
  return mod.display_name || mod.module_name;
}

export default function ModuleMultiSelect({
  modules,
  selectedIds,
  onChange,
  onApply,
  applying = false,
  includeUnmapped,
  onIncludeUnmappedChange,
  error,
}: Props) {
  const selectable = modules.filter((m) => !m.is_unmapped);
  const unmapped = modules.find((m) => m.is_unmapped);
  const allSelectableIds = selectable.map((m) => m.module_id);
  const selectedSet = new Set(selectedIds);
  const allSelected =
    allSelectableIds.length > 0 && allSelectableIds.every((id) => selectedSet.has(id));

  const toggle = (id: string) => {
    if (selectedSet.has(id)) {
      onChange(selectedIds.filter((x) => x !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectAll = () => {
    const ids = [...allSelectableIds];
    if (includeUnmapped && unmapped) ids.push(unmapped.module_id);
    onChange(ids);
  };

  const selectAllModules = () => {
    onIncludeUnmappedChange(true);
    const ids = [...allSelectableIds];
    if (unmapped) ids.push(unmapped.module_id);
    onChange(ids);
  };

  const clearAll = () => onChange([]);

  const renderRow = (mod: SubjectModule) => {
    const checked = selectedSet.has(mod.module_id);
    const asked = mod.asked_topic_count ?? 0;
    return (
      <Pressable
        key={mod.module_id}
        onPress={() => toggle(mod.module_id)}
        style={[styles.row, checked && styles.rowSelected]}
        accessibilityRole="checkbox"
        accessibilityState={{ checked }}
      >
        <Ionicons
          name={checked ? 'checkbox' : 'square-outline'}
          size={22}
          color={checked ? colors.primary : colors.textMuted}
        />
        <View style={styles.rowMeta}>
          <Text style={styles.rowTitle} numberOfLines={2}>
            {moduleLabel(mod)}
          </Text>
          <Text style={styles.rowHint}>
            {mod.topic_count} topic{mod.topic_count === 1 ? '' : 's'}
            {asked ? ` · ${asked} in PYQs` : ' · no PYQs yet'}
          </Text>
        </View>
      </Pressable>
    );
  };

  return (
    <AppCard style={styles.card}>
      <Text style={styles.heading}>Select Modules</Text>
      <Text style={styles.hint}>Choose one or more modules, then apply the filter.</Text>

      <View style={styles.actions}>
        <Pressable onPress={selectAllModules} style={[styles.chip, allSelected && styles.chipOn]}>
          <Text style={[styles.chipText, allSelected && styles.chipTextOn]}>All Modules</Text>
        </Pressable>
        <Pressable onPress={selectAll} style={styles.chip}>
          <Text style={styles.chipText}>Select All</Text>
        </Pressable>
        <Pressable onPress={clearAll} style={styles.chip}>
          <Text style={styles.chipText}>Clear All</Text>
        </Pressable>
      </View>

      {selectable.map(renderRow)}

      {unmapped ? (
        <View style={styles.unmappedBlock}>
      <Pressable
        onPress={() => {
          if (!unmapped) return;
          const next = !includeUnmapped;
          onIncludeUnmappedChange(next);
          if (next) {
            if (!selectedSet.has(unmapped.module_id)) {
              onChange([...selectedIds, unmapped.module_id]);
            }
          } else {
            onChange(selectedIds.filter((id) => id !== unmapped.module_id));
          }
        }}
            style={[styles.row, includeUnmapped && styles.rowSelected]}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: includeUnmapped }}
          >
            <Ionicons
              name={includeUnmapped ? 'checkbox' : 'square-outline'}
              size={22}
              color={includeUnmapped ? colors.primary : colors.textMuted}
            />
            <View style={styles.rowMeta}>
              <Text style={styles.rowTitle}>Unmapped</Text>
              <Text style={styles.rowHint}>
                PYQ topics that did not match a syllabus module
                {unmapped.asked_topic_count
                  ? ` · ${unmapped.asked_topic_count} topic${unmapped.asked_topic_count === 1 ? '' : 's'}`
                  : ''}
              </Text>
            </View>
          </Pressable>
        </View>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <AppButton
        label="Apply Filter"
        onPress={onApply}
        loading={applying}
        icon="filter"
        style={styles.applyBtn}
      />
    </AppCard>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  heading: {
    ...typography.h3,
    color: colors.text,
  },
  hint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
    marginBottom: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: radius.full,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipOn: {
    backgroundColor: colors.primaryLight,
    borderColor: colors.primary,
  },
  chipText: {
    ...typography.caption,
    color: colors.text,
    fontWeight: '600',
  },
  chipTextOn: {
    color: colors.primary,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xs,
    borderRadius: radius.md,
  },
  rowSelected: {
    backgroundColor: colors.primaryLight,
  },
  rowMeta: {
    flex: 1,
    minWidth: 0,
  },
  rowTitle: {
    ...typography.label,
    color: colors.text,
  },
  rowHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  unmappedBlock: {
    marginTop: spacing.xs,
    paddingTop: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  error: {
    ...typography.caption,
    color: colors.error,
    marginTop: spacing.xs,
    marginBottom: spacing.xs,
  },
  applyBtn: {
    marginTop: spacing.sm,
  },
});
