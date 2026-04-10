import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getWebSessionKey } from '@/api'
import type { Course, Streak, Me } from '@/types'
import DashboardMetricCard from '@/components/ui/dashboard-metric-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ShaderAnimation } from '@/components/ui/shader-animation'
import { Flame, BookOpen, Clock, CheckCircle, Plus, ChevronRight } from 'lucide-react'

export default function Dashboard() {
  const [me, setMe] = useState<Me | null>(null)
  const [streak, setStreak] = useState<Streak | null>(null)
  const [courses, setCourses] = useState<Course[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    if (!getWebSessionKey()) {
      setErr('Open this app using the link from the Telegram bot (menu → Web app or /web).')
      setLoading(false)
      return
    }
    try {
      const [meData, streakData, coursesData] = await Promise.all([api.get<Me>('/users/me'), api.get<Streak>('/streak'), api.get<Course[]>('/web-courses')])
      setMe(meData)
      setStreak(streakData)
      setCourses(coursesData)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground animate-pulse">Loading...</p>
      </div>
    )
  }

  if (err) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-destructive text-center max-w-md">{err}</p>
      </div>
    )
  }

  const completedToday = courses.reduce((sum, c) => sum + c.completed_lessons, 0)
  const totalMinutes = streak?.today_completed_minutes ?? 0

  return (
    <div>
      <div className="relative mb-4 overflow-hidden rounded-xl border border-border/50 h-80">
        <ShaderAnimation />
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
          <h1 className="text-4xl font-extrabold tracking-tight text-white drop-shadow-lg">{me?.name ? `Hey, ${me.name}!` : 'Welcome back!'}</h1>
          <p className="text-white/60 mt-2 text-lg">Ready to learn something new?</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <DashboardMetricCard title="Current Streak" value={`${streak?.streak_current ?? 0}`} icon={Flame} trendChange={`Best: ${streak?.streak_best ?? 0}`} trendType="neutral" />
        <DashboardMetricCard title="Courses" value={`${courses.length}`} icon={BookOpen} trendType="neutral" />
        <DashboardMetricCard title="Lessons Done" value={`${completedToday}`} icon={CheckCircle} trendType="up" />
        <DashboardMetricCard
          title="Study Today"
          value={`${totalMinutes}m`}
          icon={Clock}
          trendChange={streak ? `${Math.round(streak.progress_ratio * 100)}% of goal` : undefined}
          trendType={streak && streak.progress_ratio >= 1 ? 'up' : streak && streak.progress_ratio > 0 ? 'neutral' : 'down'}
        />
      </div>

      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-semibold">Your Courses</h2>
        <Button onClick={() => navigate('/create-course')}>
          <Plus className="h-4 w-4 mr-2" />
          New Course
        </Button>
      </div>

      {courses.length === 0 ? (
        <Card className="bg-card/60 backdrop-blur-sm border-border/50">
          <CardContent className="py-12 text-center">
            <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">No courses yet. Create one to start learning!</p>
            <Button onClick={() => navigate('/create-course')}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Course
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map((course) => {
            const progress = course.total_lessons > 0 ? Math.round((course.completed_lessons / course.total_lessons) * 100) : 0
            return (
              <Card key={course.id} className="bg-card/60 backdrop-blur-sm border-border/50 hover:bg-card/80 hover:border-primary/30 transition-all h-full rounded-xl">
                <Link to={`/course/${course.id}`} className="block">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-base min-w-0 truncate">{course.name}</CardTitle>
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </div>
                    {course.description && <p className="text-sm text-muted-foreground line-clamp-2">{course.description}</p>}
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">
                        {course.completed_lessons}/{course.total_lessons} lessons
                      </span>
                      <span className="font-medium text-primary">{progress}%</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-secondary">{course.duration_label}</span>
                      {course.status === 'generating' && <span className="text-xs text-warning px-2 py-0.5 rounded-full bg-warning/10">Generating...</span>}
                    </div>
                  </CardContent>
                </Link>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
