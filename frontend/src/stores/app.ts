import { defineStore } from "pinia";
import { ref } from "vue";

export interface Tab {
    path: string;
    title: string;
    closable: boolean;
}

export const useAppStore = defineStore("app", () => {
    // State
    const sidebarCollapsed = ref(false);
    const visitedTabs = ref<Tab[]>([
        { path: "/dashboard", title: "首页", closable: false },
    ]);

    // Sidebar actions
    function toggleSidebar() {
        sidebarCollapsed.value = !sidebarCollapsed.value;
    }

    function setSidebarCollapsed(collapsed: boolean) {
        sidebarCollapsed.value = collapsed;
    }

    // Tab actions
    function addTab(tab: Tab) {
        const exists = visitedTabs.value.some((t) => t.path === tab.path);
        if (!exists) {
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
        visitedTabs,
        toggleSidebar,
        setSidebarCollapsed,
        addTab,
        removeTab,
        closeOtherTabs,
        closeAllTabs,
    };
});
