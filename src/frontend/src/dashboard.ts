export type JobStatus = "paused" | "in_progress" | "completed" | "failed";
export type ReviewDecision = "approve" | "reject";

export interface JobDetail {
    job_id: string;
    workflow_type: string;
    current_state: string;
    status: JobStatus;
    state_version: number;
    resume_count: number;
    can_resume: boolean;
    last_error: string | null;
}

interface ReviewJobResponse {
    status: "ok";
    job: JobDetail;
}

interface DashboardOptions {
    appRoot: HTMLElement;
    backendUrl: string;
    fetchImpl?: typeof fetch;
    jobIds?: readonly string[];
}

interface DashboardState {
    errorMessage: string | null;
    isLoading: boolean;
    jobs: JobDetail[];
    pendingDecision: {
        decision: ReviewDecision;
        jobId: string;
    } | null;
}

interface DashboardApp {
    loadJobs: () => Promise<void>;
}

const defaultJobIds = [
    "job-review-321",
    "job-paused-123",
    "job-running-456",
    "job-completed-789",
] as const;

function normalizeBackendUrl(backendUrl: string): string {
    return backendUrl.endsWith("/") ? backendUrl.slice(0, -1) : backendUrl;
}

export function isReviewableJob(job: JobDetail): boolean {
    return job.status === "paused" && job.current_state === "awaiting_review";
}

function escapeHtml(value: string): string {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatStateLabel(value: string): string {
    return value.replaceAll("_", " ");
}

function describeReviewState(job: JobDetail): string {
    if (isReviewableJob(job)) {
        return "Approve or reject this review directly from the dashboard.";
    }

    if (job.current_state === "changes_requested") {
        return "Review is already rejected. Resume the workflow to draft another revision.";
    }

    if (job.status === "completed") {
        return "Review is already decided and can no longer be changed.";
    }

    return "Review actions unlock when the workflow reaches awaiting review.";
}

function getErrorMessage(error: unknown): string {
    if (error instanceof Error) {
        return error.message;
    }
    return "The dashboard could not reach the backend.";
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
    const data = (await response.json()) as T;
    if (!response.ok) {
        const detail =
            typeof data === "object" &&
            data !== null &&
            "detail" in data &&
            typeof data.detail === "string"
                ? data.detail
                : `Request failed with status ${response.status}`;
        throw new Error(detail);
    }
    return data;
}

async function fetchJobDetail(
    fetchImpl: typeof fetch,
    backendUrl: string,
    jobId: string,
): Promise<JobDetail> {
    const response = await fetchImpl(`${backendUrl}/jobs/${jobId}/detail`);
    return parseJsonResponse<JobDetail>(response);
}

async function submitReviewDecision(
    fetchImpl: typeof fetch,
    backendUrl: string,
    jobId: string,
    decision: ReviewDecision,
): Promise<JobDetail> {
    const response = await fetchImpl(`${backendUrl}/jobs/${jobId}/review`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ decision }),
    });
    const result = await parseJsonResponse<ReviewJobResponse>(response);
    return result.job;
}

function renderJobCard(
    job: JobDetail,
    pendingDecision: DashboardState["pendingDecision"],
): string {
    const reviewable = isReviewableJob(job);
    const isSubmitting = pendingDecision?.jobId === job.job_id;
    const stateLabel = escapeHtml(formatStateLabel(job.current_state));
    const lastError = job.last_error
        ? `<p class="job-meta"><strong>Note:</strong> ${escapeHtml(job.last_error)}</p>`
        : "";

    return `
      <article class="job-card" data-job-card="${escapeHtml(job.job_id)}">
        <div class="job-card-header">
          <div>
            <p class="card-label">${escapeHtml(job.workflow_type)}</p>
            <h2>${escapeHtml(job.job_id)}</h2>
          </div>
          <span class="status-pill status-pill--${escapeHtml(job.status)}">${escapeHtml(job.status)}</span>
        </div>
        <dl class="job-metadata">
          <div>
            <dt>State</dt>
            <dd>${stateLabel}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>${job.state_version}</dd>
          </div>
          <div>
            <dt>Resume count</dt>
            <dd>${job.resume_count}</dd>
          </div>
          <div>
            <dt>Can resume</dt>
            <dd>${job.can_resume ? "Yes" : "No"}</dd>
          </div>
        </dl>
        ${lastError}
        <p class="job-helper">${escapeHtml(describeReviewState(job))}</p>
        <div class="review-actions">
          <button
            type="button"
            class="review-button review-button--approve"
            data-review-action="approve"
            data-job-id="${escapeHtml(job.job_id)}"
            ${reviewable && !isSubmitting ? "" : "disabled"}
          >
            ${isSubmitting && pendingDecision?.decision === "approve" ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            class="review-button review-button--reject"
            data-review-action="reject"
            data-job-id="${escapeHtml(job.job_id)}"
            ${reviewable && !isSubmitting ? "" : "disabled"}
          >
            ${isSubmitting && pendingDecision?.decision === "reject" ? "Rejecting..." : "Reject"}
          </button>
        </div>
      </article>
    `;
}

