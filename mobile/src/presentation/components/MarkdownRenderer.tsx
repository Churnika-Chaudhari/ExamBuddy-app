import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/core/theme';

interface MarkdownRendererProps {
  content: string;
}

type Block =
  | { type: 'h1'; text: string }
  | { type: 'h2'; text: string }
  | { type: 'h3'; text: string }
  | { type: 'h4'; text: string }
  | { type: 'bullet'; text: string }
  | { type: 'code'; lines: string[] }
  | { type: 'paragraph'; text: string };

const CONTROL_CHARS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u200b-\u200d\ufeff]/g;
const DIAGRAM_LINE = /^[\s|+_\-=*/\\<>^v.~`#─━│┌┐└┘├┤┬┴┼╔╗╚╝→←↑↓⇒⇐]+$/;
const TABLE_SEPARATOR = /^\s*\|?[\s:|-]+\|[\s:|-]*$/;
const ARROWS_RIGHT = /[→⇒⟶➡]/g;
const ARROWS_LEFT = /[←⇐⟵]/g;
const BOX_CHARS = /[─━│┌┐└┘├┤┬┴┼╔╗╚╝█▀▄▌▐░▒▓↑↓↕↔]/g;

/**
 * Strip noise so only clean, important content is shown: removes control/
 * zero-width chars, markdown tables, ASCII diagrams, code fences, backticks
 * and stray special characters the simple renderer can't display.
 */
function sanitizeContent(raw: string): string {
  if (!raw) return '';
  const text = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(CONTROL_CHARS, '');
  const out: string[] = [];

  for (const original of text.split('\n')) {
    let line = original.replace(/\s+$/, '');
    let stripped = line.trim();

    if (stripped.startsWith('```') || stripped.startsWith('~~~')) continue;
    if (stripped.includes('-') && TABLE_SEPARATOR.test(stripped)) continue;

    if (stripped.startsWith('|') && (stripped.match(/\|/g)?.length ?? 0) >= 2) {
      const cells = stripped
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map((c) => c.trim())
        .filter(Boolean);
      line = cells.length ? `- ${cells.join(' — ')}` : '';
      stripped = line.trim();
      if (!stripped) continue;
    }

    if (stripped.length >= 3 && DIAGRAM_LINE.test(stripped)) continue;

    line = line
      .replace(/`+/g, '')
      .replace(ARROWS_RIGHT, '->')
      .replace(ARROWS_LEFT, '<-')
      .replace(BOX_CHARS, '')
      .replace(/\|/g, ' ')
      .replace(/[ \t]{2,}/g, ' ')
      .replace(/\s+$/, '');
    out.push(line);
  }

  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

function parseMarkdown(content: string): Block[] {
  const blocks: Block[] = [];
  const lines = sanitizeContent(content).split('\n');
  let i = 0;
  let inCode = false;
  let codeLines: string[] = [];

  const flushCode = () => {
    if (codeLines.length) {
      blocks.push({ type: 'code', lines: [...codeLines] });
      codeLines = [];
    }
  };

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trimEnd();

    if (line.trim().startsWith('```')) {
      if (inCode) {
        inCode = false;
        flushCode();
      } else {
        flushCode();
        inCode = true;
      }
      i += 1;
      continue;
    }

    if (inCode) {
      codeLines.push(raw);
      i += 1;
      continue;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith('# ')) {
      flushCode();
      blocks.push({ type: 'h1', text: trimmed.slice(2) });
    } else if (trimmed.startsWith('## ')) {
      flushCode();
      blocks.push({ type: 'h2', text: trimmed.slice(3) });
    } else if (trimmed.startsWith('### ')) {
      flushCode();
      blocks.push({ type: 'h3', text: trimmed.slice(4) });
    } else if (trimmed.startsWith('#### ')) {
      flushCode();
      blocks.push({ type: 'h4', text: trimmed.slice(5) });
    } else if (/^[-*•]\s+/.test(trimmed)) {
      blocks.push({ type: 'bullet', text: trimmed.replace(/^[-*•]\s+/, '') });
    } else {
      blocks.push({ type: 'paragraph', text: trimmed });
    }
    i += 1;
  }

  flushCode();
  return blocks;
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <Text key={idx} style={styles.bold}>
          {part.slice(2, -2)}
        </Text>
      );
    }
    // Render *italic* / _italic_, then drop any stray emphasis markers left over.
    const italic = part.split(/(\*[^*]+\*|_[^_]+_)/g);
    return (
      <Text key={idx}>
        {italic.map((seg, j) => {
          if (
            (seg.startsWith('*') && seg.endsWith('*') && seg.length > 2) ||
            (seg.startsWith('_') && seg.endsWith('_') && seg.length > 2)
          ) {
            return (
              <Text key={j} style={styles.italic}>
                {seg.slice(1, -1)}
              </Text>
            );
          }
          return <Text key={j}>{seg.replace(/[*_`]/g, '')}</Text>;
        })}
      </Text>
    );
  });
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const blocks = parseMarkdown(content);

  return (
    <View style={styles.container}>
      {blocks.map((block, index) => {
        switch (block.type) {
          case 'h1':
            return (
              <Text key={index} style={styles.h1}>
                {block.text}
              </Text>
            );
          case 'h2':
            return (
              <Text key={index} style={styles.h2}>
                {block.text}
              </Text>
            );
          case 'h3':
            return (
              <Text key={index} style={styles.h3}>
                {block.text}
              </Text>
            );
          case 'h4':
            return (
              <Text key={index} style={styles.h4}>
                {block.text}
              </Text>
            );
          case 'code':
            return (
              <View key={index} style={styles.codeBlock}>
                {block.lines.map((line, li) => (
                  <Text key={li} style={styles.codeText}>
                    {line || ' '}
                  </Text>
                ))}
              </View>
            );
          case 'bullet':
            return (
              <View key={index} style={styles.bulletRow}>
                <Text style={styles.bulletDot}>•</Text>
                <Text style={styles.bulletText}>{renderInline(block.text)}</Text>
              </View>
            );
          default:
            return (
              <Text key={index} style={styles.paragraph}>
                {renderInline(block.text)}
              </Text>
            );
        }
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs,
  },
  h1: {
    ...typography.h2,
    color: colors.text,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  h2: {
    ...typography.h3,
    color: colors.primaryDark,
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  h3: {
    ...typography.label,
    color: colors.text,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  h4: {
    ...typography.bodySmall,
    fontWeight: '700',
    color: colors.text,
    marginTop: spacing.xs,
  },
  paragraph: {
    ...typography.bodySmall,
    color: colors.text,
    lineHeight: 24,
    marginBottom: spacing.xs,
  },
  bold: {
    fontWeight: '700',
    color: colors.text,
  },
  italic: {
    fontStyle: 'italic',
    color: colors.text,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.xs,
    paddingLeft: spacing.xs,
  },
  bulletDot: {
    ...typography.bodySmall,
    color: colors.primary,
    width: 16,
    lineHeight: 24,
  },
  bulletText: {
    ...typography.bodySmall,
    color: colors.text,
    flex: 1,
    lineHeight: 24,
  },
  codeBlock: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: spacing.sm,
    marginVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  codeText: {
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: 18,
    color: colors.text,
  },
});
