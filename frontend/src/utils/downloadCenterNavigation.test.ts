import test from "node:test";
import assert from "node:assert/strict";
import {
    DOWNLOAD_CENTER_ROUTE,
    navigateToDownloadCenter,
    type DownloadCenterRouterLike,
} from "./downloadCenterNavigation.ts";

function createRouterState(currentFullPath = "/summaries") {
    const route = { fullPath: currentFullPath };
    let pushCount = 0;
    let pushedTo: unknown;

    const router: DownloadCenterRouterLike = {
        currentRoute: { value: route },
        resolve: () => ({ fullPath: "/downloads", href: "/downloads" }),
        push: async (to) => {
            pushCount += 1;
            pushedTo = to;
        },
    };

    return {
        route,
        router,
        get pushCount() {
            return pushCount;
        },
        get pushedTo() {
            return pushedTo;
        },
    };
}

test("falls back to location assign when router push resolves but route does not change", async () => {
    const state = createRouterState();
    let assignedHref = "";

    await navigateToDownloadCenter(state.router, {
        assign: (href) => {
            assignedHref = href;
        },
    });

    assert.equal(state.pushCount, 1);
    assert.deepEqual(state.pushedTo, DOWNLOAD_CENTER_ROUTE);
    assert.equal(assignedHref, "/downloads");
});

test("uses explicit downloads path as the navigation target", async () => {
    const state = createRouterState();

    await navigateToDownloadCenter(state.router, {
        assign: () => {},
    });

    assert.deepEqual(state.pushedTo, { path: "/downloads" });
});

test("does not hard redirect after router navigation succeeds", async () => {
    const state = createRouterState();
    let assignedHref = "";
    state.router.push = async () => {
        state.route.fullPath = "/downloads";
    };

    await navigateToDownloadCenter(state.router, {
        assign: (href) => {
            assignedHref = href;
        },
    });

    assert.equal(state.route.fullPath, "/downloads");
    assert.equal(assignedHref, "");
});

test("skips navigation when already on download center", async () => {
    const state = createRouterState("/downloads");
    let assignedHref = "";

    await navigateToDownloadCenter(state.router, {
        assign: (href) => {
            assignedHref = href;
        },
    });

    assert.equal(state.pushCount, 0);
    assert.equal(assignedHref, "");
});
