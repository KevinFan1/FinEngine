import { createApp } from "vue";
import { createPinia } from "pinia";
import { ElLoading } from "element-plus/es/components/loading/index.mjs";
import "element-plus/es/components/message/style/css";

import App from "./App.vue";
import router from "./router";
import { useThemeStore } from "./stores/theme";
import { registerIcons } from "./plugins/icons";
import "./styles/global.scss";

const app = createApp(App);

registerIcons(app);
app.use(ElLoading);

const pinia = createPinia();
app.use(pinia);
app.use(router);

// Initialize theme before mounting
const themeStore = useThemeStore();
themeStore.applyTheme();

app.mount("#app");
