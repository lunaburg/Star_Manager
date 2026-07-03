<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  alt: { type: String, default: "" },
  eager: { type: Boolean, default: false },
  src: { type: String, default: "" }
});

const root = ref(null);
const visible = ref(props.eager);
let observer = null;

function stopObserver() {
  if (!observer) return;
  observer.disconnect();
  observer = null;
}

function startObserver() {
  stopObserver();
  if (props.eager || visible.value || !props.src) {
    visible.value = props.eager || visible.value;
    return;
  }
  if (!("IntersectionObserver" in window)) {
    visible.value = true;
    return;
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        visible.value = true;
        stopObserver();
      }
    },
    { root: null, rootMargin: "180px", threshold: 0.01 }
  );
  if (root.value) observer.observe(root.value);
}

onMounted(startObserver);
onBeforeUnmount(stopObserver);

watch(
  () => props.src,
  () => {
    visible.value = props.eager;
    startObserver();
  }
);
</script>

<template>
  <span ref="root" class="lazy-thumbnail" :class="{ pending: src && !visible }">
    <img v-if="src && visible" :src="src" :alt="alt" loading="lazy" decoding="async">
    <span v-else class="lazy-thumbnail-placeholder" aria-hidden="true">
      <slot>IMG</slot>
    </span>
  </span>
</template>
