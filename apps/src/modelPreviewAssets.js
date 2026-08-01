const mannequinTemplatePromises = new Map();

async function loadMannequinTemplate(url) {
  if (!mannequinTemplatePromises.has(url)) {
    const templatePromise = import("three/examples/jsm/loaders/FBXLoader.js")
      .then(({ FBXLoader }) => new FBXLoader().loadAsync(url))
      .catch((error) => {
        mannequinTemplatePromises.delete(url);
        throw error;
      });
    mannequinTemplatePromises.set(url, templatePromise);
  }
  return mannequinTemplatePromises.get(url);
}

export async function cloneMannequinModel(url) {
  const [template, { clone }] = await Promise.all([
    loadMannequinTemplate(url),
    import("three/examples/jsm/utils/SkeletonUtils.js"),
  ]);
  return clone(template);
}
