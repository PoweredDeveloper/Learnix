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
admonition.tsx
import React from 'react'
import { AlertCircle, AlertTriangle, CheckCircle, Info, Lightbulb, XCircle } from 'lucide-react'

const admonitionConfig = {
  note: {
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    borderColor: 'border-blue-200 dark:border-blue-800',
    textColor: 'text-blue-700 dark:text-blue-300',
    iconColor: 'text-blue-600 dark:text-blue-400',
    icon: Info,
  },
  tip: {
    bgColor: 'bg-green-50 dark:bg-green-950/30',
    borderColor: 'border-green-200 dark:border-green-800',
    textColor: 'text-green-700 dark:text-green-300',
    iconColor: 'text-green-600 dark:text-green-400',
    icon: Lightbulb,
  },
  info: {
    bgColor: 'bg-cyan-50 dark:bg-cyan-950/30',
    borderColor: 'border-cyan-200 dark:border-cyan-800',
    textColor: 'text-cyan-700 dark:text-cyan-300',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
    icon: Info,
  },
  warning: {
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
    borderColor: 'border-amber-200 dark:border-amber-700',
    textColor: 'text-amber-700 dark:text-amber-300',
    iconColor: 'text-amber-600 dark:text-amber-400',
    icon: AlertTriangle,
  },
  danger: {
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    borderColor: 'border-red-200 dark:border-red-800',
    textColor: 'text-red-700 dark:text-red-300',
    iconColor: 'text-red-600 dark:text-red-400',
    icon: XCircle,
  },
  success: {
    bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
    textColor: 'text-emerald-700 dark:text-emerald-300',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    icon: CheckCircle,
  },
  caution: {
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
    borderColor: 'border-orange-200 dark:border-orange-700',
    textColor: 'text-orange-700 dark:text-orange-300',
    iconColor: 'text-orange-600 dark:text-orange-400',
    icon: AlertCircle,
  },
}

interface AdmonitionProps {
  type?: keyof typeof admonitionConfig
  title?: string
  children: React.ReactNode
  icon?: React.ComponentType<{ className?: string }>
  className?: string
}

export function Admonition({ type = 'note', title, children, icon: CustomIcon, className = '' }: AdmonitionProps) {
  const config = admonitionConfig[type]
  const IconComponent = CustomIcon || config.icon

  return (
    <div
      className={`
        ${config.bgColor}
        ${config.borderColor}
        border
        rounded-lg
        p-4
        ${className}
      `.trim()}
    >
      <div className="flex gap-3">
        <div className={`${config.iconColor} flex-shrink-0 mt-0.5`}>
          <IconComponent className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          {title && <div className={`${config.textColor} font-semibold text-sm mb-1`}>{title}</div>}
          <div className={`${config.textColor} text-sm leading-relaxed`}>{children}</div>
        </div>
      </div>
    </div>
  )
}

export default Admonition

demo.tsx
;('use client')

import React from 'react'
import Admonition from '@/components/ui/admonition'

export default function AdmonitionTypesDemo() {
  return (
    <div className="w-full max-w-2xl mx-auto space-y-4 p-4">
      <Admonition type="note" title="Note">
        This is a note admonition for general information.
      </Admonition>

      <Admonition type="info" title="Info">
        This is an info admonition for informational content.
      </Admonition>

      <Admonition type="tip" title="Tip">
        This is a tip admonition for helpful suggestions.
      </Admonition>

      <Admonition type="success" title="Success">
        This is a success admonition for positive outcomes.
      </Admonition>

      <Admonition type="warning" title="Warning">
        This is a warning admonition for cautionary information.
      </Admonition>

      <Admonition type="caution" title="Caution">
        This is a caution admonition for important warnings.
      </Admonition>

      <Admonition type="danger" title="Danger">
        This is a danger admonition for critical alerts.
      </Admonition>
    </div>
  )
}
```

Install NPM dependencies:

```bash
lucide-react
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
