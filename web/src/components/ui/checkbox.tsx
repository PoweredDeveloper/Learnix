import { useEffect, useRef } from "react"
import { cn } from "@/lib/utils"

export interface CheckboxProps {
  checked?: boolean
  onChange?: (checked: boolean) => void
  disabled?: boolean
  indeterminate?: boolean
  children?: React.ReactNode
  className?: string
}

/**
 * Custom checkbox (web_instructions/checkboxes.md), themed for the app palette.
 */
export function Checkbox({
  checked = false,
  onChange,
  disabled = false,
  indeterminate = false,
  children,
  className,
}: CheckboxProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const el = inputRef.current
    if (el) {
      el.indeterminate = Boolean(indeterminate)
    }
  }, [indeterminate])

  return (
    <label
      className={cn(
        "group flex cursor-pointer select-none items-center gap-2 font-sans text-[13px]",
        disabled ? "cursor-not-allowed text-muted-foreground" : "text-foreground",
        className,
      )}
    >
      <input
        ref={inputRef}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.checked)}
        className="sr-only"
      />
      <span
        className={cn(
          "relative inline-flex h-4 w-4 shrink-0 items-center justify-center rounded border duration-200",
          disabled && !checked && !indeterminate && "border-muted-foreground/35 bg-muted",
          disabled && checked && "border-primary/40 bg-primary/40 text-primary-foreground",
          disabled && indeterminate && "border-muted-foreground/35 bg-muted text-muted-foreground",
          !disabled && !checked && !indeterminate && "border-[var(--ds-gray-700)] bg-[var(--ds-background-100)] group-hover:bg-[var(--ds-gray-200)]",
          !disabled && checked && "border-primary bg-primary text-primary-foreground",
          !disabled && indeterminate && "border-[var(--ds-gray-700)] bg-[var(--ds-gray-200)] text-foreground",
        )}
      >
        <svg className="shrink-0" height="16" viewBox="0 0 20 20" width="16" aria-hidden="true">
          {indeterminate ? (
            <line
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              x1="5"
              x2="15"
              y1="10"
              y2="10"
            />
          ) : (
            <path
              className={cn(!checked && "opacity-0")}
              d="M14 7L8.5 12.5L6 10"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
            />
          )}
        </svg>
      </span>
      {children != null && <span>{children}</span>}
    </label>
  )
}
