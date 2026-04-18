import "server-only";

import { executeOdooKw, type OdooConnection } from "@/lib/odoo";

type Relation = [number, string] | false;

type ProjectRecord = {
  id: number;
  name: string;
  user_id: Relation;
  ops_department_id: Relation;
  date_start: string | false;
  date: string | false;
};

type TaskRecord = {
  id: number;
  name: string;
  project_id: Relation;
  stage_id: Relation;
  ops_team_leader_id: Relation;
  user_ids: number[];
  ops_planned_quantity: number;
  ops_completed_quantity: number;
  ops_remaining_quantity: number;
  ops_progress_percent: number;
  ops_measurement_unit: string | false;
  priority: string;
  date_deadline: string | false;
  state: string;
  description?: string | false;
  ops_can_submit_for_review?: boolean;
  ops_can_mark_done?: boolean;
  ops_can_return_for_changes?: boolean;
  ops_reports_locked?: boolean;
};

type ReportRecord = {
  id: number;
  reporter_id: Relation;
  report_datetime: string;
  report_text: string;
  report_summary: string | false;
  reported_quantity: number;
  image_count: number;
  audio_count: number;
  image_attachment_ids: number[];
  audio_attachment_ids: number[];
};

type UserRecord = {
  id: number;
  name: string;
  login: string;
  ops_user_type: string | false;
};

type DepartmentRecord = {
  id: number;
  name: string;
  parent_id: Relation;
};

export type SelectOption = {
  id: number;
  name: string;
  login: string;
  role: string;
};

export type DepartmentOption = {
  id: number;
  name: string;
  label: string;
};

export type ProjectTaskCard = {
  id: number;
  name: string;
  href: string;
  stageLabel: string;
  stageBucket: StageBucket;
  progress: number;
  deadline: string;
  teamLeaderName: string;
  plannedQuantity: number;
  completedQuantity: number;
  measurementUnit: string;
};

export type ProjectDetail = {
  id: number;
  name: string;
  managerName: string;
  managerId: number | null;
  departmentName: string;
  departmentId: number | null;
  startDate: string;
  deadline: string;
  taskCount: number;
  reviewCount: number;
  doneCount: number;
  completion: number;
  tasks: ProjectTaskCard[];
  teamLeaderOptions: SelectOption[];
};

export type TaskReportFeedItem = {
  id: number;
  reporter: string;
  submittedAt: string;
  summary: string;
  text: string;
  quantity: number;
  imageCount: number;
  audioCount: number;
  images: {
    id: number;
    name: string;
    url: string;
  }[];
  audios: {
    id: number;
    name: string;
    url: string;
  }[];
};

export type TaskDetail = {
  id: number;
  name: string;
  projectId: number | null;
  projectName: string;
  stageLabel: string;
  stageBucket: StageBucket;
  state: string;
  deadline: string;
  measurementUnit: string;
  plannedQuantity: number;
  completedQuantity: number;
  remainingQuantity: number;
  progress: number;
  teamLeaderName: string;
  assignees: string[];
  priorityLabel: string;
  description: string;
  canSubmitForReview: boolean;
  canMarkDone: boolean;
  canReturnForChanges: boolean;
  reportsLocked: boolean;
  reports: TaskReportFeedItem[];
};

type StageBucket = "todo" | "progress" | "review" | "done" | "unknown";

const STAGE_ALIASES: Array<[StageBucket, string[]]> = [
  ["todo", ["хийгдэх ажил", "hiigdeh ajil", "todo", "task"]],
  ["progress", ["явагдаж буй ажил", "yovagdaj bui ajil", "progress", "in progress"]],
  ["review", ["шалгагдаж буй ажил", "shalgagdaj bui ajil", "review", "changes requested"]],
  ["done", ["дууссан ажил", "duussan ajil", "done", "completed"]],
];

function relationName(relation: Relation, fallback = "Тодорхойгүй") {
  return Array.isArray(relation) ? relation[1] : fallback;
}

function relationId(relation: Relation) {
  return Array.isArray(relation) ? relation[0] : null;
}

function normalizeStageBucket(name: string) {
  const normalized = (name || "").trim().toLowerCase();
  for (const [bucket, aliases] of STAGE_ALIASES) {
    if (aliases.some((alias) => normalized.includes(alias))) {
      return bucket;
    }
  }
  return "unknown";
}

