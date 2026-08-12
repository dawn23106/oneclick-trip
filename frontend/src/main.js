import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'

// 前端启动入口：把 App.vue 挂载到 index.html 里的 #app 节点。
createApp(App).use(ElementPlus).mount('#app')
