import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-border",
        // 3-layer Tint Formula (nền alpha 10%, viền alpha 25%, chữ chuẩn trạng thái)
        success: "border-success/25 bg-success/10 text-success",
        info: "border-primary/25 bg-primary/10 text-primary",
        warning: "border-warning/30 bg-warning/10 text-warning",
        danger: "border-destructive/25 bg-destructive/10 text-destructive",
        // Phân loại danh mục
        doc: "border-cat-doc/25 bg-cat-doc/10 text-cat-doc",
        code: "border-cat-code/25 bg-cat-code/10 text-cat-code",
        cert: "border-cat-cert/30 bg-cat-cert/10 text-cat-cert",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
