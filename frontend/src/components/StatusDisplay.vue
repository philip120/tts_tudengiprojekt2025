<template>
  <div id="statusArea">
    <p v-if="message" :class="statusClass">{{ message }}</p>
  </div>
</template>

<script>
export default {
  name: "StatusDisplay",
  props: {
    message: {
      type: String,
      required: true,
    },
    statusClass: {
      type: String,
      default: "",
    },
  },
};
</script>

<style scoped>
.error {
  color: red;
  font-weight: bold;
}
.success {
  color: green;
  font-weight: bold;
}
</style>