<template>
  <router-view />
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
html,
body,
#app {
  min-height: 100%;
}

/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'IBM Plex Sans', 'Noto Sans SC', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #173126;
  background-color: #f7f4ea;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(23, 49, 38, 0.08);
}

::-webkit-scrollbar-thumb {
  background: rgba(31, 93, 69, 0.6);
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(31, 93, 69, 0.8);
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
