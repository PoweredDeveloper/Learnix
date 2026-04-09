import { Outlet } from "react-router-dom";
import FloatingHeader from "@/components/ui/floating-header";

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <FloatingHeader />
      <main className="mx-auto max-w-6xl px-4 pt-20 pb-12">
        <Outlet />
      </main>
    </div>
  );
}
