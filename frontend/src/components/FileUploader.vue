<template>
  <div>
    <label for="pdfFile">Choose PDF file:</label>
    <input type="file" id="pdfFile" @change="$emit('file-selected', $event.target.files[0])" accept=".pdf" required />
  </div>
</template>

<script>
export default {
  name: "FileUploader",
};
</script>

<style scoped>
/* Add any specific styles for the file uploader here */
</style>