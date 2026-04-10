import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { GraduationCap } from "lucide-react"

interface ContainerProps {
  className?: string
  children: React.ReactNode
  delay?: number
  reverse?: boolean
}

function Container({ children, className, delay = 0.2, reverse }: ContainerProps) {
  return (
    <motion.div
      className={cn("w-full h-full", className)}
      initial={{ opacity: 0, y: reverse ? -20 : 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.4, type: "spring" }}
    >
      {children}
    </motion.div>
  )
}

export default function Footer() {
  return (
    <footer className="flex flex-col relative items-center justify-center border-t border-border/50 pt-12 pb-8 px-4 w-full max-w-6xl mx-auto">
      <div className="grid gap-8 md:grid-cols-3 w-full">
        <Container delay={0.1}>
          <div className="flex flex-col items-start">
            <Link to="/" className="flex items-center gap-2">
              <GraduationCap className="h-6 w-6 text-primary" />
              <span className="text-lg font-bold">Learnix</span>
            </Link>
            <p className="text-muted-foreground mt-3 text-sm">
              AI-powered learning platform. Master any topic with personalized
              courses, practice, and exams.
            </p>
          </div>
        </Container>

        <Container delay={0.2} className="h-auto">
          <h3 className="text-sm font-medium text-foreground">Platform</h3>
          <ul className="mt-3 text-sm text-muted-foreground space-y-2">
            <li>
              <Link to="/" className="hover:text-foreground transition-colors">
                Dashboard
              </Link>
            </li>
            <li>
              <Link
                to="/create-course"
                className="hover:text-foreground transition-colors"
              >
                Create Course
              </Link>
            </li>
          </ul>
        </Container>

        <Container delay={0.3} className="h-auto">
          <h3 className="text-sm font-medium text-foreground">About</h3>
          <ul className="mt-3 text-sm text-muted-foreground space-y-2">
            <li>
              <span>Built with AI for students</span>
            </li>
            <li>
              <span>Telegram bot integration</span>
            </li>
          </ul>
        </Container>
      </div>

      <Container delay={0.4} className="w-full mt-10">
        <div className="flex items-center justify-center border-t border-border/30 pt-6">
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} Learnix. Learn anything, anywhere.
          </p>
        </div>
      </Container>
    </footer>
  )
}
