function normalizeUnityName(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/[\u0000-\u001f\u007f\u009f\u200b-\u200d\u2060\ufeff]/g, "")
    .trim()
    .toLocaleLowerCase();
}

function findUnityCandidate(candidates, value) {
  const normalized = normalizeUnityName(value);
  if (!normalized || !Array.isArray(candidates)) return null;
  return candidates.find((candidate) => (
    normalizeUnityName(typeof candidate === "string" ? candidate : candidate?.value || "") === normalized
  )) || null;
}

function resolveTextureAnimatorComponent(assets, { textureName = "", mainData = "", componentIndex } = {}) {
  const matchingTexture = findUnityCandidate(assets?.texture_candidates, textureName);
  const mainDataCandidates = Array.isArray(assets?.candidates) ? assets.candidates : [];
  const preferredAssetFile = String(matchingTexture?.asset_file || "");
  const namedMainData = findUnityCandidate(mainDataCandidates, mainData);
  const mainDataCandidate = (
    namedMainData
    && (!preferredAssetFile || String(namedMainData.asset_file || "") === preferredAssetFile)
  )
    ? namedMainData
    : mainDataCandidates.find((candidate) => (
      !preferredAssetFile || String(candidate?.asset_file || "") === preferredAssetFile
    )) || namedMainData || mainDataCandidates[0];
  const requestedComponentIndex = Number(componentIndex);
  const resolvedComponentIndex = Number.isInteger(requestedComponentIndex) && requestedComponentIndex >= 0
    ? requestedComponentIndex
    : Number(mainDataCandidate?.component_index);
  return {
    matchingTexture,
    mainDataCandidate,
    componentIndex: resolvedComponentIndex
  };
}

module.exports = {
  findUnityCandidate,
  normalizeUnityName,
  resolveTextureAnimatorComponent
};
