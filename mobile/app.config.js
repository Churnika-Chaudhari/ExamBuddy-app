/** @type {import('expo/config').ExpoConfig} */
module.exports = ({ config }) => {
  const configuredApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim() ?? '';
  const isEasProduction = process.env.EAS_BUILD_PROFILE === 'production';

  if (isEasProduction && !configuredApiUrl.startsWith('https://')) {
    throw new Error(
      'Production EAS builds require EXPO_PUBLIC_API_URL to be an https:// URL. ' +
        'Example: https://YOUR-RENDER-BACKEND.onrender.com/api/v1. ' +
        'Set it in the EAS production environment before building.'
    );
  }

  config.extra = {
    ...(config.extra ?? {}),
    ...(configuredApiUrl ? { apiUrl: configuredApiUrl } : {}),
    apiForce: process.env.EXPO_PUBLIC_API_FORCE === 'true',
  };

  return config;
};
