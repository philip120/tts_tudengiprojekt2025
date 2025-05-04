<template>
  <div id="downloadArea">
    <a v-if="link" :href="link" target="_blank">Download Podcast (.wav)</a>
    <p v-else>Download link will appear here when ready.</p>
  </div>
</template>

<script>
export default {
  name: "DownloadLink",
  props: {
    link: {
      type: String,
      default: "",
    },
  },
};
</script>

<style scoped>
a {
  display: inline-block;
  margin-top: 0.5em;
  padding: 0.5em 1em;
  background-color: #007bff;
  color: white;
  text-decoration: none;
  border-radius: 4px;
}
a:hover {
  background-color: #0056b3;
}
</style>