"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createSession,
  destroySession,
  requireSession,
  signInWithOdooCredentials,
} from "@/lib/auth";
import {
  createWorkspaceProject,
  createWorkspaceTask,
  createWorkspaceTaskReport,
  markWorkspaceTaskDone,
  returnWorkspaceTaskForChanges,
  submitWorkspaceTaskForReview,
} from "@/lib/workspace";

function getConnectionOverrides() {
  return requireSession().then((session) => ({
    login: session.login,
    password: session.password,
  }));
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Үйлдлийг гүйцэтгэх үед алдаа гарлаа.";
}

function redirectWithMessage(
  path: string,
  kind: "error" | "notice",
  message: string,
  hash = "",
) {
  const separator = path.includes("?") ? "&" : "?";
  redirect(`${path}${separator}${kind}=${encodeURIComponent(message)}${hash}`);
}

export async function loginAction(formData: FormData) {
  const login = String(formData.get("login") ?? "").trim();
  const password = String(formData.get("password") ?? "").trim();

  if (!login || !password) {
    redirect("/login?error=missing");
  }

  try {
    const session = await signInWithOdooCredentials(login, password);
    if (!session) {
      redirect("/login?error=invalid");
    }

    await createSession(session);
  } catch {
    redirect("/login?error=connection");
  }

  redirect("/");
}

export async function logoutAction() {
  await destroySession();
  redirect("/login");
}

export async function createProjectAction(formData: FormData) {
  const name = String(formData.get("name") ?? "").trim();
  const managerIdRaw = String(formData.get("manager_id") ?? "").trim();
  const departmentIdRaw = String(formData.get("department_id") ?? "").trim();
  const startDate = String(formData.get("start_date") ?? "").trim();
  const deadline = String(formData.get("deadline") ?? "").trim();

  if (!name || !departmentIdRaw) {
    redirectWithMessage(
      "/projects/new",
      "error",
      "Төслийн нэр болон алба нэгжээ заавал сонгоно уу.",
    );
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    const projectId = await createWorkspaceProject(
      {
        name,
        managerId: managerIdRaw ? Number(managerIdRaw) : null,
        departmentId: departmentIdRaw ? Number(departmentIdRaw) : null,
        startDate: startDate || undefined,
        deadline: deadline || undefined,
      },
      connectionOverrides,
    );

    revalidatePath("/");
    revalidatePath("/projects/new");
    redirect(`/projects/${projectId}?notice=${encodeURIComponent("Төсөл амжилттай үүслээ.")}`);
  } catch (error) {
    redirectWithMessage("/projects/new", "error", getErrorMessage(error));
  }
}

export async function createTaskAction(formData: FormData) {
  const projectId = Number(String(formData.get("project_id") ?? ""));
  const name = String(formData.get("name") ?? "").trim();
  const teamLeaderIdRaw = String(formData.get("team_leader_id") ?? "").trim();
  const deadline = String(formData.get("deadline") ?? "").trim();
  const measurementUnit = String(formData.get("measurement_unit") ?? "").trim();
  const plannedQuantityRaw = String(formData.get("planned_quantity") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();

  if (!projectId || !name) {
    redirectWithMessage(
      `/projects/${projectId || ""}`,
      "error",
      "Task үүсгэхэд шаардлагатай талбар дутуу байна.",
    );
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    const taskId = await createWorkspaceTask(
      {
        projectId,
        name,
        teamLeaderId: teamLeaderIdRaw ? Number(teamLeaderIdRaw) : null,
        deadline: deadline || undefined,
        measurementUnit: measurementUnit || undefined,
        plannedQuantity: plannedQuantityRaw ? Number(plannedQuantityRaw) : null,
        description: description || undefined,
      },
      connectionOverrides,
    );

    revalidatePath("/");
    revalidatePath(`/projects/${projectId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Шинэ task амжилттай үүслээ.")}`);
  } catch (error) {
    redirectWithMessage(`/projects/${projectId}`, "error", getErrorMessage(error));
  }
}

export async function createTaskReportAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));
  const reportText = String(formData.get("report_text") ?? "").trim();
  const quantityRaw = String(formData.get("reported_quantity") ?? "").trim();
  const reportedQuantity = quantityRaw ? Number(quantityRaw) : 0;

  if (!taskId || !reportText) {
    redirectWithMessage(
      `/tasks/${taskId || ""}`,
      "error",
      "Тайлангийн текстээ оруулна уу.",
      "#report-form",
    );
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await createWorkspaceTaskReport(
      {
        taskId,
        reportText,
        reportedQuantity,
      },
      connectionOverrides,
    );

    revalidatePath("/");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Тайлан амжилттай хадгалагдлаа.")}`);
  } catch (error) {
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error), "#report-form");
  }
}

export async function submitTaskForReviewAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));

  try {
    const connectionOverrides = await getConnectionOverrides();
    await submitWorkspaceTaskForReview(taskId, connectionOverrides);
    revalidatePath("/");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажлыг шалгалтад илгээлээ.")}`);
  } catch (error) {
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error));
  }
}

export async function markTaskDoneAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));

  try {
    const connectionOverrides = await getConnectionOverrides();
    await markWorkspaceTaskDone(taskId, connectionOverrides);
    revalidatePath("/");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажил дууссан төлөвт орлоо.")}`);
  } catch (error) {
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error));
  }
}

export async function returnTaskForChangesAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));
  const reason = String(formData.get("return_reason") ?? "").trim();

  if (!reason) {
    redirectWithMessage(`/tasks/${taskId}`, "error", "Буцаах шалтгаанаа бичнэ үү.");
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await returnWorkspaceTaskForChanges(taskId, reason, connectionOverrides);
    revalidatePath("/");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажлыг засвар нэхэж буцаалаа.")}`);
  } catch (error) {
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error));
  }
}
