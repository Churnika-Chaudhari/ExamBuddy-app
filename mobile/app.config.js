const appJson = require('./app.json');

/** @type {import('expo/config').ExpoConfig} */
module.exports = {
  ...appJson.expo,
  extra: {
    ...appJson.expo.extra,
    apiUrl:
      process.env.EXPO_PUBLIC_API_URL?.trim() ||
      appJson.expo.extra?.apiUrl ||
      'http://localhost:8000/api/v1',
    apiForce: process.env.EXPO_PUBLIC_API_FORCE === 'true',
  },
};
