import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GraduationCap, Menu, Settings, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const navLinks = [{ label: 'Dashboard', href: '/' }]

export default function FloatingHeader() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4">
      <header className={cn('pointer-events-auto w-full max-w-280', 'rounded-xl border border-border/50 shadow-lg', 'bg-card/70 backdrop-blur-xl')}>
        <nav className="flex items-center justify-between gap-1 p-1 sm:gap-1.5 sm:p-1.5">
          <div className="flex min-w-0 flex-1 items-center">
            <Link to="/" className="flex min-w-0 max-w-full cursor-pointer items-center gap-1.5 rounded-md px-1.5 py-1 duration-100 hover:bg-accent sm:gap-2 sm:px-2">
              <GraduationCap className="h-5 w-5 shrink-0 text-primary" />
              <span className="truncate text-sm font-bold sm:text-base">Learnix</span>
            </Link>
          </div>

          <div className="hidden shrink-0 items-center gap-1 md:flex">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={cn(
                  'inline-flex items-center justify-center whitespace-nowrap rounded-md px-2 py-1.5 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                  location.pathname === link.href && 'bg-accent',
                )}
              >
                {link.label}
              </Link>
            ))}
            <Link to="/settings" className={cn('rounded-md p-2 text-muted-foreground transition-colors', 'hover:bg-accent hover:text-foreground', location.pathname === '/settings' && 'bg-accent text-foreground')} aria-label="Settings">
              <Settings className="h-4 w-4" />
            </Link>
          </div>
          <Button size="icon" variant="outline" className="h-8 w-8 shrink-0 md:hidden" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </nav>

        {mobileOpen && (
          <div className="border-t border-border/50 px-3 pb-3 pt-2 md:hidden">
            <div className="flex flex-col gap-0.5">
              {navLinks.map((link) => (
                <Link key={link.href} to={link.href} className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent" onClick={() => setMobileOpen(false)}>
                  {link.label}
                </Link>
              ))}
              <Link to="/settings" className={cn('inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium hover:bg-accent', location.pathname === '/settings' && 'bg-accent')} onClick={() => setMobileOpen(false)}>
                <Settings className="h-4 w-4" />
                Settings
              </Link>
            </div>
          </div>
        )}
      </header>
    </div>
  )
}
