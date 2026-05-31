<script setup lang="ts">
import { MotionConfig } from 'motion-v'
</script>

<template>
  <MotionConfig :reducedMotion="'user'">
    <v-app theme="calliopeScriptorium">
      <v-main class="calliope-app">
        <router-view />
      </v-main>
    </v-app>
  </MotionConfig>
</template>

<style scoped>
.calliope-app {
  min-height: 100vh;
  background: var(--calliope-ink);
  color: var(--calliope-paper);
  font-family: var(--calliope-font-body);
}
</style>
