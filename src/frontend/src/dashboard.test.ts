// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createDashboardApp } from "./dashboard";

function jsonResponse(body: unknown, status = 200): Response {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    } as Response;
}

function flushDashboard(): Promise<void> {
    return new Promise((resolve) => {
        setTimeout(resolve, 0);
    });
}

describe("createDashboardApp", () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="app"></div>';
    });

    it("submits approve decisions and rerenders from refreshed job details", async () => {
        const reviewJob = {
            job_id: "job-review-321",
            workflow_type: "pm_tool_workflow",
            current_state: "awaiting_review",
            status: "paused",
            state_version: 6,
            resume_count: 1,
            can_resume: false,
            last_error: "Pending PM review",
        } as const;
        const pausedJob = {
            job_id: "job-paused-123",
            workflow_type: "pm_tool_workflow",
            current_state: "awaiting_requirements",
            status: "paused",
            state_version: 3,
            resume_count: 0,
            can_resume: true,
            last_error: "Waiting for product requirements",
        } as const;
        const runningJob = {
            job_id: "job-running-456",
            workflow_type: "pm_tool_workflow",
            current_state: "drafting_pr",
            status: "in_progress",
            state_version: 5,
            resume_count: 1,
            can_resume: true,
            last_error: null,
        } as const;
        const completedJob = {
            job_id: "job-completed-789",
            workflow_type: "pm_tool_workflow",
            current_state: "published_summary",
            status: "completed",
            state_version: 8,
            resume_count: 0,
            can_resume: false,
            last_error: null,
        } as const;
        const approvedReviewJob = {
            ...reviewJob,
            current_state: "published_summary",
            status: "completed",
            state_version: 7,
            last_error: null,
        } as const;
        const queuedResponses = [
            jsonResponse(reviewJob),
            jsonResponse(pausedJob),
            jsonResponse(runningJob),
            jsonResponse(completedJob),
            jsonResponse({ status: "ok", job: approvedReviewJob }),
            jsonResponse(approvedReviewJob),
            jsonResponse(pausedJob),
            jsonResponse(runningJob),
            jsonResponse(completedJob),
        ];
        const fetchImpl = vi.fn(async () => {
            const response = queuedResponses.shift();
            if (!response) {
                throw new Error("Unexpected fetch call");
            }
            return response;
        }) as typeof fetch;
        const appRoot = document.querySelector<HTMLDivElement>("#app");

        if (!appRoot) {
            throw new Error("Test app root was not created.");
        }

        const dashboard = createDashboardApp({
            appRoot,
            backendUrl: "http://localhost:8000",
            fetchImpl,
        });

        await dashboard.loadJobs();

        const approveButtonBefore = appRoot.querySelector<HTMLButtonElement>(
            '[data-job-id="job-review-321"][data-review-action="approve"]',
        );

        expect(approveButtonBefore?.disabled).toBe(false);

        approveButtonBefore?.click();
        await flushDashboard();

        expect(fetchImpl).toHaveBeenCalledWith(
            "http://localhost:8000/jobs/job-review-321/review",
            expect.objectContaining({
                body: JSON.stringify({ decision: "approve" }),
                method: "POST",
            }),
        );

        const approveButtonAfter = appRoot.querySelector<HTMLButtonElement>(
            '[data-job-id="job-review-321"][data-review-action="approve"]',
        );
        const reviewStatus = appRoot.querySelector<HTMLElement>(
            '[data-job-card="job-review-321"] .status-pill',
        );

        expect(approveButtonAfter?.disabled).toBe(true);
        expect(reviewStatus?.textContent).toContain("completed");
        expect(appRoot.textContent).toContain("Review is already decided");
    });

    it("keeps non-reviewable jobs disabled", async () => {
        const queuedResponses = [
            jsonResponse({
                job_id: "job-review-321",
                workflow_type: "pm_tool_workflow",
                current_state: "awaiting_review",
                status: "paused",
                state_version: 6,
                resume_count: 1,
                can_resume: false,
                last_error: "Pending PM review",
            }),
            jsonResponse({
                job_id: "job-paused-123",
                workflow_type: "pm_tool_workflow",
                current_state: "awaiting_requirements",
                status: "paused",
                state_version: 3,
                resume_count: 0,
                can_resume: true,
                last_error: "Waiting for product requirements",
            }),
            jsonResponse({
                job_id: "job-running-456",
                workflow_type: "pm_tool_workflow",
                current_state: "drafting_pr",
                status: "in_progress",
                state_version: 5,
                resume_count: 1,
                can_resume: true,
                last_error: null,
            }),
            jsonResponse({
                job_id: "job-completed-789",
                workflow_type: "pm_tool_workflow",
                current_state: "published_summary",
                status: "completed",
                state_version: 8,
                resume_count: 0,
                can_resume: false,
                last_error: null,
            }),
        ];
        const fetchImpl = vi.fn(async () => {
            const response = queuedResponses.shift();
            if (!response) {
                throw new Error("Unexpected fetch call");
            }
            return response;
        }) as typeof fetch;
        const appRoot = document.querySelector<HTMLDivElement>("#app");

        if (!appRoot) {
            throw new Error("Test app root was not created.");
        }

        const dashboard = createDashboardApp({
            appRoot,
            backendUrl: "http://localhost:8000",
            fetchImpl,
        });

        await dashboard.loadJobs();

        const pausedApproveButton = appRoot.querySelector<HTMLButtonElement>(
            '[data-job-id="job-paused-123"][data-review-action="approve"]',
        );
        const runningRejectButton = appRoot.querySelector<HTMLButtonElement>(
            '[data-job-id="job-running-456"][data-review-action="reject"]',
        );
        const completedApproveButton = appRoot.querySelector<HTMLButtonElement>(
            '[data-job-id="job-completed-789"][data-review-action="approve"]',
        );

        expect(pausedApproveButton?.disabled).toBe(true);
        expect(runningRejectButton?.disabled).toBe(true);
        expect(completedApproveButton?.disabled).toBe(true);
    });
});
