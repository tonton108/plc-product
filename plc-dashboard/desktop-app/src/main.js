import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// ページコンポーネント
import EquipmentList from './pages/EquipmentList.vue'
import Monitoring from './pages/Monitoring.vue'

// Vuetifyインスタンス作成
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107'
        }
      }
    }
  }
})

// ルーター設定
const routes = [
  {
    path: '/',
    name: 'home',
    component: EquipmentList
  },
  {
    path: '/monitoring/:id',
    name: 'monitoring',
    component: Monitoring
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// Vueアプリケーション作成
const app = createApp(App)
app.use(vuetify)
app.use(router)
app.mount('#app')
