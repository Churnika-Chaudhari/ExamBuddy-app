import type { SubjectModule, SubjectTopic } from '@/domain/types';

export function topicLabel(t: SubjectTopic): string {
  return (t.topic_name || t.topic || '').trim();
}

export function occurrenceOf(t: SubjectTopic): number {
  return t.occurrence_count ?? t.frequency ?? 0;
}

export function paperCountOf(t: SubjectTopic): number {
  return t.paper_count ?? 0;
}

export function topicPriority(t: SubjectTopic): 'High' | 'Medium' | 'Low' | null {
  const occ = occurrenceOf(t);
  if (occ <= 0) return null;
  const raw = (t.priority || t.importance || '').toString();
  if (/high/i.test(raw)) return 'High';
  if (/medium/i.test(raw)) return 'Medium';
  if (/low/i.test(raw)) return 'Low';
  if (occ >= 3) return 'High';
  if (occ === 2) return 'Medium';
  return 'Low';
}

export function topicStatus(t: SubjectTopic): {
  label: string;
  kind: 'frequent' | 'repeated' | 'once' | 'syllabus' | 'no_pyq';
} {
  const occ = occurrenceOf(t);
  const priority = topicPriority(t);
  if (occ >= 3 || (priority === 'High' && occ >= 2)) {
    return { label: 'Frequently Asked', kind: 'frequent' };
  }
  if (occ >= 2) {
    return { label: 'Repeated', kind: 'repeated' };
  }
  if (occ === 1) {
    return { label: 'Asked Once', kind: 'once' };
  }
  if (t.from_syllabus) {
    return { label: 'Available from Syllabus', kind: 'syllabus' };
  }
  return { label: 'No PYQ Data', kind: 'no_pyq' };
}

export function normalizeTopicKey(topic: string): string {
  return topic
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s\-/+]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function topicHasCachedNotes(t: SubjectTopic, cachedKeys: Set<string>): boolean {
  const label = topicLabel(t);
  const key = normalizeTopicKey(label);
  if (cachedKeys.has(key) || cachedKeys.has(label.toLowerCase().trim())) return true;
  if (t.topic_id && cachedKeys.has(t.topic_id.toLowerCase())) return true;
  return false;
}

export function isRealSyllabusModule(mod: SubjectModule): boolean {
  return !mod.is_fallback && !mod.is_unmapped;
}

export function partitionTopics(topics: SubjectTopic[]): {
  frequent: SubjectTopic[];
  repeated: SubjectTopic[];
  once: SubjectTopic[];
  syllabus: SubjectTopic[];
  analyzed: SubjectTopic[];
  hasRepeated: boolean;
  hasAnalyzed: boolean;
} {
  const frequent: SubjectTopic[] = [];
  const repeated: SubjectTopic[] = [];
  const once: SubjectTopic[] = [];
  const syllabus: SubjectTopic[] = [];
  const analyzed: SubjectTopic[] = [];

  for (const t of topics) {
    const kind = topicStatus(t).kind;
    if (kind === 'frequent') frequent.push(t);
    else if (kind === 'repeated') repeated.push(t);
    else if (kind === 'once') once.push(t);
    else syllabus.push(t);
    if (occurrenceOf(t) > 0) analyzed.push(t);
  }

  return {
    frequent,
    repeated,
    once,
    syllabus,
    analyzed,
    hasRepeated: frequent.length + repeated.length > 0,
    hasAnalyzed: analyzed.length > 0,
  };
}
