const noop = async () => undefined;

const AsyncStorage = {
  getItem: async () => null,
  setItem: async () => undefined,
  removeItem: noop,
  clear: noop,
  getAllKeys: async () => [],
  multiGet: async () => [],
  multiSet: async () => undefined,
  multiRemove: async () => undefined,
};

export default AsyncStorage;
export { AsyncStorage };

