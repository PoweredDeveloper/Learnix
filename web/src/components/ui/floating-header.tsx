import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GraduationCap, Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const navLinks = [{ label: 'Dashboard', href: '/' }]

export default function FloatingHeader() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  return (
    <header className={cn('fixed top-4 left-1/2 -translate-x-1/2 z-50', 'mx-auto w-full max-w-6xl rounded-lg border border-border/50 shadow-lg', 'bg-card/70 backdrop-blur-xl')}>
      <nav className="mx-auto flex items-center justify-between p-1.5">
        <Link to="/" className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 duration-100 hover:bg-accent">
          <GraduationCap className="h-5 w-5 text-primary" />
          <span className="text-base font-bold">Learnix</span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              to={link.href}
              className={cn(
                'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                location.pathname === link.href && 'bg-accent',
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <Button size="icon" variant="outline" className="md:hidden" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
          {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      </nav>

      {mobileOpen && (
        <div className="border-t border-border/50 px-4 pb-4 pt-2 md:hidden">
          <div className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link key={link.href} to={link.href} className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent" onClick={() => setMobileOpen(false)}>
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  )
}
