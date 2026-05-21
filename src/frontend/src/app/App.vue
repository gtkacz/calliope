<template>
  <v-app>
    <v-main class="calliope-app">
      <router-view />
    </v-main>
  </v-app>
</template>

<style scoped>
.calliope-app {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
}
</style>
