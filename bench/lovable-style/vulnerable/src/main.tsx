import { createRoot } from "react-dom/client";
import App from "./App";

window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled error", event.reason);
});

createRoot(document.getElementById("root")!).render(<App />);
