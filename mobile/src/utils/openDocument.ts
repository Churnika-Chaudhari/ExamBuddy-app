import { Alert, Linking } from 'react-native';

import type { Document } from '@/domain/types';

export function canOpenDocument(doc: Document): boolean {
  return doc.status === 'ready' && Boolean(doc.file_url?.trim());
}

export async function openDocumentPdf(doc: Document): Promise<boolean> {
  if (doc.status === 'processing' || doc.status === 'uploading') {
    Alert.alert('Processing', 'This document is still being processed. Try again in a moment.');
    return false;
  }

  if (doc.status === 'failed') {
    Alert.alert('Upload failed', doc.error_message ?? 'This document could not be processed.');
    return false;
  }

  const url = doc.file_url?.trim();
  if (!url) {
    Alert.alert('Unavailable', 'No PDF file is available for this document.');
    return false;
  }

  try {
    const supported = await Linking.canOpenURL(url);
    if (!supported) {
      Alert.alert('Cannot open PDF', 'Your device cannot open this file type.');
      return false;
    }
    await Linking.openURL(url);
    return true;
  } catch {
    Alert.alert('Could not open PDF', 'Please try again or check your internet connection.');
    return false;
  }
}
