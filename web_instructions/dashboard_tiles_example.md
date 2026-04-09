You are given a task to integrate an existing React component in the codebase

The codebase should support:

- shadcn project structure
- Tailwind CSS
- Typescript

If it doesn't, provide instructions on how to setup project via shadcn CLI, install Tailwind or Typescript.

Determine the default path for components and styles.
If default path for components is not /components/ui, provide instructions on why it's important to create this folder
Copy-paste this component to /components/ui folder:

```tsx
dashboard - overview.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils' // Assumes shadcn's utility for class merging
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowDown, ArrowUp, Minus, Users, DollarSign, Clock, AlertCircle } from 'lucide-react'

// Define the icon type. Using React.ElementType for flexibility.
type IconType = React.ElementType | React.FunctionComponent<React.SVGProps<SVGSVGElement>>

// Define trend types
export type TrendType = 'up' | 'down' | 'neutral'

// --- 📦 API (Props) Definition ---
export interface DashboardMetricCardProps {
  /** The main value of the metric (e.g., "1,234", "$5.6M", "92%"). */
  value: string
  /** The descriptive title of the metric (e.g., "Total Users", "Revenue"). */
  title: string
  /** Optional icon to display in the card header. */
  icon?: IconType
  /** The percentage or absolute change for the trend (e.g., "2.5%"). */
  trendChange?: string
  /** The direction of the trend ('up', 'down', 'neutral'). */
  trendType?: TrendType
  /** Optional class name for the card container. */
  className?: string
}

/**
 * A professional, animated metric card for admin dashboards.
 * Displays a key value, title, icon, and trend indicator with Framer Motion hover effects.
 */
const DashboardMetricCard: React.FC<DashboardMetricCardProps> = ({ value, title, icon: IconComponent, trendChange, trendType = 'neutral', className }) => {
  // Determine trend icon and color
  const TrendIcon = trendType === 'up' ? ArrowUp : trendType === 'down' ? ArrowDown : Minus
  const trendColorClass = trendType === 'up' ? 'text-green-600 dark:text-green-400' : trendType === 'down' ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'

  return (
    <motion.div
      whileHover={{ y: -4, boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)' }} // Subtle lift and shadow on hover
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      className={cn(
        'cursor-pointer rounded-lg', // Ensure cursor indicates interactivity
        className,
      )}
    >
      <Card className="h-full transition-colors duration-200">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          {IconComponent && <IconComponent className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground mb-2">{value}</div>
          {trendChange && (
            <p className={cn('flex items-center text-xs font-medium', trendColorClass)}>
              <TrendIcon className="h-3 w-3 mr-1" aria-hidden="true" />
              {trendChange} {trendType === 'up' ? 'increase' : trendType === 'down' ? 'decrease' : 'change'}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

const ExampleUsage = () => {
  return (
    <div className="p-8 bg-background border rounded-lg max-w-7xl mx-auto shadow-md">
      <h3 className="text-xl font-semibold text-foreground mb-6">Dashboard Overview</h3>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardMetricCard title="Total Users" value="2,350" icon={Users} trendChange="+180" trendType="up" />
        <DashboardMetricCard title="Revenue" value="$12,450" icon={DollarSign} trendChange="-2.5%" trendType="down" />
        <DashboardMetricCard
          title="Avg. Session"
          value="4m 32s"
          icon={Clock}
          trendChange="+0.5s"
          trendType="neutral" // Or "up" if positive
        />
        <DashboardMetricCard
          title="Open Tickets"
          value="12"
          icon={AlertCircle} // Using AlertCircle from lucide-react if needed
          trendChange="+3"
          trendType="up"
          className="lg:col-span-1" // Example of custom class for layout
        />
      </div>
    </div>
  )
}

export default ExampleUsage

demo.tsx
import ExampleUsage from '@/components/ui/dashboard-overview'

export default function DemoOne() {
  return <ExampleUsage />
}
```

Copy-paste these files for dependencies:

```tsx
shadcn / card
import * as React from 'react'

import { cn } from '@/lib/utils'

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => <div ref={ref} className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)} {...props} />)
Card.displayName = 'Card'

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />)
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) => (
  <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className, ...props }, ref) => <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />)
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />)
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />)
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

Install NPM dependencies:

```bash
lucide-react, framer-motion
```

Implementation Guidelines

1.  Analyze the component structure and identify all required dependencies
2.  Review the component's argumens and state
3.  Identify any required context providers or hooks and install them
4.  Questions to Ask

- What data/props will be passed to this component?
- Are there any specific state management requirements?
- Are there any required assets (images, icons, etc.)?
- What is the expected responsive behavior?
- What is the best place to use this component in the app?

Steps to integrate 0. Copy paste all the code above in the correct directories

1.  Install external dependencies
2.  Fill image assets with Unsplash stock images you know exist
3.  Use lucide-react icons for svgs or logos if component requires them
