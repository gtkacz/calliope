<template>
  <v-app theme="calliopeDark">
    <v-main class="calliope-app">
      <router-view />
    </v-main>
  </v-app>
</template>

<style scoped>
.calliope-app {
  min-height: 100vh;
  background: var(--calliope-ink);
  color: var(--calliope-paper);
  font-family: var(--calliope-font-body);
}
</style>
