import { Dimensions, PixelRatio, ScaledSize } from 'react-native';

// Base design dimensions (iPhone X / common 375pt-wide reference).
const GUIDELINE_BASE_WIDTH = 375;
const GUIDELINE_BASE_HEIGHT = 812;

function compute(window: ScaledSize) {
  const shortDimension = Math.min(window.width, window.height);
  const longDimension = Math.max(window.width, window.height);

  // Linear scale relative to the reference width, clamped so phones never get
  // absurdly tiny or oversized text/spacing.
  const widthRatio = clamp(shortDimension / GUIDELINE_BASE_WIDTH, 0.85, 1.3);
  const heightRatio = clamp(longDimension / GUIDELINE_BASE_HEIGHT, 0.85, 1.3);

  return {
    width: window.width,
    height: window.height,
    shortDimension,
    longDimension,
    widthRatio,
    heightRatio,
    isSmall: shortDimension < 360,
    isLarge: shortDimension >= 414,
    isTablet: shortDimension >= 600,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

let metrics = compute(Dimensions.get('window'));

// Keep metrics fresh if the device rotates / window resizes (foldables, tablets).
Dimensions.addEventListener('change', ({ window }) => {
  metrics = compute(window);
});

/** Scale a size proportionally to the screen width (clamped). */
export function scale(size: number): number {
  return Math.round(size * metrics.widthRatio);
}

/** Scale a size proportionally to the screen height (clamped). */
export function verticalScale(size: number): number {
  return Math.round(size * metrics.heightRatio);
}

/**
 * Scale with a dampening factor so values change gently between devices.
 * factor 0 = no scaling, 1 = full width scaling.
 */
export function moderateScale(size: number, factor = 0.5): number {
  return Math.round(size + (size * metrics.widthRatio - size) * factor);
}

/** Font-size aware scaling, snapped to the nearest device pixel. */
export function fontScale(size: number): number {
  const scaled = size + (size * metrics.widthRatio - size) * 0.4;
  return Math.round(PixelRatio.roundToNearestPixel(scaled));
}

export function getScreen() {
  return metrics;
}
