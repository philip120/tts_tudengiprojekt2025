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
#downloadArea a {
  display: inline-block;
  margin-top: 0.5em;
  padding: 0.5em 1em;
  background-color: #d3d3d3; 
  color: #000000; 
  border: 1px solid #a9a9a9; 
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  outline: none;
  transition: background-color 0.3s, transform 0.2s;
}

#downloadArea a:hover {
  background-color: #c0c0c0; 
  transform: scale(1.05);
}
</style>