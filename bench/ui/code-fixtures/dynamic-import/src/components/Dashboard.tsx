import { lazy, Suspense } from "react";
import { enabledWidgets } from "../widgets.config";

// Widgets are loaded by name from the config, so their files have no static import.
const load = (name: string) => lazy(() => import(`./widgets/${name}.tsx`));

export default function Dashboard() {
  return (
    <main>
      <h1>Dashboard</h1>
      <Suspense fallback={null}>
        {enabledWidgets.map((name) => {
          const Widget = load(name);
          return <Widget key={name} />;
        })}
      </Suspense>
    </main>
  );
}
