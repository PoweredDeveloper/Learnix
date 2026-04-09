import React, { createContext, useContext, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface SwitchContextValue {
  value: string | null;
  setValue: (v: string) => void;
}

const SwitchContext = createContext<SwitchContextValue | null>(null);

interface SwitchProps {
  children: React.ReactNode;
  name?: string;
  size?: "small" | "medium" | "large";
  style?: React.CSSProperties;
  className?: string;
  onChange?: (value: string) => void;
  defaultValue?: string;
}

interface SwitchControlProps {
  label?: string;
  value: string;
  defaultChecked?: boolean;
  disabled?: boolean;
  name?: string;
  size?: "small" | "medium" | "large";
  icon?: React.ReactNode;
}

export function Switch({
  children,
  name = "default",
  size = "medium",
  style,
  className,
  onChange,
  defaultValue,
}: SwitchProps) {
  const [value, setValueRaw] = useState<string | null>(defaultValue ?? null);

  function setValue(v: string) {
    setValueRaw(v);
    onChange?.(v);
  }

  return (
    <SwitchContext.Provider value={{ value, setValue }}>
      <div
        className={cn(
          "flex flex-wrap rounded-md border border-input bg-muted p-1",
          size === "small" && "h-8",
          size === "medium" && "min-h-[2.5rem]",
          size === "large" && "min-h-[3rem] rounded-lg",
          className,
        )}
        style={style}
      >
        {React.Children.map(children, (child) =>
          React.isValidElement<SwitchControlProps>(child)
            ? React.cloneElement(child, { size, name })
            : child,
        )}
      </div>
    </SwitchContext.Provider>
  );
}

export function SwitchControl({
  label,
  value,
  defaultChecked,
  disabled = false,
  name,
  size = "medium",
  icon,
}: SwitchControlProps) {
  const context = useContext(SwitchContext);
  const checked = value === context?.value;

  useEffect(() => {
    if (defaultChecked && context?.value == null) {
      context?.setValue(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <label
      className={cn(
        "flex h-full",
        disabled && "pointer-events-none cursor-not-allowed",
      )}
      onClick={() => !disabled && context?.setValue(value)}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => context?.setValue(value)}
        disabled={disabled}
        className="hidden"
      />
      <span
        className={cn(
          "flex cursor-pointer items-center justify-center font-medium duration-150",
          checked
            ? "rounded-sm bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
          disabled && "text-muted-foreground/50",
          !icon && size === "small" && "px-3 text-sm",
          !icon && size === "medium" && "px-3 py-1 text-sm",
          !icon && size === "large" && "px-4 text-base",
          icon && size === "small" && "px-2 py-1",
          icon && size === "medium" && "px-3 py-2",
          icon && size === "large" && "p-3",
        )}
      >
        {icon ? (
          <span className={cn(size === "large" && "scale-125")}>{icon}</span>
        ) : (
          label
        )}
      </span>
    </label>
  );
}
