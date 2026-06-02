export const DOWNLOAD_CENTER_ROUTE = { name: "DownloadCenter" } as const;

type DownloadCenterTarget = {
    fullPath: string;
    href: string;
};

export interface DownloadCenterRouterLike {
    currentRoute: {
        value: {
            fullPath: string;
        };
    };
    resolve: (to: typeof DOWNLOAD_CENTER_ROUTE) => DownloadCenterTarget;
    push: (to: typeof DOWNLOAD_CENTER_ROUTE) => Promise<unknown>;
}

export interface DownloadCenterLocationLike {
    assign: (href: string) => void;
}

export async function navigateToDownloadCenter(
    router: DownloadCenterRouterLike,
    location: DownloadCenterLocationLike,
) {
    const target = router.resolve(DOWNLOAD_CENTER_ROUTE);
    if (router.currentRoute.value.fullPath === target.fullPath) return;

    try {
        await router.push(DOWNLOAD_CENTER_ROUTE);
        if (router.currentRoute.value.fullPath === target.fullPath) {
            return;
        }
    } catch {
        // Fall through to a hard redirect when in-app navigation is interrupted.
    }

    if (router.currentRoute.value.fullPath !== target.fullPath) {
        location.assign(target.href);
    }
}
