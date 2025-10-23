<template>
  <v-snackbar
    v-model="toast.state.value.show"
    :color="toast.state.value.color"
    :timeout="toast.state.value.timeout"
    location="top right"
    elevation="8"
    class="toast-notification"
  >
    <div class="d-flex align-center">
      <v-icon v-if="toast.state.value.icon" size="small" class="mr-2">
        {{ toast.state.value.icon }}
      </v-icon>
      <span>{{ toast.state.value.message }}</span>
    </div>

    <template #actions>
      <v-btn
        variant="text"
        size="small"
        @click="toast.hide()"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup>
import { useToast } from '~/composables/useToast'

const toast = useToast()
</script>

<style scoped>
.toast-notification {
  font-weight: 500;
}
</style>
