import "./style.css";
import { createDashboardApp } from "./dashboard";

const app = document.querySelector<HTMLDivElement>("#app");
const defaultBackendUrl = "http://localhost:8000";
const configuredBackendUrl = import.meta.env.VITE_BACKEND_URL ?? defaultBackendUrl;
const backendUrl = configuredBackendUrl.endsWith("/")
    ? configuredBackendUrl.slice(0, -1)
    : configuredBackendUrl;

if (!app) {
    throw new Error("Frontend app root was not found.");
}

const dashboard = createDashboardApp({
    appRoot: app,
    backendUrl,
});

void dashboard.loadJobs();
