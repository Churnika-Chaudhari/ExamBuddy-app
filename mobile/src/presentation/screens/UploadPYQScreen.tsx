import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text, Chip, SegmentedButtons, TextInput } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { MAX_PYQ_FILES } from '@/core/constants/upload';
import { colors, radius, spacing, typography } from '@/core/theme';
import { verticalScale } from '@/core/theme/responsive';
import { getErrorMessage } from '@/data/api/client';
import type { RootStackParamList } from '@/navigation/types';
import AppButton from '@/presentation/components/AppButton';
import LoadingOverlay from '@/presentation/components/LoadingOverlay';
import ScreenWrapper from '@/presentation/components/ScreenWrapper';
import { documentsApi } from '@/data/api/endpoints';
import type { PickedFile } from '@/store/documentStore';
import { useDocumentStore } from '@/store/documentStore';
import { useAnalysisStore } from '@/store/analysisStore';
import { useUIStore } from '@/store/uiStore';
import { mergeFiles, pickMultiplePdfs } from '@/utils/pickDocuments';

type Nav = NativeStackNavigationProp<RootStackParamList, 'UploadPYQ'>;

type DocCategory = 'pyq' | 'notes';

const CATEGORY_COPY: Record<DocCategory, { heading: string; desc: string; noun: string }> = {
  pyq: {
    heading: 'Upload PYQ Papers',
    desc: 'Select previous-year question papers to analyze and extract topics.',
    noun: 'paper',
  },
  notes: {
    heading: 'Upload Notes',
    desc: 'Add your notes PDFs. They appear in the Notes tab and are used as the top-priority source for AI study notes.',
    noun: 'notes PDF',
  },
};

function isPdf(file: PickedFile): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith('.pdf') || file.mimeType === 'application/pdf';
}

function buildTitle(files: PickedFile[], category: DocCategory): string {
  if (files.length === 1) {
    return files[0].name.replace(/\.[^/.]+$/, '');
  }
  const labels: Record<DocCategory, string> = {
    pyq: 'PYQ Set',
    notes: 'Notes Set',
  };
  return `${labels[category]} (${files.length} files)`;
}

