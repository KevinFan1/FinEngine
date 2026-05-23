import { inject, onBeforeUnmount, type InjectionKey } from "vue";
import { useRoute } from "vue-router";

export type PageRefreshHandler = () => void | Promise<void>;

export interface PageRefreshRegistry {
    register(routeKey: string, handler: PageRefreshHandler): void;
    unregister(routeKey: string, handler: PageRefreshHandler): void;
    refresh(routeKey: string): Promise<boolean>;
}

export const pageRefreshKey: InjectionKey<PageRefreshRegistry> = Symbol(
    "pageRefresh",
);

export function usePageRefresh(handler: PageRefreshHandler) {
    const registry = inject(pageRefreshKey, null);
    if (!registry) return;

    const route = useRoute();
    const routeKey = route.name ? String(route.name) : route.path;
    if (!routeKey) return;

    registry.register(routeKey, handler);

    onBeforeUnmount(() => {
        registry.unregister(routeKey, handler);
    });
}
