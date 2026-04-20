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
  createFieldStopIssue,
  markFieldStopArrived,
  markFieldStopDone,
  markFieldStopSkipped,
  saveFieldStopNote,
  startFieldShift,
  submitFieldShift,
  uploadFieldStopProof,
} from "@/lib/field-ops";
import {
  createGarbageWorkspaceProject,
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

function isRedirectException(error: unknown) {
  return Boolean(
    error &&
      typeof error === "object" &&
      "digest" in error &&
      typeof (error as { digest?: unknown }).digest === "string" &&
      String((error as { digest: string }).digest).startsWith("NEXT_REDIRECT"),
  );
}

function rethrowIfRedirectError(error: unknown) {
  if (isRedirectException(error)) {
    throw error;
  }
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

function getNumberValue(formData: FormData, key: string) {
  return Number(String(formData.get(key) ?? ""));
}

function revalidateFieldPaths(taskId?: number) {
  revalidatePath("/");
  revalidatePath("/projects");
  revalidatePath("/review");
  revalidatePath("/reports");
  revalidatePath("/quality");
  revalidatePath("/field");
  if (taskId) {
    revalidatePath(`/tasks/${taskId}`);
  }
}

function buildFieldPath(taskId: number, stopLineId?: number) {
  return {
    path: `/field?taskId=${taskId}`,
    hash: stopLineId ? `#stop-${stopLineId}` : "",
  };
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
  const operationUnit = String(formData.get("operation_unit") ?? "").trim();
  const trackQuantity = String(formData.get("track_quantity") ?? "").trim() === "1";
  const plannedQuantityRaw = String(formData.get("planned_quantity") ?? "").trim();
  const measurementUnit = String(formData.get("measurement_unit") ?? "").trim();
  const startDate = String(formData.get("start_date") ?? "").trim();
  const deadline = String(formData.get("deadline") ?? "").trim();
  const garbageVehicleIdRaw = String(formData.get("garbage_vehicle_id") ?? "").trim();
  const garbageRouteIdRaw = String(formData.get("garbage_route_id") ?? "").trim();

  if (operationUnit === "garbage_transport") {
    if (!departmentIdRaw || !garbageVehicleIdRaw || !garbageRouteIdRaw || !startDate) {
      redirectWithMessage(
        "/projects/new",
        "error",
        "Хог тээвэрлэлтийн ажилд машин, маршрут, огноо гурвыг заавал сонгоно уу.",
      );
    }

    try {
      const connectionOverrides = await getConnectionOverrides();
      const result = await createGarbageWorkspaceProject(
        {
          vehicleId: Number(garbageVehicleIdRaw),
          routeId: Number(garbageRouteIdRaw),
          shiftDate: startDate,
        },
        connectionOverrides,
      );

      revalidatePath("/");
      revalidatePath("/projects");
      revalidatePath("/tasks");
      revalidatePath("/review");
      revalidatePath("/reports");
      revalidatePath("/projects/new");
      revalidatePath(`/projects/${result.project_id}`);
      redirect(
        `/projects/${result.project_id}?notice=${encodeURIComponent(
          result.message || "Хог тээвэрлэлтийн ажил амжилттай үүслээ.",
        )}`,
      );
    } catch (error) {
      rethrowIfRedirectError(error);
      redirectWithMessage("/projects/new", "error", getErrorMessage(error));
    }
  }

  if (!name || !departmentIdRaw) {
    redirectWithMessage(
      "/projects/new",
      "error",
      "Төслийн нэр болон алба нэгжээ заавал сонгоно уу.",
    );
  }

  if (trackQuantity) {
    const plannedQuantity = Number(plannedQuantityRaw);
    if (!plannedQuantityRaw || Number.isNaN(plannedQuantity) || plannedQuantity <= 0) {
      redirectWithMessage(
        "/projects/new",
        "error",
        "Checkbox идэвхтэй бол төлөвлөсөн хэмжээг 0-ээс их тоогоор оруулна уу.",
      );
    }

    if (!measurementUnit) {
      redirectWithMessage(
        "/projects/new",
        "error",
        "Checkbox идэвхтэй бол хэмжих нэгжээ заавал оруулна уу.",
      );
    }
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    const projectId = await createWorkspaceProject(
      {
        name,
        managerId: managerIdRaw ? Number(managerIdRaw) : null,
        departmentId: departmentIdRaw ? Number(departmentIdRaw) : null,
        trackQuantity,
        plannedQuantity:
          trackQuantity && plannedQuantityRaw ? Number(plannedQuantityRaw) : null,
        measurementUnit: trackQuantity ? measurementUnit : undefined,
        startDate: startDate || undefined,
        deadline: deadline || undefined,
      },
      connectionOverrides,
    );

    revalidatePath("/");
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath("/projects/new");
    redirect(`/projects/${projectId}?notice=${encodeURIComponent("Төсөл амжилттай үүслээ.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
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
      "Ажил үүсгэхэд шаардлагатай талбар дутуу байна.",
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
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath(`/projects/${projectId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Шинэ ажил амжилттай үүслээ.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
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
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Тайлан амжилттай хадгалагдлаа.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error), "#report-form");
  }
}

export async function submitTaskForReviewAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));

  try {
    const connectionOverrides = await getConnectionOverrides();
    await submitWorkspaceTaskForReview(taskId, connectionOverrides);
    revalidatePath("/");
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажлыг шалгалтад илгээлээ.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error));
  }
}

