<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import lottie from "lottie-web";
import defaultAnimationData from "../assets/model-preview-loading.json";

const props = defineProps({
  animationData: { type: Object, default: () => defaultAnimationData },
});

const host = ref(null);
let animationInstance;

onMounted(() => {
  if (!host.value) return;
  animationInstance = lottie.loadAnimation({
    container: host.value,
    renderer: "svg",
    loop: true,
    autoplay: true,
    animationData: props.animationData,
    rendererSettings: {
      progressiveLoad: true,
      preserveAspectRatio: "xMidYMid meet",
    },
  });
});

onBeforeUnmount(() => {
  animationInstance?.destroy();
  animationInstance = null;
});
</script>

<template>
  <div ref="host" class="loading-animation" aria-hidden="true"></div>
</template>
