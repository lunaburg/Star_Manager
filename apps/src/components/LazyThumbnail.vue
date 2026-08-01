<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { observeLazyThumbnail, unobserveLazyThumbnail } from "../lazyThumbnailObserver";

const props = defineProps({
  alt: { type: String, default: "" },
  eager: { type: Boolean, default: false },
  src: { type: String, default: "" }
});

const root = ref(null);
const visible = ref(props.eager);

function stopObserver() {
  unobserveLazyThumbnail(root.value);
}

function startObserver() {
  stopObserver();
  if (props.eager || visible.value || !props.src) {
    visible.value = props.eager || visible.value;
    return;
  }
  if (!observeLazyThumbnail(root.value, () => {
    visible.value = true;
  })) {
    visible.value = true;
  }
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
