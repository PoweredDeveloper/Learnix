import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import CreateCourse from "@/pages/CreateCourse";
import Settings from "@/pages/Settings";
import CourseView from "@/pages/CourseView";
import LessonView from "@/pages/LessonView";
import AdminDashboard from "@/AdminDashboard";
import Layout from "@/components/Layout";
import { useEffect } from "react";
import { captureKeyFromQuery } from "@/api";

export default function App() {
  useEffect(() => {
    captureKeyFromQuery();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/create-course" element={<CreateCourse />} />
          <Route path="/course/:courseId" element={<CourseView />} />
          <Route
            path="/course/:courseId/lesson/:lessonId"
            element={<LessonView />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
