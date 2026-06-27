import * as DocumentPicker from 'expo-document-picker';

import { MAX_PYQ_FILES } from '@/core/constants/upload';
import type { PickedFile } from '@/store/documentStore';

export function dedupeFiles(files: PickedFile[]): PickedFile[] {
  const seen = new Set<string>();
  return files.filter((file) => {
    const key = `${file.name.toLowerCase()}::${file.uri}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function toPickedFile(asset: DocumentPicker.DocumentPickerAsset): PickedFile {
  return {
    uri: asset.uri,
    name: asset.name,
    mimeType: asset.mimeType,
  };
}

/** Pick one PDF — works reliably on all Android file managers. */
export async function pickSinglePdf(): Promise<PickedFile[]> {
  const result = await DocumentPicker.getDocumentAsync({
    type: 'application/pdf',
    copyToCacheDirectory: true,
    multiple: false,
  });

  if (result.canceled || !result.assets?.[0]) return [];
  return [toPickedFile(result.assets[0])];
}

/** Pick multiple PDFs — may return one file on some Android devices. */
export async function pickMultiplePdfs(): Promise<PickedFile[]> {
  const result = await DocumentPicker.getDocumentAsync({
    type: 'application/pdf',
    copyToCacheDirectory: true,
    multiple: true,
  });

  if (result.canceled || !result.assets?.length) return [];
  return result.assets.map(toPickedFile);
}

export function mergeFiles(
  existing: PickedFile[],
  incoming: PickedFile[],
  maxFiles = MAX_PYQ_FILES
): { files: PickedFile[]; skipped: number } {
  const merged = dedupeFiles([...existing, ...incoming]);
  if (merged.length <= maxFiles) {
    return { files: merged, skipped: 0 };
  }
  return { files: merged.slice(0, maxFiles), skipped: merged.length - maxFiles };
}