export async function markTaskDoneAction(formData: FormData) {
  const taskId = Number(String(formData.get("task_id") ?? ""));

  try {
    const connectionOverrides = await getConnectionOverrides();
    await markWorkspaceTaskDone(taskId, connectionOverrides);
    revalidatePath("/");
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажил дууссан төлөвт орлоо.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
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
    revalidatePath("/projects");
    revalidatePath("/review");
    revalidatePath("/reports");
    revalidatePath(`/tasks/${taskId}`);
    redirect(`/tasks/${taskId}?notice=${encodeURIComponent("Ажлыг засвар нэхэж буцаалаа.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(`/tasks/${taskId}`, "error", getErrorMessage(error));
  }
}

export async function startFieldShiftAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const { path } = buildFieldPath(taskId);

  try {
    const connectionOverrides = await getConnectionOverrides();
    await startFieldShift(taskId, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Ээлжийг эхлүүллээ.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error));
  }
}

export async function submitFieldShiftAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const summary = String(formData.get("summary") ?? "").trim();
  const { path } = buildFieldPath(taskId);

  if (!summary) {
    redirectWithMessage(path, "error", "Ээлжийн тайлангаа бөглөнө үү.");
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await submitFieldShift(taskId, summary, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Ээлжийг шалгалтад илгээлээ.")}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error));
  }
}

export async function saveFieldStopNoteAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const note = String(formData.get("note") ?? "");
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  try {
    const connectionOverrides = await getConnectionOverrides();
    await saveFieldStopNote(stopLineId, note, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Тэмдэглэлийг хадгаллаа.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}

export async function markFieldStopArrivedAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  try {
    const connectionOverrides = await getConnectionOverrides();
    await markFieldStopArrived(stopLineId, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Цэг дээр ирснийг тэмдэглэлээ.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}

export async function markFieldStopDoneAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  try {
    const connectionOverrides = await getConnectionOverrides();
    await markFieldStopDone(stopLineId, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Цэгийг дууссан төлөвт орууллаа.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}

export async function markFieldStopSkippedAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const skipReason = String(formData.get("skip_reason") ?? "").trim();
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  if (!skipReason) {
    redirectWithMessage(path, "error", "Алгассан шалтгаанаа оруулна уу.", hash);
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await markFieldStopSkipped(stopLineId, skipReason, connectionOverrides);
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Цэгийг алгассан төлөвт орууллаа.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}

export async function uploadFieldStopProofAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const proofType = String(formData.get("proof_type") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const latitudeRaw = String(formData.get("latitude") ?? "").trim();
  const longitudeRaw = String(formData.get("longitude") ?? "").trim();
  const imageFile = formData.get("image");
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  if (!(imageFile instanceof File) || imageFile.size <= 0) {
    redirectWithMessage(path, "error", "Зураг сонгоно уу.", hash);
  }

  const uploadedFile = imageFile as File;

  if (!["before", "after"].includes(proofType)) {
    redirectWithMessage(path, "error", "Өмнөх эсвэл дараах зургийг сонгоно уу.", hash);
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await uploadFieldStopProof(
      {
        taskId,
        stopLineId,
        proofType,
        imageBase64: Buffer.from(await uploadedFile.arrayBuffer()).toString("base64"),
        fileName: uploadedFile.name,
        description,
        latitude: latitudeRaw ? Number(latitudeRaw) : null,
        longitude: longitudeRaw ? Number(longitudeRaw) : null,
      },
      connectionOverrides,
    );
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Зургийг орууллаа.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}

export async function createFieldStopIssueAction(formData: FormData) {
  const taskId = getNumberValue(formData, "task_id");
  const stopLineId = getNumberValue(formData, "stop_line_id");
  const title = String(formData.get("title") ?? "").trim();
  const issueType = String(formData.get("issue_type") ?? "").trim();
  const severity = String(formData.get("severity") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const { path, hash } = buildFieldPath(taskId, stopLineId);

  if (!title || !description) {
    redirectWithMessage(path, "error", "Асуудлын гарчиг, тайлбар хоёрыг бөглөнө үү.", hash);
  }

  try {
    const connectionOverrides = await getConnectionOverrides();
    await createFieldStopIssue(
      {
        taskId,
        stopLineId,
        title,
        issueType: issueType || "other",
        severity: severity || "medium",
        description,
      },
      connectionOverrides,
    );
    revalidateFieldPaths(taskId);
    redirect(`${path}&notice=${encodeURIComponent("Асуудлыг бүртгэлээ.")}${hash}`);
  } catch (error) {
    rethrowIfRedirectError(error);
    redirectWithMessage(path, "error", getErrorMessage(error), hash);
  }
}