function formatDateLabel(value?: string | false) {
  if (!value) {
    return "Товлоогүй";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("mn-MN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatDateInput(value?: string | false) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toISOString().slice(0, 10);
}

function priorityLabel(priority: string) {
  switch (priority) {
    case "3":
      return "Яаралтай";
    case "2":
      return "Өндөр";
    case "1":
      return "Дунд";
    default:
      return "Тогтмол";
  }
}

async function loadUserOptions(
  roles: string[],
  connectionOverrides: Partial<OdooConnection>,
) {
  try {
    const users = await executeOdooKw<UserRecord[]>(
      "res.users",
      "search_read",
      [[["share", "=", false], ["ops_user_type", "in", roles]]],
      {
        fields: ["name", "login", "ops_user_type"],
        order: "name asc",
        limit: 80,
      },
      connectionOverrides,
    );

    return users.map((user) => ({
      id: user.id,
      name: user.name,
      login: user.login,
      role: user.ops_user_type || "worker",
    }));
  } catch {
    return [] satisfies SelectOption[];
  }
}

export async function loadProjectManagerOptions(
  connectionOverrides: Partial<OdooConnection> = {},
) {
  return loadUserOptions(
    ["general_manager", "project_manager", "system_admin"],
    connectionOverrides,
  );
}

export async function loadTeamLeaderOptions(
  connectionOverrides: Partial<OdooConnection> = {},
) {
  return loadUserOptions(["team_leader"], connectionOverrides);
}

export async function loadDepartmentOptions(
  connectionOverrides: Partial<OdooConnection> = {},
): Promise<DepartmentOption[]> {
  try {
    const departments = await executeOdooKw<DepartmentRecord[]>(
      "hr.department",
      "search_read",
      [[["active", "=", true]]],
      {
        fields: ["name", "parent_id"],
        order: "parent_id asc, name asc",
        limit: 80,
      },
      connectionOverrides,
    );

    return departments.map((department) => {
      const parentName = Array.isArray(department.parent_id)
        ? department.parent_id[1]
        : "";

      return {
        id: department.id,
        name: department.name,
        label: parentName ? `${parentName} / ${department.name}` : department.name,
      };
    });
  } catch {
    return [];
  }
}

export async function loadProjectDetail(
  projectId: number,
  connectionOverrides: Partial<OdooConnection> = {},
): Promise<ProjectDetail> {
  const [projects, tasks, teamLeaderOptions] = await Promise.all([
    executeOdooKw<ProjectRecord[]>(
      "project.project",
      "search_read",
      [[["id", "=", projectId]]],
      {
        fields: ["name", "user_id", "ops_department_id", "date_start", "date"],
        limit: 1,
      },
      connectionOverrides,
    ),
    executeOdooKw<TaskRecord[]>(
      "project.task",
      "search_read",
      [[["project_id", "=", projectId]]],
      {
        fields: [
          "name",
          "stage_id",
          "ops_team_leader_id",
          "ops_planned_quantity",
          "ops_completed_quantity",
          "ops_progress_percent",
          "ops_measurement_unit",
          "date_deadline",
        ],
        order: "priority desc, date_deadline asc, create_date desc",
        limit: 120,
      },
      connectionOverrides,
    ),
    loadTeamLeaderOptions(connectionOverrides),
  ]);

  const project = projects[0];
  if (!project) {
    throw new Error("Төсөл олдсонгүй.");
  }

  const doneCount = tasks.filter(
    (task) => normalizeStageBucket(relationName(task.stage_id, "")) === "done",
  ).length;
  const reviewCount = tasks.filter(
    (task) => normalizeStageBucket(relationName(task.stage_id, "")) === "review",
  ).length;

  return {
    id: project.id,
    name: project.name,
    managerName: relationName(project.user_id),
    managerId: relationId(project.user_id),
    departmentName: relationName(project.ops_department_id),
    departmentId: relationId(project.ops_department_id),
    startDate: formatDateInput(project.date_start),
    deadline: formatDateInput(project.date),
    taskCount: tasks.length,
    reviewCount,
    doneCount,
    completion: tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0,
    tasks: tasks.map((task) => ({
      id: task.id,
      name: task.name,
      href: `/tasks/${task.id}`,
      stageLabel: relationName(task.stage_id, "Тодорхойгүй"),
      stageBucket: normalizeStageBucket(relationName(task.stage_id, "")),
      progress: Math.round(task.ops_progress_percent ?? 0),
      deadline: formatDateLabel(task.date_deadline),
      teamLeaderName: relationName(task.ops_team_leader_id),
      plannedQuantity: task.ops_planned_quantity ?? 0,
      completedQuantity: task.ops_completed_quantity ?? 0,
      measurementUnit: task.ops_measurement_unit || "нэгж",
    })),
    teamLeaderOptions,
  };
}

export async function loadTaskDetail(
  taskId: number,
  connectionOverrides: Partial<OdooConnection> = {},
): Promise<TaskDetail> {
  const [tasks, reports] = await Promise.all([
    executeOdooKw<TaskRecord[]>(
      "project.task",
      "search_read",
      [[["id", "=", taskId]]],
      {
        fields: [
          "name",
          "project_id",
          "stage_id",
          "ops_team_leader_id",
          "user_ids",
          "ops_planned_quantity",
          "ops_completed_quantity",
          "ops_remaining_quantity",
          "ops_progress_percent",
          "ops_measurement_unit",
          "priority",
          "date_deadline",
          "state",
          "description",
          "ops_can_submit_for_review",
          "ops_can_mark_done",
          "ops_can_return_for_changes",
          "ops_reports_locked",
        ],
        limit: 1,
      },
      connectionOverrides,
    ),
    executeOdooKw<ReportRecord[]>(
      "ops.task.report",
      "search_read",
      [[["task_id", "=", taskId]]],
      {
        fields: [
          "reporter_id",
          "report_datetime",
          "report_text",
          "report_summary",
          "reported_quantity",
          "image_count",
          "audio_count",
          "image_attachment_ids",
          "audio_attachment_ids",
        ],
        order: "report_datetime desc",
        limit: 60,
      },
      connectionOverrides,
    ),
  ]);

  const task = tasks[0];
  if (!task) {
    throw new Error("Даалгавар олдсонгүй.");
  }

  let assigneeNames: string[] = [];
  if (task.user_ids?.length) {
    try {
      const assignees = await executeOdooKw<UserRecord[]>(
        "res.users",
        "search_read",
        [[["id", "in", task.user_ids]]],
        {
          fields: ["name", "login", "ops_user_type"],
          order: "name asc",
          limit: task.user_ids.length,
        },
        connectionOverrides,
      );
      assigneeNames = assignees.map((user) => user.name);
    } catch {
      assigneeNames = task.user_ids.map((id) => `Хэрэглэгч #${id}`);
    }
  }

  return {
    id: task.id,
    name: task.name,
    projectId: relationId(task.project_id),
    projectName: relationName(task.project_id),
    stageLabel: relationName(task.stage_id, "Тодорхойгүй"),
    stageBucket: normalizeStageBucket(relationName(task.stage_id, "")),
    state: task.state,
    deadline: formatDateLabel(task.date_deadline),
    measurementUnit: task.ops_measurement_unit || "нэгж",
    plannedQuantity: task.ops_planned_quantity ?? 0,
    completedQuantity: task.ops_completed_quantity ?? 0,
    remainingQuantity: task.ops_remaining_quantity ?? 0,
    progress: Math.round(task.ops_progress_percent ?? 0),
    teamLeaderName: relationName(task.ops_team_leader_id),
    assignees: assigneeNames,
    priorityLabel: priorityLabel(task.priority),
    description: task.description || "",
    canSubmitForReview: Boolean(task.ops_can_submit_for_review),
    canMarkDone: Boolean(task.ops_can_mark_done),
    canReturnForChanges: Boolean(task.ops_can_return_for_changes),
    reportsLocked: Boolean(task.ops_reports_locked),
    reports: reports.map((report) => ({
      id: report.id,
      reporter: relationName(report.reporter_id),
      submittedAt: formatDateLabel(report.report_datetime),
      summary: report.report_summary || "Тайлбар оруулаагүй",
      text: report.report_text || "",
      quantity: report.reported_quantity ?? 0,
      imageCount: report.image_count ?? 0,
      audioCount: report.audio_count ?? 0,
      images: (report.image_attachment_ids ?? []).map((attachmentId) => ({
        id: attachmentId,
        name: `image-${attachmentId}`,
        url: `/api/odoo/attachments/${attachmentId}`,
      })),
      audios: (report.audio_attachment_ids ?? []).map((attachmentId) => ({
        id: attachmentId,
        name: `audio-${attachmentId}`,
        url: `/api/odoo/attachments/${attachmentId}`,
      })),
    })),
  };
}

export async function createWorkspaceProject(
  input: {
    name: string;
    managerId?: number | null;
    departmentId?: number | null;
    trackQuantity?: boolean;
    plannedQuantity?: number | null;
    measurementUnit?: string;
    startDate?: string;
    deadline?: string;
  },
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const values: Record<string, unknown> = {
    name: input.name.trim(),
  };

  if (input.managerId) {
    values.user_id = input.managerId;
  }
  if (input.departmentId) {
    values.ops_department_id = input.departmentId;
  }
  if (input.trackQuantity) {
    values.ops_track_quantity = true;
    if (
      typeof input.plannedQuantity === "number" &&
      !Number.isNaN(input.plannedQuantity)
    ) {
      values.ops_planned_quantity = input.plannedQuantity;
    }
    if (input.measurementUnit) {
      values.ops_measurement_unit = input.measurementUnit.trim();
    }
  }
  if (input.startDate) {
    values.date_start = input.startDate;
  }
  if (input.deadline) {
    values.date = input.deadline;
  }

  return executeOdooKw<number>(
    "project.project",
    "create",
    [values],
    {},
    connectionOverrides,
  );
}

export async function createWorkspaceTask(
  input: {
    projectId: number;
    name: string;
    teamLeaderId?: number | null;
    deadline?: string;
    measurementUnit?: string;
    plannedQuantity?: number | null;
    description?: string;
  },
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const values: Record<string, unknown> = {
    project_id: input.projectId,
    name: input.name.trim(),
  };

  if (input.teamLeaderId) {
    values.ops_team_leader_id = input.teamLeaderId;
  }
  if (input.deadline) {
    values.date_deadline = input.deadline;
  }
  if (input.measurementUnit) {
    values.ops_measurement_unit = input.measurementUnit.trim();
  }
  if (typeof input.plannedQuantity === "number" && !Number.isNaN(input.plannedQuantity)) {
    values.ops_planned_quantity = input.plannedQuantity;
  }
  if (input.description) {
    values.description = input.description.trim();
  }

  return executeOdooKw<number>(
    "project.task",
    "create",
    [values],
    {},
    connectionOverrides,
  );
}

export async function createWorkspaceTaskReport(
  input: {
    taskId: number;
    reportText: string;
    reportedQuantity: number;
  },
  connectionOverrides: Partial<OdooConnection> = {},
) {
  return executeOdooKw<number>(
    "ops.task.report",
    "create",
    [
      {
        task_id: input.taskId,
        report_text: input.reportText.trim(),
        reported_quantity: input.reportedQuantity,
      },
    ],
    {},
    connectionOverrides,
  );
}

export async function submitWorkspaceTaskForReview(
  taskId: number,
  connectionOverrides: Partial<OdooConnection> = {},
) {
  return executeOdooKw<boolean>(
    "project.task",
    "action_ops_submit_for_review",
    [[taskId]],
    {},
    connectionOverrides,
  );
}

export async function markWorkspaceTaskDone(
  taskId: number,
  connectionOverrides: Partial<OdooConnection> = {},
) {
  return executeOdooKw<boolean>(
    "project.task",
    "action_ops_mark_done",
    [[taskId]],
    {},
    connectionOverrides,
  );
}

export async function returnWorkspaceTaskForChanges(
  taskId: number,
  reason: string,
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const wizardId = await executeOdooKw<number>(
    "ops.task.return.wizard",
    "create",
    [
      {
        task_id: taskId,
        return_reason: reason.trim(),
      },
    ],
    {},
    connectionOverrides,
  );

  return executeOdooKw(
    "ops.task.return.wizard",
    "action_confirm_return",
    [[wizardId]],
    {},
    connectionOverrides,
  );
}
