import "./style.css";

type JobStatus = "paused" | "in_progress" | "completed" | "failed";
type ApprovalStatus = "pending" | "approved" | "rejected";
type JobDecision = "approve" | "reject";

type JobDetail = {
    job_id: string;
    workflow_type: string;
    current_state: string;
    status: JobStatus;
    state_version: number;
    resume_count: number;
    can_resume: boolean;
    approval_status: ApprovalStatus;
    can_approve: boolean;
    can_reject: boolean;
    last_error: string | null;
};

type JobActionResponse = {
    status: "ok";
    job: JobDetail;
};

class ApiError extends Error {
    readonly status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

const app = document.querySelector<HTMLDivElement>("#app");
const defaultBackendUrl = "http://localhost:8000";
const configuredBackendUrl = import.meta.env.VITE_BACKEND_URL ?? defaultBackendUrl;
const backendUrl = configuredBackendUrl.endsWith("/")
    ? configuredBackendUrl.slice(0, -1)
    : configuredBackendUrl;
const jobDashboardId = "job-dashboard";

const state = {
    jobs: [] as JobDetail[],
    isLoading: true,
    globalError: "",
    pendingDecisionByJobId: new Map<string, JobDecision>(),
    errorByJobId: new Map<string, string>(),
};

if (!app) {
    throw new Error("Frontend app root was not found.");
}

app.innerHTML = `
  <main class="page-shell">
    <section class="hero-card">
      <p class="eyebrow">PM Tool Workflow</p>
      <h1>Review jobs in the dashboard</h1>
      <p class="lede">
        This starter dashboard loads the sample <code>pm_tool_workflow</code>
        jobs from FastAPI and lets eligible items approve or reject directly in
        the browser using the same backend transition logic as the workflow
        itself.
      </p>
      <div class="hero-actions">
        <button type="button" data-refresh-dashboard>
          Refresh dashboard
        </button>
        <a href="${backendUrl}/docs" target="_blank" rel="noreferrer">
          Open FastAPI docs
        </a>
        <a href="${backendUrl}/health" target="_blank" rel="noreferrer">
          Check backend health
        </a>
      </div>
      <p class="backend-pill">
        Backend API: <code>${backendUrl}</code>
      </p>
    </section>

    <section class="dashboard-section" aria-labelledby="dashboard-heading">
      <div class="section-copy">
        <p class="card-label">Workflow queue</p>
        <h2 id="dashboard-heading">Sample PM workflow items</h2>
        <p>
          Pending requirements reviews are actionable here. Completed or
          already-approved jobs stay visible so the dashboard reflects the
          current workflow state instead of sending users elsewhere.
        </p>
      </div>
      <div id="${jobDashboardId}" class="job-grid" aria-live="polite"></div>
    </section>
  </main>
`;

const dashboardRoot = document.querySelector<HTMLDivElement>(`#${jobDashboardId}`);

if (!dashboardRoot) {
    throw new Error("Dashboard root was not found.");
}

function formatLabel(value: string): string {
    return value.split("_").join(" ");
}

function getJobSummary(job: JobDetail): string {
    if (job.can_approve || job.can_reject) {
        return "Awaiting PM approval. Approve or reject to continue.";
    }
    if (job.approval_status === "approved") {
        return "Approved. The workflow already moved forward.";
    }
    if (job.approval_status === "rejected") {
        return "Rejected. The workflow has stopped at the review step.";
    }
    return "Not currently actionable.";
}

function getActionLabel(jobId: string, decision: JobDecision): string {
    if (state.pendingDecisionByJobId.get(jobId) !== decision) {
        return decision === "approve" ? "Approve" : "Reject";
    }
    return decision === "approve" ? "Approving..." : "Rejecting...";
}

function renderJobs(): void {
    if (state.isLoading) {
        dashboardRoot.innerHTML = `
          <article class="job-card loading-card">
            <p class="card-label">Loading</p>
            <h3>Fetching workflow items</h3>
            <p>Reading the current PM workflow state from FastAPI.</p>
          </article>
        `;
        return;
    }

    if (state.globalError) {
        dashboardRoot.innerHTML = `
          <article class="job-card error-card">
            <p class="card-label">Dashboard error</p>
            <h3>Unable to load workflow items</h3>
            <p>${state.globalError}</p>
          </article>
        `;
        return;
    }

    if (state.jobs.length === 0) {
        dashboardRoot.innerHTML = `
          <article class="job-card empty-card">
            <p class="card-label">No items</p>
            <h3>No workflow items were returned</h3>
            <p>The sample backend is expected to expose at least one job.</p>
          </article>
        `;
        return;
    }

    const jobs = [...state.jobs].sort((left, right) => {
        const leftPriority = Number(left.can_approve || left.can_reject);
        const rightPriority = Number(right.can_approve || right.can_reject);
        if (leftPriority !== rightPriority) {
            return rightPriority - leftPriority;
        }
        return left.job_id.localeCompare(right.job_id);
    });

    dashboardRoot.innerHTML = jobs
        .map((job) => {
            const pendingDecision = state.pendingDecisionByJobId.get(job.job_id);
            const cardError = state.errorByJobId.get(job.job_id);
            const buttonsDisabled = Boolean(pendingDecision);

            return `
              <article class="job-card">
                <div class="job-card-header">
                  <div>
                    <p class="card-label">${job.workflow_type}</p>
                    <h3>${job.job_id}</h3>
                  </div>
                  <div class="pill-row">
                    <span class="pill status-pill status-${job.status}">
                      ${formatLabel(job.status)}
                    </span>
                    <span class="pill approval-pill approval-${job.approval_status}">
                      ${formatLabel(job.approval_status)}
                    </span>
                  </div>
                </div>

                <p class="job-summary">${getJobSummary(job)}</p>

                <dl class="job-metadata">
                  <div>
                    <dt>Current state</dt>
                    <dd>${formatLabel(job.current_state)}</dd>
                  </div>
                  <div>
                    <dt>State version</dt>
                    <dd>${job.state_version}</dd>
                  </div>
                  <div>
                    <dt>Resume count</dt>
                    <dd>${job.resume_count}</dd>
                  </div>
                </dl>

                ${
                    job.last_error
                        ? `<p class="inline-note">Last update: ${job.last_error}</p>`
                        : ""
                }
                ${
                    cardError
                        ? `<p class="inline-error">${cardError}</p>`
                        : ""
                }

                <div class="job-actions">
                  <button
                    type="button"
                    class="action-button approve-button"
                    data-job-id="${job.job_id}"
                    data-decision="approve"
                    ${!job.can_approve || buttonsDisabled ? "disabled" : ""}
                  >
                    ${getActionLabel(job.job_id, "approve")}
                  </button>
                  <button
                    type="button"
                    class="action-button reject-button"
                    data-job-id="${job.job_id}"
                    data-decision="reject"
                    ${!job.can_reject || buttonsDisabled ? "disabled" : ""}
                  >
                    ${getActionLabel(job.job_id, "reject")}
                  </button>
                </div>
              </article>
            `;
        })
        .join("");
}

async function parseError(response: Response): Promise<string> {
    try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string" && payload.detail) {
            return payload.detail;
        }
    } catch {
        return `Request failed with status ${response.status}`;
    }
    return `Request failed with status ${response.status}`;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, init);
    if (!response.ok) {
        throw new ApiError(await parseError(response), response.status);
    }
    return (await response.json()) as T;
}

