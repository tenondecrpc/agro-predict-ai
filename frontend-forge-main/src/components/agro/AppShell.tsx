import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { AppProvider } from "@/lib/agro/app-context";
import { Toaster } from "sonner";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AppProvider>
      <div className="min-h-screen flex bg-background">
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col">
          <Header />
          <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 max-w-[1400px] w-full mx-auto">
            {children}
          </main>
        </div>
        <Toaster richColors position="top-right" />
      </div>
    </AppProvider>
  );
}