function renderDashboard(
    appRoot: HTMLElement,
    backendUrl: string,
    state: DashboardState,
): void {
    const jobCards = state.jobs.map((job) => renderJobCard(job, state.pendingDecision)).join("");
    const loadingMessage = state.isLoading
        ? '<p class="surface-banner" aria-live="polite">Loading workflow items...</p>'
        : "";
    const errorMessage = state.errorMessage
        ? `<p class="surface-banner surface-banner--error" aria-live="polite">${escapeHtml(state.errorMessage)}</p>`
        : "";
    const emptyState =
        !state.isLoading && state.jobs.length === 0
            ? '<p class="surface-banner">No workflow items were returned by the backend.</p>'
            : "";

    appRoot.innerHTML = `
      <main class="page-shell">
        <section class="hero-card">
          <p class="eyebrow">PM Tool Dashboard</p>
          <h1>Review work without leaving the dashboard</h1>
          <p class="lede">
            This starter page now calls the same backend review mutation for approve and reject decisions.
            Reviewable jobs stay actionable here, while already-decided or non-reviewable jobs remain disabled.
          </p>
          <div class="hero-actions">
            <a href="${backendUrl}/" target="_blank" rel="noreferrer">
              Open FastAPI sample
            </a>
            <a href="${backendUrl}/health" target="_blank" rel="noreferrer">
              Check backend health
            </a>
          </div>
        </section>

        <section class="dashboard-surface" aria-label="Workflow review queue">
          <div class="section-header">
            <div>
              <p class="eyebrow">Review Queue</p>
              <h2>Approve or reject PM workflow jobs</h2>
            </div>
            <p class="section-note">The page reloads each job from the backend after a decision is submitted.</p>
          </div>
          ${loadingMessage}
          ${errorMessage}
          ${emptyState}
          <div class="job-grid">
            ${jobCards}
          </div>
        </section>
      </main>
    `;
}

export function createDashboardApp({
    appRoot,
    backendUrl,
    fetchImpl = fetch,
    jobIds = defaultJobIds,
}: DashboardOptions): DashboardApp {
    const normalizedBackendUrl = normalizeBackendUrl(backendUrl);
    const state: DashboardState = {
        errorMessage: null,
        isLoading: false,
        jobs: [],
        pendingDecision: null,
    };

    const render = (): void => {
        renderDashboard(appRoot, normalizedBackendUrl, state);
        for (const button of appRoot.querySelectorAll<HTMLButtonElement>("[data-review-action]")) {
            button.addEventListener("click", () => {
                const jobId = button.dataset.jobId;
                const decision = button.dataset.reviewAction as ReviewDecision | undefined;
                if (!jobId || !decision) {
                    return;
                }

                state.pendingDecision = { decision, jobId };
                state.errorMessage = null;
                render();
                void submitReviewDecision(fetchImpl, normalizedBackendUrl, jobId, decision)
                    .then(async () => {
                        await loadJobs();
                    })
                    .catch((error: unknown) => {
                        state.errorMessage = getErrorMessage(error);
                    })
                    .finally(() => {
                        state.pendingDecision = null;
                        render();
                    });
            });
        }
    };

    const loadJobs = async (): Promise<void> => {
        state.isLoading = true;
        state.errorMessage = null;
        render();
        try {
            state.jobs = await Promise.all(
                jobIds.map((jobId) =>
                    fetchJobDetail(fetchImpl, normalizedBackendUrl, jobId),
                ),
            );
        } catch (error: unknown) {
            state.errorMessage = getErrorMessage(error);
        } finally {
            state.isLoading = false;
            render();
        }
    };

    render();

    return {
        loadJobs,
    };
}
