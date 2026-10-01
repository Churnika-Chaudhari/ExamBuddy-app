import * as FileSystem from 'expo-file-system/legacy';

import type { DashboardData } from '@/domain/types';

const CACHE_PATH = `${FileSystem.cacheDirectory ?? ''}exambuddy_dashboard.json`;

export async function readDashboardCache(): Promise<DashboardData | null> {
  if (!FileSystem.cacheDirectory) return null;
  try {
    const info = await FileSystem.getInfoAsync(CACHE_PATH);
    if (!info.exists) return null;
    const raw = await FileSystem.readAsStringAsync(CACHE_PATH);
    const parsed = JSON.parse(raw) as { data?: DashboardData };
    if (!parsed?.data?.stats) return null;
    return parsed.data;
  } catch {
    return null;
  }
}

export async function writeDashboardCache(data: DashboardData): Promise<void> {
  if (!FileSystem.cacheDirectory) return;
  try {
    await FileSystem.writeAsStringAsync(CACHE_PATH, JSON.stringify({ data, savedAt: Date.now() }));
  } catch {
    // Cache is best-effort — never block the dashboard on a write failure.
  }
}

export async function clearDashboardCache(): Promise<void> {
  if (!FileSystem.cacheDirectory) return;
  try {
    const info = await FileSystem.getInfoAsync(CACHE_PATH);
    if (info.exists) {
      await FileSystem.deleteAsync(CACHE_PATH, { idempotent: true });
    }
  } catch {
    // Best-effort.
  }
}
