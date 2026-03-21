import { RouterProvider } from "@tanstack/react-router";
import { router } from "@/config/router";

function App() {
  return <RouterProvider router={router} />;
}

export default App;
