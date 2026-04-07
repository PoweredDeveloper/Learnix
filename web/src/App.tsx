import AdminDashboard from "./AdminDashboard";
import UserDashboard from "./UserDashboard";

export default function App() {
  const path = window.location.pathname || "/";
  if (path === "/admin" || path.startsWith("/admin/")) {
    return <AdminDashboard />;
  }
  return <UserDashboard />;
}
