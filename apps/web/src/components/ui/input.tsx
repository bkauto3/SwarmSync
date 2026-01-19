import * as React from "react"

import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "input-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--shadow-focus)] focus-visible:ring-offset-2 border border-[var(--border-base)] placeholder:text-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-70 focus:border-[var(--border-hover)]",
          className,
        )}
        ref={ref}
        {...props}
      />
    )
  },
)
Input.displayName = "Input"

export { Input }
