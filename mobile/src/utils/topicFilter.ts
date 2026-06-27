/** Exam instruction/boilerplate words that are not subject topics */
const EXAM_STOPWORDS = new Set([
  'explain', 'define', 'describe', 'write', 'discuss', 'prove', 'state', 'list',
  'draw', 'illustrate', 'compare', 'differentiate', 'distinguish', 'enumerate',
  'briefly', 'short', 'note', 'notes', 'question', 'questions', 'answer',
  'marks', 'mark', 'section', 'paper', 'attempt', 'total', 'following',
  'suitable', 'scheme', 'information', 'technology', 'involved', 'process',
  'advantages', 'disadvantages', 'features', 'applications', 'introduction',
  'functions', 'importance', 'uses', 'mention',
  'example', 'examples', 'diagram', 'given', 'below', 'above', 'university',
  'examination', 'semester', 'course', 'student', 'students', 'subject',
  'year', 'instructions', 'compulsory', 'optional', 'theory', 'practical',
  'choose', 'select', 'correct', 'option', 'options', 'solve', 'calculate',
  'show', 'consider', 'using', 'help', 'terms', 'what', 'when', 'where',
  'which', 'how', 'why', 'does', 'have', 'been', 'were', 'will', 'would',
  'could', 'should', 'the', 'and', 'for', 'with', 'from', 'that', 'this',
  'they', 'their', 'there', 'also', 'only', 'more', 'most', 'some', 'any',
  'all', 'each', 'other', 'between', 'four', 'five', 'first', 'second',
  'third', 'one', 'two', 'three', 'a', 'an',
]);

export function isValidTopic(topic: string): boolean {
  const phrase = topic.trim();
  if (!phrase || phrase.length < 3) return false;

  const lower = phrase.toLowerCase();
  const words = lower.split(/\s+/);

  if (words.every((w) => EXAM_STOPWORDS.has(w))) return false;
  if (EXAM_STOPWORDS.has(lower)) return false;

  if (words.length === 1) {
    const word = words[0];
    if (EXAM_STOPWORDS.has(word)) return false;
    if (/^\d+$/.test(word)) return false;
    if (word === word.toUpperCase() && word.length >= 2) return true;
    if (word.length < 5) return false;
  }

  const substantive = words.filter((w) => !EXAM_STOPWORDS.has(w) && w.length >= 3);
  return substantive.length > 0;
}

export function filterTopics(topics: string[]): string[] {
  const seen = new Set<string>();
  return topics.filter((topic) => {
    const key = topic.trim().toLowerCase();
    if (!key || seen.has(key) || !isValidTopic(topic)) return false;
    seen.add(key);
    return true;
  });
}
