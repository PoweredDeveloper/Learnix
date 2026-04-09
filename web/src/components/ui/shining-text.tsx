import * as React from "react"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

interface ShiningTextProps {
  children: React.ReactNode
  className?: string
}

export function ShiningText({ children, className }: ShiningTextProps) {
  return (
    <motion.span
      className={cn("bg-clip-text text-base font-normal text-transparent", className)}
      style={{
        backgroundImage:
          "linear-gradient(110deg, hsl(var(--muted-foreground)) 35%, hsl(var(--primary)) 50%, hsl(var(--muted-foreground)) 75%)",
        backgroundSize: "200% 100%",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        backgroundClip: "text",
      }}
      initial={{ backgroundPosition: "200% 0" }}
      animate={{ backgroundPosition: "-200% 0" }}
      transition={{
        repeat: Infinity,
        duration: 2,
        ease: "linear",
      }}
    >
      {children}
    </motion.span>
  )
}
