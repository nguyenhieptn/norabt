import React from "react";
import { Sparkles, Moon, Sun, Layers, ArrowUpRight } from "lucide-react";
import { Button } from "./ui/button";

interface NavbarProps {
  darkMode: boolean;
  onToggleTheme: () => void;
  onOpenAction: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ darkMode, onToggleTheme, onOpenAction }) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/70 bg-background/80 backdrop-blur-md transition-colors">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-glow">
            <Layers className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <span className="font-display text-lg font-bold tracking-tight text-foreground">
              ICTU <span className="text-primary">EVM</span>
            </span>
            <span className="ml-2 hidden rounded-full bg-brand-cyan/10 px-2 py-0.5 text-[10px] font-semibold text-brand-cyan sm:inline-block">
              UI DESIGN SYSTEM
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Theme Toggle Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleTheme}
            className="rounded-lg text-muted-foreground hover:text-foreground"
            aria-label="Chuyển đổi giao diện Sáng / Tối"
          >
            {darkMode ? <Sun className="h-5 w-5 text-warning" /> : <Moon className="h-5 w-5" />}
          </Button>

          {/* Connect / Action CTA Button */}
          <Button variant="cta" onClick={onOpenAction} className="gap-1.5 font-medium shadow-sm">
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">Khám phá Demo</span>
            <span className="sm:hidden">Demo</span>
            <ArrowUpRight className="h-3.5 w-3.5 opacity-80" />
          </Button>
        </div>
      </div>
    </header>
  );
};
