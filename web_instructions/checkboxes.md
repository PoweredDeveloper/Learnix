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
checkbox.tsx
import React from 'react'

interface CheckboxProps {
  checked?: boolean
  onChange?: (checked: boolean) => void
  disabled?: boolean
  indeterminate?: boolean
  children?: React.ReactNode
}

const getInputClasses = (checked: boolean, disabled: boolean, indeterminate: boolean) => {
  let className = 'relative border w-4 h-4 duration-200 rounded inline-flex items-center justify-center'
  if (disabled) {
    if (!checked || indeterminate) {
      className += ' bg-gray-100 border-gray-500'
      if (indeterminate) {
        className += ' stroke-gray-500'
      } else {
        className += ' fill-gray-100 stroke-gray-100'
      }
    } else {
      className += ' bg-gray-600 border-gray-600 fill-gray-600 stroke-gray-100'
    }
  } else {
    if (!checked || indeterminate) {
      className += ' bg-background-100 border-gray-700 group-hover:bg-gray-200'
      if (indeterminate) {
        className += ' stroke-gray-700'
      } else {
        className += ' fill-background-100 stroke-background-100 group-hover:stroke-gray-200 group-hover:fill-gray-200'
      }
    } else {
      className += ' bg-gray-1000 border-gray-1000 fill-gray-1000 stroke-gray-100'
    }
  }

  return className
}

export const Checkbox = ({ checked = false, onChange, disabled = false, indeterminate = false, children }: CheckboxProps) => {
  return (
    <div className={`flex items-center cursor-pointer text-[13px] font-sans group ${disabled ? 'text-gray-500' : 'text-gray-1000'}`} onClick={() => onChange && !indeterminate && onChange(!checked)}>
      <input disabled={disabled} type="checkbox" checked={checked} className="absolute w-[1px] h-[1px] p-0 overflow-hidden whitespace-nowrap border-none" />
      <span className={getInputClasses(checked, disabled, indeterminate)}>
        <svg className="shrink-0" height="16" viewBox="0 0 20 20" width="16">
          {indeterminate ? <line strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" x1="5" x2="15" y1="10" y2="10" /> : <path d="M14 7L8.5 12.5L6 10" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />}
        </svg>
      </span>
      <span className="ml-2">{children}</span>
    </div>
  )
}

demo.tsx
import React, { useState } from 'react'
import { Checkbox } from '@/components/ui/checkbox'

export const Demo = () => {
  const [checked, setChecked] = useState(false)

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <div className="font-bold text-xl dark:text-white">Default</div>
        <Checkbox checked={checked} onChange={(): void => setChecked((value) => !value)}>
          Option 1
        </Checkbox>
      </div>
      <div className="flex flex-col gap-2">
        <div className="font-bold text-xl dark:text-white">Disabled</div>
        <Checkbox disabled>Disabled</Checkbox>
        <Checkbox checked disabled>
          Disabled Checked
        </Checkbox>
        <Checkbox disabled indeterminate>
          Disabled Indeterminate
        </Checkbox>
      </div>
      <div className="flex flex-col gap-2">
        <div className="font-bold text-xl dark:text-white">Indeterminate</div>
        <Checkbox indeterminate>Option 1</Checkbox>
      </div>
    </div>
  )
}

export const Default = () => {
  const [checked, setChecked] = useState(false)

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <div className="font-bold text-xl dark:text-white">Default</div>
        <Checkbox checked={checked} onChange={(): void => setChecked((b) => !b)}>
          Option 1
        </Checkbox>
      </div>
    </div>
  )
}

export const Disabled = () => (
  <div className="flex flex-col gap-8">
    <div className="flex flex-col gap-2">
      <div className="font-bold text-xl dark:text-white">Disabled</div>
      <Checkbox disabled>Disabled</Checkbox>
      <Checkbox checked disabled>
        Disabled Checked
      </Checkbox>
      <Checkbox disabled indeterminate>
        Disabled Indeterminate
      </Checkbox>
    </div>
  </div>
)

export const Indeterminate = () => (
  <div className="flex flex-col gap-8">
    <div className="flex flex-col gap-2">
      <div className="font-bold text-xl dark:text-white">Indeterminate</div>
      <Checkbox indeterminate>Option 1</Checkbox>
    </div>
  </div>
)
```

Extend existing tailwind.config.js with this code:

```js
/** @type {import('tailwindcss').Config} */

module.exports = {
  theme: {
    extend: {
      colors: {
        'gray-100': 'var(--ds-gray-100)',
        'gray-200': 'var(--ds-gray-200)',
        'gray-500': 'var(--ds-gray-500)',
        'gray-600': 'var(--ds-gray-600)',
        'gray-700': 'var(--ds-gray-700)',
        'gray-1000': 'var(--ds-gray-1000)',
        'background-100': 'var(--ds-background-100)',
      },
    },
  },
}
```

Extend existing globals.css with this code:

```css
@layer base {
  :root {
    --ds-gray-100: hsla(0, 0%, 95%, 1);
    --ds-gray-200: hsla(0, 0%, 92%, 1);
    --ds-gray-500: hsla(0, 0%, 79%, 1);
    --ds-gray-600: hsla(0, 0%, 66%, 1);
    --ds-gray-700: hsla(0, 0%, 56%, 1);
    --ds-gray-1000: hsla(0, 0%, 9%, 1);
    --ds-background-100: hsla(0, 0%, 100%, 1);
  }

  .dark {
    --ds-gray-100: hsla(0, 0%, 10%, 1);
    --ds-gray-200: hsla(0, 0%, 12%, 1);
    --ds-gray-500: hsla(0, 0%, 27%, 1);
    --ds-gray-600: hsla(0, 0%, 53%, 1);
    --ds-gray-700: hsla(0, 0%, 56%, 1);
    --ds-gray-1000: hsla(0, 0%, 93%, 1);
    --ds-background-100: hsla(0, 0%, 4%, 1);
  }
}
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
