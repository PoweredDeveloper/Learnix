import * as React from "react"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

interface ShiningTextProps {
  children: React.ReactNode
  className?: string
}

const gradient =
  "linear-gradient(110deg,#404040,35%,#ffffff,50%,#404040,75%,#404040)"

export function ShiningText({ children, className }: ShiningTextProps) {
  return (
    <motion.span
      className={cn("text-base font-normal text-transparent", className)}
      style={{
        backgroundImage: gradient,
        backgroundSize: "200% 100%",
        WebkitBackgroundClip: "text",
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
