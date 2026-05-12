import { defineStore } from "pinia";
import { ref } from "vue";

export interface Tab {
    path: string;
    fullPath?: string;
    name?: string;
    title: string;
    closable: boolean;
}

export const useAppStore = defineStore("app", () => {
    // State
    const sidebarCollapsed = ref(false);
    const tagCacheEnabled = ref(localStorage.getItem("tag-cache-enabled") !== "0");
    const visitedTabs = ref<Tab[]>([
        { path: "/dashboard", name: "Dashboard", title: "首页", closable: false },
    ]);

    // Sidebar actions
    function toggleSidebar() {
        sidebarCollapsed.value = !sidebarCollapsed.value;
    }

    function setSidebarCollapsed(collapsed: boolean) {
        sidebarCollapsed.value = collapsed;
    }

    function setTagCacheEnabled(enabled: boolean) {
        tagCacheEnabled.value = enabled;
        localStorage.setItem("tag-cache-enabled", enabled ? "1" : "0");
    }

    // Tab actions
    function addTab(tab: Tab) {
        const existingTab = visitedTabs.value.find((t) => t.path === tab.path);
        if (existingTab) {
            existingTab.fullPath = tab.fullPath || tab.path;
            existingTab.name = tab.name;
            existingTab.title = tab.title;
            existingTab.closable = tab.closable;
        } else {
            visitedTabs.value.push(tab);
        }
    }

    function removeTab(path: string) {
        const index = visitedTabs.value.findIndex((t) => t.path === path);
        if (index !== -1) {
            visitedTabs.value.splice(index, 1);
        }
    }

    function closeOtherTabs(path: string) {
        visitedTabs.value = visitedTabs.value.filter(
            (t) => !t.closable || t.path === path,
        );
    }

    function closeAllTabs() {
        visitedTabs.value = visitedTabs.value.filter((t) => !t.closable);
    }

    return {
        sidebarCollapsed,
        tagCacheEnabled,
        visitedTabs,
        toggleSidebar,
        setSidebarCollapsed,
        setTagCacheEnabled,
        addTab,
        removeTab,
        closeOtherTabs,
        closeAllTabs,
    };
});