export default function UploadPYQScreen() {
  const navigation = useNavigation<Nav>();
  const { uploadDocuments, isUploading, uploadProgress } = useDocumentStore();
  const { createAnalysis, pollAnalysis } = useAnalysisStore();
  const showSnackbar = useUIStore((s) => s.showSnackbar);

  const [files, setFiles] = useState<PickedFile[]>([]);
  const [category, setCategory] = useState<DocCategory>('pyq');
  const [subject, setSubject] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const atLimit = files.length >= MAX_PYQ_FILES;
  const copy = CATEGORY_COPY[category];

  const applyPickedFiles = (incoming: PickedFile[]) => {
    const pdfs = incoming.filter(isPdf);
    if (!pdfs.length) {
      showSnackbar('Please select PDF files only', 'error');
      return;
    }
    if (pdfs.length < incoming.length) {
      showSnackbar('Non-PDF files were skipped', 'error');
    }

    const { files: merged, skipped } = mergeFiles(files, pdfs);
    setFiles(merged);

    if (skipped > 0) {
      showSnackbar(`File limit reached. ${skipped} file(s) skipped.`, 'error');
    } else {
      showSnackbar(`Selected ${pdfs.length} PDF${pdfs.length > 1 ? 's' : ''}`, 'success');
    }
  };

  const handleSelectPdfs = async () => {
    if (atLimit) {
      showSnackbar('Maximum files reached', 'error');
      return;
    }
    applyPickedFiles(await pickMultiplePdfs());
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAllFiles = () => {
    setFiles([]);
  };

  const handleUploadAndAnalyze = async () => {
    if (!files.length) {
      showSnackbar('Please select at least one PDF', 'error');
      return;
    }

    const trimmedSubject = subject.trim();

    try {
      const docs = await uploadDocuments(files, {
        category,
        subject: trimmedSubject || undefined,
      });

      // Notes are RAG source material — upload only.
      if (category !== 'pyq') {
        showSnackbar(
          `Uploaded ${docs.length} ${copy.noun}${docs.length > 1 ? 's' : ''}. View them in the Notes tab.`,
          'success'
        );
        navigation.replace('Main', { screen: 'Notes' });
        return;
      }

      const title = buildTitle(files, category);
      showSnackbar(
        `Uploaded ${docs.length} PDF${docs.length > 1 ? 's' : ''}. Processing...`,
        'success'
      );

      setIsAnalyzing(true);
      setStatusMessage('Waiting for text extraction...');
      await waitForDocuments(docs.map((d) => d.id));

      setStatusMessage('Running analysis...');
      const analysis = await createAnalysis(
        docs.map((d) => d.id),
        trimmedSubject || undefined,
        title
      );
      const completed = await pollAnalysis(analysis.id);
      setIsAnalyzing(false);
      setStatusMessage(null);

      if (completed.status === 'completed') {
        navigation.replace('AnalysisResult', { analysisId: completed.id });
      } else {
        showSnackbar(completed.error_message ?? 'Analysis failed', 'error');
      }
    } catch (err) {
      setIsAnalyzing(false);
      setStatusMessage(null);
      showSnackbar(getErrorMessage(err), 'error');
    }
  };

  const waitForDocument = async (id: string): Promise<void> => {
    const poll = async (): Promise<void> => {
      const { data } = await documentsApi.getStatus(id);
      if (data.data.status === 'processing' || data.data.status === 'uploading') {
        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      }
      if (data.data.status === 'failed') {
        throw new Error(data.data.error_message ?? 'Document processing failed');
      }
    };
    return poll();
  };

  const waitForDocuments = async (ids: string[]): Promise<void> => {
    let done = 0;
    await Promise.all(
      ids.map(async (id) => {
        await waitForDocument(id);
        done += 1;
        setStatusMessage(`Processing ${done}/${ids.length}...`);
      })
    );
  };

  const overlayMessage =
    uploadProgress ??
    statusMessage ??
    (isUploading ? 'Uploading...' : isAnalyzing ? 'Analyzing...' : '');

  return (
    <ScreenWrapper scrollable={false}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
      <LoadingOverlay visible={isUploading || isAnalyzing} message={overlayMessage} />

      <Text style={styles.heading}>{copy.heading}</Text>
      <Text style={styles.desc}>{copy.desc}</Text>

      <SegmentedButtons
        value={category}
        onValueChange={(v) => setCategory(v as DocCategory)}
        density="medium"
        style={styles.segmented}
        buttons={[
          { value: 'pyq', label: 'PYQ', icon: 'file-document-outline' },
          { value: 'notes', label: 'Notes', icon: 'note-text-outline' },
        ]}
      />

      <TextInput
        mode="outlined"
        label="Subject (optional)"
        placeholder="e.g. DBMS, Computer Networks"
        value={subject}
        onChangeText={setSubject}
        style={styles.subjectInput}
        left={<TextInput.Icon icon="bookmark-outline" />}
      />
      <Text style={styles.subjectHint}>
        Helps group this with the right subject so notes pull from every related PDF.
      </Text>

      <AppButton
        label="Select Multiple PDFs"
        onPress={handleSelectPdfs}
        icon="file-multiple"
        disabled={atLimit || isUploading || isAnalyzing}
        style={styles.selectBtn}
      />

      {files.length > 0 && (
        <>
          {files.length < MAX_PYQ_FILES && (
            <AppButton
              label="Select More PDFs"
              onPress={handleSelectPdfs}
              mode="outlined"
              icon="file-multiple"
              disabled={isUploading || isAnalyzing}
              style={styles.selectMoreBtn}
            />
          )}

          <AppButton
            label="Clear All"
            onPress={clearAllFiles}
            mode="outlined"
            icon="delete-outline"
            disabled={isUploading || isAnalyzing}
            style={styles.clearBtn}
          />

          <ScrollView style={styles.fileList} nestedScrollEnabled>
            {files.map((file, index) => (
              <View key={`${file.uri}-${index}`} style={styles.fileRow}>
                <Ionicons name="document-text-outline" size={18} color={colors.primary} />
                <Text style={styles.fileRowName} numberOfLines={1}>
                  {file.name}
                </Text>
                <Chip compact onPress={() => removeFile(index)} style={styles.removeChip}>
                  Remove
                </Chip>
              </View>
            ))}
          </ScrollView>
        </>
      )}

      <AppButton
        label={
          category === 'pyq'
            ? files.length > 1
              ? `Upload & Analyze (${files.length})`
              : 'Upload & Analyze'
            : files.length > 1
              ? `Upload (${files.length})`
              : 'Upload'
        }
        onPress={handleUploadAndAnalyze}
        loading={isUploading || isAnalyzing}
        disabled={!files.length}
        icon="upload"
        style={styles.button}
      />
      </ScrollView>
    </ScreenWrapper>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    flexGrow: 1,
    paddingBottom: spacing.xl,
  },
  heading: {
    ...typography.h2,
    color: colors.text,
    marginBottom: spacing.sm,
  },
  desc: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  segmented: {
    marginBottom: spacing.md,
  },
  subjectInput: {
    marginBottom: spacing.xs,
    backgroundColor: colors.background,
  },
  subjectHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  selectBtn: {
    marginBottom: spacing.md,
  },
  selectMoreBtn: {
    marginBottom: spacing.sm,
  },
  clearBtn: {
    marginBottom: spacing.md,
  },
  fileList: {
    maxHeight: verticalScale(240),
    marginBottom: spacing.md,
  },
  fileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    marginBottom: spacing.xs,
  },
  fileRowName: {
    ...typography.caption,
    color: colors.text,
    flex: 1,
  },
  removeChip: {
    backgroundColor: colors.errorLight,
  },
  button: {
    marginTop: spacing.sm,
    marginBottom: spacing.xl,
  },
});
