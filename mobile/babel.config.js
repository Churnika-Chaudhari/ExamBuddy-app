module.exports = function (api) {
  api.cache.using(() =>
    [process.env.EXPO_PUBLIC_API_URL ?? '', process.env.EXPO_PUBLIC_API_FORCE ?? ''].join('|')
  );
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        'module-resolver',
        {
          root: ['./'],
          alias: {
            '@': './src',
          },
        },
      ],
    ],
  };
};
