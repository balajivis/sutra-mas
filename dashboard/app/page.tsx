import { StatusDashboard } from "@/components/StatusDashboard";

export default function Page() {
  const dashboardUrl = process.env.DASHBOARD_URL || "http://localhost:8050";
  return <StatusDashboard dashboardUrl={dashboardUrl} />;
}
