module.exports = function (api) {
  api.cache(true)
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        'module-resolver',
        {
          extensions: ['.ios.tsx', '.android.tsx', '.web.tsx', '.tsx', '.ts', '.jsx', '.js'],
          alias: {
            '@': './src',
            '@modules': './modules',
          },
        },
      ],
    ],
  }
}