async function fetchJobs(): Promise<JobDetail[]> {
    return await fetchJson<JobDetail[]>(`${backendUrl}/jobs`);
}

function getErrorMessage(error: unknown): string {
    if (error instanceof ApiError) {
        return error.message;
    }
    if (error instanceof Error && error.message) {
        return error.message;
    }
    return "The dashboard request failed.";
}

async function loadJobs(): Promise<void> {
    state.isLoading = true;
    state.globalError = "";
    state.errorByJobId.clear();
    renderJobs();

    try {
        state.jobs = await fetchJobs();
    } catch (error) {
        state.globalError = getErrorMessage(error);
    } finally {
        state.isLoading = false;
        renderJobs();
    }
}

async function submitReview(jobId: string, decision: JobDecision): Promise<void> {
    state.pendingDecisionByJobId.set(jobId, decision);
    state.errorByJobId.delete(jobId);
    renderJobs();

    try {
        const response = await fetchJson<JobActionResponse>(
            `${backendUrl}/jobs/${encodeURIComponent(jobId)}/review`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ decision }),
            },
        );

        state.jobs = state.jobs.map((job) =>
            job.job_id === jobId ? response.job : job,
        );
    } catch (error) {
        try {
            state.jobs = await fetchJobs();
        } catch (refreshError) {
            state.globalError = getErrorMessage(refreshError);
        }
        state.errorByJobId.set(
            jobId,
            `${getErrorMessage(error)}. The dashboard was refreshed.`,
        );
    } finally {
        state.pendingDecisionByJobId.delete(jobId);
        renderJobs();
    }
}

app.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }

    if (target.matches("[data-refresh-dashboard]")) {
        void loadJobs();
        return;
    }

    if (!(target instanceof HTMLButtonElement)) {
        return;
    }

    const jobId = target.dataset.jobId;
    const decision = target.dataset.decision as JobDecision | undefined;
    if (!jobId || !decision) {
        return;
    }
    void submitReview(jobId, decision);
});

renderJobs();
void loadJobs();
