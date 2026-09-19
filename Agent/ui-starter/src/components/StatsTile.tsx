import React from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, LucideIcon } from "lucide-react";
import { Card, CardContent } from "./ui/card";
import { cn } from "@/lib/utils";

interface StatsTileProps {
  title: string;
  value: string;
  subtext: string;
  icon: LucideIcon;
  trend?: string;
  isPositive?: boolean;
  glowColor?: "primary" | "success" | "warning";
}

export const StatsTile: React.FC<StatsTileProps> = ({
  title,
  value,
  subtext,
  icon: Icon,
  trend,
  isPositive = true,
  glowColor = "primary",
}) => {
  return (
    <motion.div
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      <Card className="relative overflow-hidden border-border/70 hover:border-primary/40 hover:shadow-md">
        {/* Soft Ambient Radial Light */}
        <div
          className={cn(
            "pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-20 blur-2xl transition-opacity",
            glowColor === "primary" && "bg-primary",
            glowColor === "success" && "bg-success",
            glowColor === "warning" && "bg-warning"
          )}
        />

        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-foreground">
              <Icon className="h-4 w-4" />
            </div>
          </div>

          <div className="mt-4 flex items-baseline justify-between">
            <div className="font-sans text-2xl font-bold tracking-tight text-foreground">{value}</div>
            {trend && (
              <div
                className={cn(
                  "flex items-center text-xs font-semibold",
                  isPositive ? "text-success" : "text-danger"
                )}
              >
                <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" />
                {trend}
              </div>
            )}
          </div>

          <p className="mt-1 text-xs text-muted-foreground">{subtext}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
};
