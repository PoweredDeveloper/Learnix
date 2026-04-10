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
calendar.tsx
;('use client')

import { cn } from '@/lib/utils'
import { ChevronLeftIcon, ChevronRightIcon, ChevronsUpDownIcon } from 'lucide-react'
import type * as React from 'react'
import { DayPicker } from 'react-day-picker'

const buttonClassNames =
  "relative flex size-(--cell-size) text-base sm:text-sm items-center justify-center rounded-lg text-foreground not-in-data-selected:hover:bg-accent disabled:pointer-events-none disabled:opacity-64 [&_svg:not([class*='opacity-'])]:opacity-80 [&_svg:not([class*='size-'])]:size-4.5 sm:[&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0"

export function Calendar({ className, classNames, showOutsideDays = true, components: userComponents, mode = 'single', ...props }: React.ComponentProps<typeof DayPicker>): React.ReactElement {
  const defaultClassNames = {
    button_next: buttonClassNames,
    button_previous: buttonClassNames,
    caption_label: 'text-base sm:text-sm font-medium flex items-center gap-2 h-full',
    day: 'size-(--cell-size) text-sm py-px',
    day_button: cn(
      buttonClassNames,
      'in-data-disabled:pointer-events-none in-[.range-middle]:rounded-none in-[.range-end:not(.range-start)]:rounded-s-none in-[.range-start:not(.range-end)]:rounded-e-none in-[.range-middle]:in-data-selected:bg-accent in-data-selected:bg-primary in-[.range-middle]:in-data-selected:text-foreground in-data-disabled:text-muted-foreground/72 in-data-outside:text-muted-foreground/72 in-data-selected:in-data-outside:text-primary-foreground in-data-selected:text-primary-foreground in-data-disabled:line-through outline-none in-[[data-selected]:not(.range-middle)]:transition-[color,background-color,border-radius,box-shadow] focus-visible:z-1 focus-visible:ring-[3px] focus-visible:ring-ring/50',
    ),
    dropdown: 'absolute bg-popover inset-0 opacity-0',
    dropdown_root:
      "relative has-focus:border-ring has-focus:ring-ring/50 has-focus:ring-[3px] border border-input shadow-xs/5 rounded-lg px-[calc(--spacing(3)-1px)] h-9 sm:h-8 [&_svg:not([class*='opacity-'])]:opacity-80 [&_svg:not([class*='size-'])]:size-4.5 sm:[&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:-me-1",
    dropdowns: 'w-full flex items-center text-base sm:text-sm justify-center h-(--cell-size) gap-1.5 *:[span]:font-medium',
    hidden: 'invisible',
    month: 'w-full',
    month_caption: 'relative mx-(--cell-size) px-1 mb-1 flex h-(--cell-size) items-center justify-center z-2',
    months: 'relative flex flex-col sm:flex-row gap-2',
    nav: 'absolute top-0 flex w-full justify-between z-1',
    outside: 'text-muted-foreground data-selected:bg-accent/50 data-selected:text-muted-foreground',
    range_end: 'range-end',
    range_middle: 'range-middle',
    range_start: 'range-start',
    today:
      '*:after:pointer-events-none *:after:absolute *:after:bottom-1 *:after:start-1/2 *:after:z-1 *:after:size-[3px] *:after:-translate-x-1/2 *:after:rounded-full *:after:bg-primary [&[data-selected]:not(.range-middle)>*]:after:bg-background [&[data-disabled]>*]:after:bg-foreground/30 *:after:transition-colors',
    week_number: 'size-(--cell-size) p-0 text-xs font-medium text-muted-foreground/72',
    weekday: 'size-(--cell-size) p-0 text-xs font-medium text-muted-foreground/72',
  }
  const mergedClassNames: typeof defaultClassNames = Object.keys(defaultClassNames).reduce(
    (acc, key) => {
      const userClass = classNames?.[key as keyof typeof classNames]
      const baseClass = defaultClassNames[key as keyof typeof defaultClassNames]

      acc[key as keyof typeof defaultClassNames] = userClass ? cn(baseClass, userClass) : baseClass

      return acc
    },
    { ...defaultClassNames } as typeof defaultClassNames,
  )

  const defaultComponents = {
    Chevron: ({ className, orientation, ...props }: { className?: string; orientation?: 'left' | 'right' | 'up' | 'down' }): React.ReactElement => {
      if (orientation === 'left') {
        return <ChevronLeftIcon className={cn(className, 'rtl:rotate-180')} {...props} aria-hidden="true" />
      }

      if (orientation === 'right') {
        return <ChevronRightIcon className={cn(className, 'rtl:rotate-180')} {...props} aria-hidden="true" />
      }

      return <ChevronsUpDownIcon className={className} {...props} aria-hidden="true" />
    },
  }

  const mergedComponents = {
    ...defaultComponents,
    ...userComponents,
  }

  const dayPickerProps = {
    className: cn('w-fit [--cell-size:--spacing(10)] sm:[--cell-size:--spacing(9)]', className),
    classNames: mergedClassNames,
    components: mergedComponents,
    'data-slot': 'calendar',
    formatters: {
      formatMonthDropdown: (date: Date) => date.toLocaleString('default', { month: 'short' }),
    } as React.ComponentProps<typeof DayPicker>['formatters'],
    mode,
    showOutsideDays,
    ...props,
  }

  return <DayPicker {...(dayPickerProps as React.ComponentProps<typeof DayPicker>)} />
}

demo.tsx
;('use client')

import { useState } from 'react'
import { Calendar } from '@/components/ui/calendar'

export default function CalendarDefault() {
  const [date, setDate] = useState<Date | undefined>(new Date())

  return (
    <div className="flex items-center justify-center w-full min-h-screen bg-background p-8">
      <Calendar mode="single" selected={date} onSelect={setDate} />
    </div>
  )
}
```

Install NPM dependencies:

```bash
lucide-react, react-day-picker
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
