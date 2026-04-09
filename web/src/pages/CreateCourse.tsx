import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Switch, SwitchControl } from "@/components/ui/inline-radio";
import { ShiningText } from "@/components/ui/shining-text";
import { ArrowLeft, Sparkles } from "lucide-react";

const DURATION_OPTIONS = [
  { value: "2h", label: "2 hours" },
  { value: "12h", label: "12 hours" },
  { value: "1d", label: "1 day" },
  { value: "3d", label: "3 days" },
  { value: "1w", label: "1 week" },
  { value: "1month", label: "1 month" },
];

export default function CreateCourse() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("1w");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!description.trim()) {
      setError("Please describe what you want to learn.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<{ course: { id: string } }>(
        "/web-courses/create",
        {
          name: name.trim() || description.trim().slice(0, 60),
          description: description.trim(),
          duration_label: duration,
        },
      );
      const courseId = result.course?.id ?? (result as any).id;
      navigate(`/course/${courseId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create course");
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Sparkles className="h-12 w-12 text-primary animate-pulse" />
        <ShiningText className="text-xl font-semibold">
          Generating your course...
        </ShiningText>
        <p className="text-muted-foreground text-sm max-w-md text-center">
          AI is designing your personalized curriculum with theory, practice, and
          exams. This may take a minute.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </button>

      <Card className="bg-card/60 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>Create a New Course</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">
              What do you want to learn?
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Integral calculus for my midterm exam, focusing on substitution and integration by parts"
              className="min-h-[100px]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Course name (optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Auto-generated from description"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              How long do you want to study?
            </label>
            <Switch
              name="duration"
              size="medium"
              defaultValue={duration}
              onChange={setDuration}
            >
              {DURATION_OPTIONS.map((opt) => (
                <SwitchControl
                  key={opt.value}
                  value={opt.value}
                  label={opt.label}
                />
              ))}
            </Switch>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button onClick={handleCreate} size="lg" className="w-full">
            <Sparkles className="h-4 w-4 mr-2" />
            Generate Course with AI
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
