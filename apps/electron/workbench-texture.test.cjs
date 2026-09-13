const assert = require("node:assert/strict");
const test = require("node:test");

const { resolveTextureAnimatorComponent } = require("./workbench-texture.cjs");

const assets = {
  candidates: [
    { value: "T006_base_obj", asset_file: "CAB-main", component_index: 1 }
  ],
  texture_candidates: [
    { value: "T006_base_diffuse1", asset_file: "CAB-main", component_index: 394 }
  ]
};

test("texture replacement opens the MainData animator instead of the Texture2D component", () => {
  const result = resolveTextureAnimatorComponent(assets, {
    textureName: "T006_base_diffuse1",
    mainData: "T006_base_obj"
  });

  assert.equal(result.matchingTexture.component_index, 394);
  assert.equal(result.mainDataCandidate.component_index, 1);
  assert.equal(result.componentIndex, 1);
});

test("texture replacement matches normalized names and supports an explicit animator component", () => {
  const result = resolveTextureAnimatorComponent(assets, {
    textureName: " T006_BASE_DIFFUSE1 ",
    mainData: "T006_BASE_OBJ",
    componentIndex: 7
  });

  assert.equal(result.matchingTexture.value, "T006_base_diffuse1");
  assert.equal(result.componentIndex, 7);
});

test("missing textures do not accidentally reuse a Texture2D component index", () => {
  const result = resolveTextureAnimatorComponent(assets, {
    textureName: "missing_texture",
    mainData: "T006_base_obj"
  });

  assert.equal(result.matchingTexture, null);
  assert.equal(result.componentIndex, 1);
});
