import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2",
          variant === "default" && "bg-slate-900 text-white hover:bg-slate-800",
          variant === "outline" && "border border-slate-300 bg-white hover:bg-slate-50",
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
