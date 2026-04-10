import { Outlet } from "react-router-dom";
import FloatingHeader from "@/components/ui/floating-header";
import Footer from "@/components/ui/footer";

export default function Layout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <FloatingHeader />
      <main className="mx-auto w-full max-w-6xl px-4 pt-20 pb-12 flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
