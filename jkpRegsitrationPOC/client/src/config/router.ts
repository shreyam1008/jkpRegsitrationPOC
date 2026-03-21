import {
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { RootLayout } from "@/components/layout/RootLayout";
import { SearchPage } from "@/pages/search/SearchPage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";

// Root route — renders the shell layout with <Outlet />
const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFoundPage,
});

// Search page — "/" (home)
const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: SearchPage,
});

// Route tree
const routeTree = rootRoute.addChildren([searchRoute]);

// Router instance
export const router = createRouter({ routeTree });

// Type registration for type-safe navigation
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
