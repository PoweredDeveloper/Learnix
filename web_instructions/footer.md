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
ruixen - footer03.tsx
;('use client')

import Link from 'next/link'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

interface Props {
  className?: string
  children: React.ReactNode
  delay?: number
  reverse?: boolean
  simple?: boolean
}

const Container = ({ children, className, delay = 0.2, reverse, simple }: Props) => {
  return (
    <motion.div
      className={cn('w-full h-full', className)}
      initial={{ opacity: 0, y: reverse ? -20 : 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: delay, duration: simple ? 0.2 : 0.4, type: simple ? 'keyframes' : 'spring', stiffness: simple && 100 }}
    >
      {children}
    </motion.div>
  )
}

export default function Footer_03() {
  return (
    <footer className="flex flex-col relative items-center justify-center border-t border-foreground/5 pt-16 pb-8 px-6 lg:px-8 w-full max-w-6xl mx-auto lg:pt-32">
      <div className="grid gap-8 xl:grid-cols-3 xl:gap-8 w-full">
        <Container>
          <div className="flex flex-col items-start justify-start md:max-w-[200px]">
            <div className="flex items-center gap-2">
              <Image src="/ruixen_dark.png" alt="Ruixen Logo" width={40} height={40} className="rounded-full h-10 w-10 block dark:hidden" />
              <Image src="/ruixen_light.png" alt="Ruixen Logo" width={40} height={40} className="rounded-full h-10 w-10 hidden dark:block" />
            </div>
            <p className="text-muted-foreground mt-4 text-sm text-start">Build better UIs faster with Ruixen – the AI-enhanced component library for modern teams.</p>
          </div>
        </Container>

        <div className="grid-cols-2 gap-8 grid mt-16 xl:col-span-2 xl:mt-0">
          <div className="md:grid md:grid-cols-2 md:gap-8">
            <Container delay={0.1} className="h-auto">
              <h3 className="text-base font-normal text-foreground">Ruixen</h3>
              <ul className="mt-4 text-sm text-gray-500 space-y-4">
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Components
                  </Link>
                </li>
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Pricing
                  </Link>
                </li>
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Use Cases
                  </Link>
                </li>
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Language Support
                  </Link>
                </li>
              </ul>
            </Container>
            <Container delay={0.2} className="h-auto">
              <div className="mt-10 md:mt-0 flex flex-col">
                <h3 className="text-base font-normal text-foreground">Solutions</h3>
                <ul className="mt-4 text-sm text-gray-500 space-y-4">
                  <li>
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Developers
                    </Link>
                  </li>
                  <li className="mt-2">
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Design Teams
                    </Link>
                  </li>
                  <li className="mt-2">
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Startups
                    </Link>
                  </li>
                  <li className="mt-2">
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Enterprises
                    </Link>
                  </li>
                </ul>
              </div>
            </Container>
          </div>
          <div className="md:grid md:grid-cols-2 md:gap-8">
            <Container delay={0.3} className="h-auto">
              <h3 className="text-base font-normal text-foreground">Resources</h3>
              <ul className="mt-4 text-sm text-gray-500 space-y-4">
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Documentation
                  </Link>
                </li>
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Component Guides
                  </Link>
                </li>
                <li className="mt-2">
                  <Link href="#" className="link hover:text-foreground transition-all duration-300">
                    Support Center
                  </Link>
                </li>
              </ul>
            </Container>
            <Container delay={0.4} className="h-auto">
              <div className="mt-10 md:mt-0 flex flex-col">
                <h3 className="text-base font-normal text-foreground">Company</h3>
                <ul className="mt-4 text-sm text-gray-500 space-y-4">
                  <li>
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Our Story
                    </Link>
                  </li>
                  <li className="mt-2">
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Privacy Policy
                    </Link>
                  </li>
                  <li className="mt-2">
                    <Link href="#" className="link hover:text-foreground transition-all duration-300">
                      Terms of Service
                    </Link>
                  </li>
                </ul>
              </div>
            </Container>
          </div>
        </div>
      </div>

      <Container delay={0.5} className="w-full relative mt-12 lg:mt-20">
        <div className="mt-8 md:flex md:items-center justify-center footer w-full">
          <p className="text-sm text-gray-500 mt-8 md:mt-0">&copy; {new Date().getFullYear()} Ruixen. Built for UI excellence.</p>
        </div>
      </Container>
    </footer>
  )
}

demo.tsx
import Footer_03 from '@/components/ui/ruixen-footer03'

export default function DemoOne() {
  return <Footer_03 />
}
```

Install NPM dependencies:

```bash
next, framer-motion
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
