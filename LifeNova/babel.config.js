module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      // react-native-reanimated doit être en dernier dans la liste des plugins
      'react-native-reanimated/plugin',
    ],
  };
};