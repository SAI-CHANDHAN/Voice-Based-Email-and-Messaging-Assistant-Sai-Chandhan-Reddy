import { ReactNode, useEffect } from "react";
import { useGovind } from "@/contexts/GovindContext";
import { useNavigate } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { AssistantPanel } from "./AssistantPanel";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: ReactNode;
  fullWidth?: boolean;
}

export const Layout = ({ children, fullWidth = false }: LayoutProps) => {
  const navigate = useNavigate();
  const { routeIntent, setRouteIntent, isAssistantOpen } = useGovind();

  useEffect(() => {
    if (routeIntent) {
      navigate(routeIntent);
      setRouteIntent(null);
    }
  }, [routeIntent, navigate, setRouteIntent]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <Sidebar />

      <main
        className={cn(
          "pt-16 min-h-screen transition-all duration-300",
          "ml-16 lg:ml-64",
          fullWidth && "mr-0",
          isAssistantOpen && "mr-80" // shift content left when assistant is open
        )}
      >
        {children}
      </main>

      {/* Floating Assistant */}
      <AssistantPanel />
    </div>
  );
};
