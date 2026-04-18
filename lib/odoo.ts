import "server-only";

import type { RoleGroupFlags } from "@/lib/roles";

type OdooRelation = [number, string] | false;

type OdooProjectRecord = {
  id: number;
  name: string;
  user_id: OdooRelation;
  ops_department_id: OdooRelation;
  date_start: string | false;
  date: string | false;
};

type OdooTaskRecord = {
  id: number;
  name: string;
  project_id: OdooRelation;
  ops_department_id: OdooRelation;
  stage_id: OdooRelation;
  ops_team_leader_id: OdooRelation;
  user_ids: number[];
  ops_planned_quantity: number;
  ops_completed_quantity: number;
  ops_remaining_quantity: number;
  ops_progress_percent: number;
  ops_measurement_unit: string | false;
  priority: string;
  date_deadline: string | false;
  state: string;
  mfo_is_operation_project: boolean;
  mfo_operation_type: string | false;
  mfo_route_id: OdooRelation;
  mfo_unresolved_stop_count: number;
  mfo_missing_proof_stop_count: number;
  mfo_route_deviation_stop_count: number;
  mfo_skipped_without_reason_count: number;
  mfo_weight_sync_warning: boolean;
  mfo_quality_exception_count: number;
};

type OdooReportRecord = {
  id: number;
  task_id: OdooRelation;
  reporter_id: OdooRelation;
  report_datetime: string;
  report_summary: string | false;
  reported_quantity: number;
  image_count: number;
  audio_count: number;
  image_attachment_ids: number[];
  audio_attachment_ids: number[];
};

type OdooAttachmentRecord = {
  id: number;
  name: string | false;
  mimetype: string | false;
};

type OdooAttachmentBinaryRecord = OdooAttachmentRecord & {
  datas: string | false;
};

type OdooUserRecord = {
  id: number;
  name: string;
  login: string;
  ops_user_type: string | false;
};

type DepartmentCard = {
  name: string;
  label: string;
  accent: string;
  openTasks: number;
  reviewTasks: number;
  completion: number;
};

type ProjectCard = {
  id: number;
  name: string;
  manager: string;
  departmentName: string;
  stageLabel: string;
  stageBucket: StageBucket;
  openTasks: number;
  completion: number;
  deadline: string;
  href: string;
};

type ReviewItem = {
  id: number;
  name: string;
  departmentName: string;
  stageLabel: string;
  deadline: string;
  projectName: string;
  leaderName: string;
  progress: number;
  href: string;
};

type LiveTask = {
  id: number;
  name: string;
  departmentName: string;
  projectName: string;
  stageLabel: string;
  stageBucket: StageBucket;
  deadline: string;
  plannedQuantity: number;
  completedQuantity: number;
  remainingQuantity: number;
  measurementUnit: string;
  leaderName: string;
  priorityLabel: string;
  progress: number;
  href: string;
};

type ReportFeedItem = {
  id: number;
  reporter: string;
  taskName: string;
  departmentName: string;
  projectName: string;
  summary: string;
  reportedQuantity: number;
  imageCount: number;
  audioCount: number;
  submittedAt: string;
  images: {
    id: number;
    name: string;
    mimetype: string;
    url: string;
  }[];
  audios: {
    id: number;
    name: string;
    mimetype: string;
    url: string;
  }[];
};

type TeamLeaderCard = {
  name: string;
  activeTasks: number;
  reviewTasks: number;
  averageCompletion: number;
  squadSize: number;
};

type QualityAlert = {
  id: number;
  name: string;
  departmentName: string;
  projectName: string;
  routeName: string;
  operationTypeLabel: string;
  exceptionCount: number;
  unresolvedStopCount: number;
  missingProofStopCount: number;
  deviationStopCount: number;
  skippedWithoutReasonCount: number;
  hasWeightWarning: boolean;
  href: string;
};

type DashboardMetric = {
  label: string;
  value: string;
  note: string;
  tone: "amber" | "teal" | "red" | "slate";
};

export type OdooConnection = {
  url: string;
  db: string;
  login: string;
  password: string;
};

export type AuthenticatedOdooUser = {
  uid: number;
  user: {
    name: string;
    login: string;
    role: string;
    groupFlags: RoleGroupFlags;
  };
};

export type DashboardSnapshot = {
  source: "live" | "demo";
  generatedAt: string;
  metrics: DashboardMetric[];
  qualityMetrics: DashboardMetric[];
  departments: DepartmentCard[];
  projects: ProjectCard[];
  liveTasks: LiveTask[];
  reviewQueue: ReviewItem[];
  qualityAlerts: QualityAlert[];
  reports: ReportFeedItem[];
  teamLeaders: TeamLeaderCard[];
  odooBaseUrl: string;
  totalTasks: number;
};

type StageBucket = "todo" | "progress" | "review" | "done" | "unknown";

const DEFAULT_CONNECTION: OdooConnection = {
  url: process.env.ODOO_URL ?? "http://localhost:8069",
  db: process.env.ODOO_DB ?? "odoo19_admin",
  login: process.env.ODOO_LOGIN ?? "admin",
  password: process.env.ODOO_PASSWORD ?? "admin",
};

export function createOdooConnection(
  overrides: Partial<OdooConnection> = {},
): OdooConnection {
  return {
    ...DEFAULT_CONNECTION,
    ...overrides,
  };
}

const DEPARTMENT_ORDER = [
  "Авто бааз",
  "Хог тээвэрлэлт",
  "Ногоон байгууламж",
  "Зам талбайн цэвэрлэгээ",
  "Тохижилт үйлчилгээ",
] as const;

const DEPARTMENT_LABELS: Record<(typeof DEPARTMENT_ORDER)[number], string> = {
  "Авто бааз": "Техник, тээврийн бэлэн байдал",
  "Хог тээвэрлэлт": "Ачилт, маршрут, цуглуулалт",
  "Ногоон байгууламж": "Мод, зүлэг, хэлбэржүүлэлт",
  "Зам талбайн цэвэрлэгээ": "Зам, талбай, явган зам",
  "Тохижилт үйлчилгээ": "Нийтийн талбай, засвар, жижиг ажил",
};

const DEPARTMENT_ACCENTS: Record<(typeof DEPARTMENT_ORDER)[number], string> = {
  "Авто бааз": "var(--tone-amber)",
  "Хог тээвэрлэлт": "var(--tone-red)",
  "Ногоон байгууламж": "var(--tone-teal)",
  "Зам талбайн цэвэрлэгээ": "var(--tone-blue)",
  "Тохижилт үйлчилгээ": "var(--tone-slate)",
};

const OPERATION_TYPE_LABELS: Record<string, string> = {
  garbage: "Хог цуглуулалт",
  street_cleaning: "Гудамж цэвэрлэгээ",
  green_maintenance: "Ногоон байгууламж",
};

const STAGE_LABELS: Record<StageBucket, string> = {
  todo: "Хийгдэх ажил",
  progress: "Явагдаж буй ажил",
  review: "Шалгагдаж буй ажил",
  done: "Дууссан ажил",
  unknown: "Тодорхойгүй",
};

const KNOWN_STAGE_MATCHERS: Array<[StageBucket, string[]]> = [
  ["todo", ["хийгдэх", "todo", "task"]],
  ["progress", ["явагдаж", "progress", "hiihdej", "in progress"]],
  ["review", ["шалгагдаж", "review", "changes requested", "shalgagdaj", "shalgah"]],
  ["done", ["дууссан", "done", "completed", "duussan"]],
];

function getStageBucket(stageName?: string | null): StageBucket {
  const normalized = (stageName ?? "").trim().toLowerCase();
  for (const [bucket, matchers] of KNOWN_STAGE_MATCHERS) {
    if (matchers.some((item) => normalized.includes(item))) {
      return bucket;
    }
  }
  return "unknown";
}

function relationName(relation: OdooRelation, fallback = "Оноогоогүй") {
  return Array.isArray(relation) ? relation[1] : fallback;
}

function formatCompactDate(value?: string | false) {
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

function formatSyncDate(value: Date) {
  return new Intl.DateTimeFormat("mn-MN", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function formatQuantity(value: number, unit: string) {
  return `${Math.round(value * 10) / 10} ${unit}`.trim();
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

function mapTaskToDepartment(task: Pick<OdooTaskRecord, "name" | "project_id">) {
  const haystack = `${task.name} ${relationName(task.project_id, "")}`.toLowerCase();
  if (haystack.includes("мод") || haystack.includes("ногоон")) {
    return "Ногоон байгууламж";
  }
  if (haystack.includes("хог")) {
    return "Хог тээвэрлэлт";
  }
  if (haystack.includes("авто") || haystack.includes("машин") || haystack.includes("техник")) {
    return "Авто бааз";
  }
  if (haystack.includes("зам") || haystack.includes("талбай") || haystack.includes("цэвэрлэгээ")) {
    return "Зам талбайн цэвэрлэгээ";
  }
  return "Тохижилт үйлчилгээ";
}

function resolveTaskDepartmentName(
  task: Pick<OdooTaskRecord, "name" | "project_id" | "ops_department_id">,
  projectDepartmentById: Map<number, string>,
) {
  const directDepartmentName = relationName(task.ops_department_id, "").trim();
  if (directDepartmentName) {
    return directDepartmentName;
  }

  const projectId = Array.isArray(task.project_id) ? task.project_id[0] : null;
  if (projectId && projectDepartmentById.get(projectId)) {
    return projectDepartmentById.get(projectId) as string;
  }

  return mapTaskToDepartment(task);
}

function operationTypeLabel(operationType?: string | false) {
  if (!operationType) {
    return "Ерөнхий ажил";
  }
  return OPERATION_TYPE_LABELS[operationType] ?? operationType;
}

function resolveProjectDepartmentName(
  project: Pick<OdooProjectRecord, "ops_department_id">,
  fallback = "Тодорхойгүй",
) {
  return relationName(project.ops_department_id, fallback);
}

function resolveDepartmentLabel(name: string) {
  return DEPARTMENT_LABELS[name as keyof typeof DEPARTMENT_LABELS] ?? "Төслийн харьяалал";
}

function resolveDepartmentAccent(name: string) {
  return DEPARTMENT_ACCENTS[name as keyof typeof DEPARTMENT_ACCENTS] ?? "var(--tone-slate)";
}

async function jsonRpc<T>(
  service: "common" | "object",
  method: string,
  args: unknown[],
  connection: OdooConnection,
) {
  const response = await fetch(`${connection.url}/jsonrpc`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "call",
      params: {
        service,
        method,
        args,
      },
      id: `${service}-${method}-${Date.now()}`,
    }),
  });

  if (!response.ok) {
    throw new Error(`Odoo JSON-RPC хүсэлт HTTP ${response.status} алдаатай дууслаа.`);
  }

  const payload = (await response.json()) as {
    result?: T;
    error?: {
      message?: string;
      data?: {
        message?: string;
        debug?: string;
      };
    };
  };
  if (payload.error) {
    throw new Error(
      payload.error.data?.message ??
        payload.error.message ??
        "Odoo JSON-RPC алдаа тодорхойгүй байна.",
    );
  }

  return payload.result as T;
}

async function authenticate(connection: OdooConnection) {
  return jsonRpc<number | false>(
    "common",
    "authenticate",
    [connection.db, connection.login, connection.password, {}],
    connection,
  );
}

export async function authenticateOdooUser(
  login: string,
  password: string,
): Promise<AuthenticatedOdooUser | null> {
  const connection = createOdooConnection({ login, password });
  const uid = await authenticate(connection);

  if (!uid) {
    return null;
  }

  const users = await executeKw<OdooUserRecord[]>(
    uid,
    "res.users",
    "search_read",
    [[["id", "=", uid]]],
    {
      fields: ["name", "login", "ops_user_type"],
      limit: 1,
    },
    connection,
  );

  const user = users[0];
  if (!user) {
    return null;
  }

  const [
    mfoManager,
    mfoDispatcher,
    mfoInspector,
    mfoMobile,
  ] = await Promise.all([
    executeKw<boolean>(
      uid,
      "res.users",
      "has_group",
      [[uid], "municipal_field_ops.group_mfo_manager"],
      {},
      connection,
    ),
    executeKw<boolean>(
      uid,
      "res.users",
      "has_group",
      [[uid], "municipal_field_ops.group_mfo_dispatcher"],
      {},
      connection,
    ),
    executeKw<boolean>(
      uid,
      "res.users",
      "has_group",
      [[uid], "municipal_field_ops.group_mfo_inspector"],
      {},
      connection,
    ),
    executeKw<boolean>(
      uid,
      "res.users",
      "has_group",
      [[uid], "municipal_field_ops.group_mfo_mobile_user"],
      {},
      connection,
    ),
  ]);

  return {
    uid,
    user: {
      name: user.name,
      login: user.login,
      role: user.ops_user_type || "worker",
      groupFlags: {
        mfoManager,
        mfoDispatcher,
        mfoInspector,
        mfoMobile,
      },
    },
  };
}

async function executeKw<T>(
  uid: number,
  model: string,
  method: string,
  methodArgs: unknown[],
  kwargs: Record<string, unknown>,
  connection: OdooConnection,
) {
  return jsonRpc<T>(
    "object",
    "execute_kw",
    [connection.db, uid, connection.password, model, method, methodArgs, kwargs],
    connection,
  );
}

export async function executeOdooKw<T>(
  model: string,
  method: string,
  methodArgs: unknown[],
  kwargs: Record<string, unknown> = {},
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const connection = createOdooConnection(connectionOverrides);
  const uid = await authenticate(connection);

  if (!uid) {
    throw new Error("Odoo authentication failed");
  }

  return executeKw<T>(uid, model, method, methodArgs, kwargs, connection);
}

export async function fetchOdooAttachmentContent(
  attachmentId: number,
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const attemptRead = async (connection: OdooConnection) => {
    const uid = await authenticate(connection);

    if (!uid) {
      throw new Error("Odoo authentication failed");
    }

    const attachments = await executeKw<OdooAttachmentBinaryRecord[]>(
      uid,
      "ir.attachment",
      "search_read",
      [[["id", "=", attachmentId]]],
      {
        fields: ["name", "mimetype", "datas"],
        limit: 1,
      },
      connection,
    );

    const attachment = attachments[0];
    if (!attachment?.datas) {
      return null;
    }

    return {
      id: attachment.id,
      name: attachment.name || `attachment-${attachment.id}`,
      mimetype: attachment.mimetype || "application/octet-stream",
      datas: attachment.datas,
    };
  };

  const primaryConnection = createOdooConnection(connectionOverrides);
  const primaryResult = await attemptRead(primaryConnection);
  if (primaryResult) {
    return primaryResult;
  }

  const fallbackConnection = createOdooConnection();
  const sameCredentials =
    fallbackConnection.login === primaryConnection.login &&
    fallbackConnection.password === primaryConnection.password &&
    fallbackConnection.db === primaryConnection.db &&
    fallbackConnection.url === primaryConnection.url;

  if (sameCredentials) {
    return null;
  }

  return attemptRead(fallbackConnection);
}

async function fetchLiveSnapshot(connection: OdooConnection): Promise<DashboardSnapshot> {
  const uid = await authenticate(connection);
  if (!uid) {
    throw new Error("Odoo authentication failed");
  }

  const [projects, tasks, reports] = await Promise.all([
    executeKw<OdooProjectRecord[]>(
      uid,
      "project.project",
      "search_read",
      [[]],
      {
        fields: ["name", "user_id", "ops_department_id", "date_start", "date"],
        limit: 500,
        order: "create_date desc",
      },
      connection,
    ),
    executeKw<OdooTaskRecord[]>(
      uid,
      "project.task",
      "search_read",
      [[["project_id", "!=", false]]],
      {
        fields: [
          "name",
          "project_id",
          "ops_department_id",
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
          "mfo_is_operation_project",
          "mfo_operation_type",
          "mfo_route_id",
          "mfo_unresolved_stop_count",
          "mfo_missing_proof_stop_count",
          "mfo_route_deviation_stop_count",
          "mfo_skipped_without_reason_count",
          "mfo_weight_sync_warning",
          "mfo_quality_exception_count",
        ],
        limit: 2000,
        order: "priority desc, date_deadline asc, create_date desc",
      },
      connection,
    ),
    executeKw<OdooReportRecord[]>(
      uid,
      "ops.task.report",
      "search_read",
      [[]],
      {
        fields: [
          "task_id",
          "reporter_id",
          "report_datetime",
          "report_summary",
          "reported_quantity",
          "image_count",
          "audio_count",
          "image_attachment_ids",
          "audio_attachment_ids",
        ],
        limit: 200,
        order: "report_datetime desc",
      },
      connection,
    ),
  ]);

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((task) => getStageBucket(relationName(task.stage_id, "")) === "done");
  const reviewTasks = tasks.filter((task) => getStageBucket(relationName(task.stage_id, "")) === "review");
  const activeTasks = tasks.filter((task) => {
    const bucket = getStageBucket(relationName(task.stage_id, ""));
    return bucket === "todo" || bucket === "progress";
  });
  const overdueTasks = tasks.filter((task) => {
    if (!task.date_deadline) {
      return false;
    }
    const bucket = getStageBucket(relationName(task.stage_id, ""));
    if (bucket === "done") {
      return false;
    }
    return new Date(task.date_deadline).getTime() < Date.now();
  });

  const projectDepartmentById = new Map(
    projects.map((project) => [
      project.id,
      Array.isArray(project.ops_department_id)
        ? project.ops_department_id[1]
        : mapTaskToDepartment({ name: project.name, project_id: false }),
    ]),
  );

  const taskDepartmentNames = tasks.map((task) =>
    resolveTaskDepartmentName(task, projectDepartmentById),
  );

  const departmentNames = [
    ...DEPARTMENT_ORDER.filter((name) =>
      [...projectDepartmentById.values(), ...taskDepartmentNames].includes(name),
    ),
    ...new Set(
      [...projectDepartmentById.values(), ...taskDepartmentNames].filter(Boolean),
    ),
  ]
    .filter(
      (name, index, collection) =>
        collection.indexOf(name) === index &&
        !DEPARTMENT_ORDER.includes(name as (typeof DEPARTMENT_ORDER)[number]),
    )
    .sort((left, right) => left.localeCompare(right, "mn"));

  const orderedDepartmentNames = [
    ...DEPARTMENT_ORDER.filter((name) =>
      [...projectDepartmentById.values(), ...taskDepartmentNames].includes(name),
    ),
    ...departmentNames,
  ];

  const departments = orderedDepartmentNames.map((department) => {
    const departmentTasks = tasks.filter((task) => {
      const departmentName = resolveTaskDepartmentName(task, projectDepartmentById);
      return departmentName === department;
    });
    const departmentDone = departmentTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "done",
    );
    const departmentReview = departmentTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "review",
    );

    return {
      name: department,
      label: resolveDepartmentLabel(department),
      accent: resolveDepartmentAccent(department),
      openTasks: departmentTasks.length - departmentDone.length,
      reviewTasks: departmentReview.length,
      completion: departmentTasks.length
        ? Math.round((departmentDone.length / departmentTasks.length) * 100)
        : 0,
    };
  });

  const projectsWithStats = projects.map((project) => {
    const projectTasks = tasks.filter(
      (task) => Array.isArray(task.project_id) && task.project_id[0] === project.id,
    );
    const completed = projectTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "done",
    ).length;
    const buckets = projectTasks.map((task) => getStageBucket(relationName(task.stage_id, "")));
    const stageBucket =
      buckets.includes("review")
        ? "review"
        : buckets.includes("progress")
          ? "progress"
          : buckets.includes("todo")
            ? "todo"
            : buckets.includes("done")
              ? "done"
              : "unknown";

    return {
      id: project.id,
      name: project.name,
      manager: relationName(project.user_id),
      departmentName: resolveProjectDepartmentName(project),
      stageLabel: STAGE_LABELS[stageBucket],
      stageBucket,
      openTasks: projectTasks.length - completed,
      completion: projectTasks.length ? Math.round((completed / projectTasks.length) * 100) : 0,
      deadline: formatCompactDate(project.date),
      href: `/projects/${project.id}`,
    } satisfies ProjectCard;
  });

  const liveTasks = activeTasks.map((task) => ({
    id: task.id,
    name: task.name,
    departmentName: resolveTaskDepartmentName(task, projectDepartmentById),
    projectName: relationName(task.project_id),
    stageLabel: STAGE_LABELS[getStageBucket(relationName(task.stage_id, ""))],
    stageBucket: getStageBucket(relationName(task.stage_id, "")),
    deadline: formatCompactDate(task.date_deadline),
    plannedQuantity: task.ops_planned_quantity ?? 0,
    completedQuantity: task.ops_completed_quantity ?? 0,
    remainingQuantity: task.ops_remaining_quantity ?? 0,
    measurementUnit: task.ops_measurement_unit || "ш",
    leaderName: relationName(task.ops_team_leader_id),
    priorityLabel: priorityLabel(task.priority),
    progress: Math.round(task.ops_progress_percent ?? 0),
    href: `/tasks/${task.id}`,
  }));

  const reviewQueue = reviewTasks.map((task) => ({
    id: task.id,
    name: task.name,
    departmentName: resolveTaskDepartmentName(task, projectDepartmentById),
    stageLabel: relationName(task.stage_id, STAGE_LABELS.review),
    deadline: formatCompactDate(task.date_deadline),
    projectName: relationName(task.project_id),
    leaderName: relationName(task.ops_team_leader_id),
    progress: Math.round(task.ops_progress_percent ?? 0),
    href: `/tasks/${task.id}`,
  }));

  const attachmentIds = [
    ...new Set(
      reports.flatMap((report) => [
        ...(report.image_attachment_ids ?? []),
        ...(report.audio_attachment_ids ?? []),
      ]),
    ),
  ];

  const attachmentMap = new Map<number, OdooAttachmentRecord>();
  if (attachmentIds.length) {
    const attachments = await executeKw<OdooAttachmentRecord[]>(
      uid,
      "ir.attachment",
      "search_read",
      [[["id", "in", attachmentIds]]],
      {
        fields: ["name", "mimetype"],
        limit: attachmentIds.length,
      },
      connection,
    );

    for (const attachment of attachments) {
      attachmentMap.set(attachment.id, attachment);
    }
  }

  const reportTaskMap = new Map(tasks.map((task) => [task.id, task]));
  const reportsFeed = reports.map((report) => {
    const task = Array.isArray(report.task_id) ? reportTaskMap.get(report.task_id[0]) : undefined;
    const images = (report.image_attachment_ids ?? []).map((attachmentId) => {
      const attachment = attachmentMap.get(attachmentId);
      return {
        id: attachmentId,
        name: attachment?.name || `image-${attachmentId}`,
        mimetype: attachment?.mimetype || "image/*",
        url: `/api/odoo/attachments/${attachmentId}`,
      };
    });
    const audios = (report.audio_attachment_ids ?? []).map((attachmentId) => {
      const attachment = attachmentMap.get(attachmentId);
      return {
        id: attachmentId,
        name: attachment?.name || `audio-${attachmentId}`,
        mimetype: attachment?.mimetype || "audio/*",
        url: `/api/odoo/attachments/${attachmentId}`,
      };
    });
    return {
      id: report.id,
      reporter: relationName(report.reporter_id),
      taskName: relationName(report.task_id),
      departmentName: task
        ? resolveTaskDepartmentName(task, projectDepartmentById)
        : "Тодорхойгүй",
      projectName: task ? relationName(task.project_id) : "Төсөлгүй",
      summary: report.report_summary || "Тайлбар оруулаагүй",
      reportedQuantity: report.reported_quantity ?? 0,
      imageCount: report.image_count ?? 0,
      audioCount: report.audio_count ?? 0,
      submittedAt: formatCompactDate(report.report_datetime),
      images,
      audios,
    } satisfies ReportFeedItem;
  });

  const teamLeaderMap = new Map<string, TeamLeaderCard>();
  for (const task of tasks) {
    const leaderName = relationName(task.ops_team_leader_id, "Оноогоогүй");
    const entry = teamLeaderMap.get(leaderName) ?? {
      name: leaderName,
      activeTasks: 0,
      reviewTasks: 0,
      averageCompletion: 0,
      squadSize: Math.max((task.user_ids?.length ?? 1) - 1, 0),
    };

    const bucket = getStageBucket(relationName(task.stage_id, ""));
    if (bucket === "review") {
      entry.reviewTasks += 1;
    }
    if (bucket === "todo" || bucket === "progress") {
      entry.activeTasks += 1;
    }
    entry.averageCompletion += task.ops_progress_percent ?? 0;
    entry.squadSize = Math.max(entry.squadSize, Math.max((task.user_ids?.length ?? 1) - 1, 0));
    teamLeaderMap.set(leaderName, entry);
  }

  const teamLeaders = Array.from(teamLeaderMap.values())
    .map((leader) => {
      const relatedTasks = tasks.filter(
        (task) => relationName(task.ops_team_leader_id, "Оноогоогүй") === leader.name,
      );
      const totalProgress = relatedTasks.reduce(
        (sum, task) => sum + (task.ops_progress_percent ?? 0),
        0,
      );
      return {
        ...leader,
        averageCompletion: relatedTasks.length ? Math.round(totalProgress / relatedTasks.length) : 0,
      };
    })
    .sort((left, right) => right.activeTasks - left.activeTasks)
    .slice(0, 4);

  const qualitySourceTasks = tasks.filter(
    (task) => task.mfo_is_operation_project && (task.mfo_quality_exception_count ?? 0) > 0,
  );
  const missingProofTasks = qualitySourceTasks.filter(
    (task) => (task.mfo_missing_proof_stop_count ?? 0) > 0,
  );
  const syncWarningTasks = qualitySourceTasks.filter((task) => task.mfo_weight_sync_warning);
  const deviationTasks = qualitySourceTasks.filter(
    (task) => (task.mfo_route_deviation_stop_count ?? 0) > 0,
  );
  const unresolvedQualityTasks = qualitySourceTasks.filter(
    (task) => (task.mfo_unresolved_stop_count ?? 0) > 0,
  );
  const qualityAlerts = qualitySourceTasks
    .map((task) => ({
      id: task.id,
      name: task.name,
      departmentName: resolveTaskDepartmentName(task, projectDepartmentById),
      projectName: relationName(task.project_id),
      routeName: relationName(task.mfo_route_id, "Маршрутгүй"),
      operationTypeLabel: operationTypeLabel(task.mfo_operation_type),
      exceptionCount: task.mfo_quality_exception_count ?? 0,
      unresolvedStopCount: task.mfo_unresolved_stop_count ?? 0,
      missingProofStopCount: task.mfo_missing_proof_stop_count ?? 0,
      deviationStopCount: task.mfo_route_deviation_stop_count ?? 0,
      skippedWithoutReasonCount: task.mfo_skipped_without_reason_count ?? 0,
      hasWeightWarning: Boolean(task.mfo_weight_sync_warning),
      href: `/tasks/${task.id}`,
    }))
    .sort((left, right) => right.exceptionCount - left.exceptionCount)
    .slice(0, 12);

  const completionRate = totalTasks ? Math.round((doneTasks.length / totalTasks) * 100) : 0;
  const completedQuantity = tasks.reduce(
    (sum, task) => sum + (task.ops_completed_quantity ?? 0),
    0,
  );

  return {
    source: "live",
    generatedAt: formatSyncDate(new Date()),
    odooBaseUrl: connection.url,
    totalTasks,
    metrics: [
      {
        label: "Идэвхтэй ажил",
        value: String(activeTasks.length),
        note: `${overdueTasks.length} нь хугацаа давсан`,
        tone: overdueTasks.length ? "red" : "slate",
      },
      {
        label: "Шалгалтын дараалал",
        value: String(reviewTasks.length),
        note: "Ерөнхий менежер баталгаажуулалт хүлээж байна",
        tone: "amber",
      },
      {
        label: "Нийт гүйцэтгэл",
        value: `${completionRate}%`,
        note: `${doneTasks.length}/${totalTasks} ажил дууссан`,
        tone: "teal",
      },
      {
        label: "Хэмжээний биелэлт",
        value: formatQuantity(completedQuantity, "нэгж"),
        note: "Талбарын тайлангаас автоматаар тооцсон",
        tone: "slate",
      },
    ],
    qualityMetrics: [
      {
        label: "Чанарын анхааруулга",
        value: String(qualitySourceTasks.length),
        note: "Талбарын гүйцэтгэл дээр засах шаардлагатай ажил",
        tone: qualitySourceTasks.length ? "red" : "teal",
      },
      {
        label: "Зураг дутсан ажил",
        value: String(missingProofTasks.length),
        note: "Өмнө, дараах зураг бүрэн биш",
        tone: missingProofTasks.length ? "amber" : "teal",
      },
      {
        label: "Синк анхааруулга",
        value: String(syncWarningTasks.length),
        note: "WRS эсвэл жингийн өгөгдөл бүрэн биш",
        tone: syncWarningTasks.length ? "red" : "slate",
      },
      {
        label: "Маршрутын зөрүү",
        value: String(deviationTasks.length),
        note: `${unresolvedQualityTasks.length} ажил нээлттэй цэгтэй`,
        tone: deviationTasks.length ? "amber" : "slate",
      },
    ],
    departments,
    projects: projectsWithStats,
    liveTasks,
    reviewQueue,
    qualityAlerts,
    reports: reportsFeed,
    teamLeaders,
  };
}

// Preserved temporarily while the clean fallback snapshot replaces the old demo payload.
function fallbackSnapshot(): DashboardSnapshot {
  return {
    source: "demo",
    generatedAt: formatSyncDate(new Date()),
    odooBaseUrl: DEFAULT_CONNECTION.url,
    totalTasks: 28,
    metrics: [
      {
        label: "Идэвхтэй ажил",
        value: "18",
        note: "3 нь хугацаа давсан",
        tone: "red",
      },
      {
        label: "Шалгалтын дараалал",
        value: "4",
        note: "Ерөнхий менежер шалгаж байна",
        tone: "amber",
      },
      {
        label: "Нийт гүйцэтгэл",
        value: "64%",
        note: "18/28 ажил дээр ахиц бүртгэгдсэн",
        tone: "teal",
      },
      {
        label: "Хэмжээний биелэлт",
        value: "713 мод",
        note: "Өнөөдрийн тайлангаас автоматаар тооцсон",
        tone: "slate",
      },
    ],
    qualityMetrics: [
      {
        label: "Чанарын анхааруулга",
        value: "5",
        note: "Талбарын гүйцэтгэл дээр дахин шалгах ажил",
        tone: "red",
      },
      {
        label: "Зураг дутсан ажил",
        value: "2",
        note: "Өмнө эсвэл дараах зураг бүрэн биш",
        tone: "amber",
      },
      {
        label: "Синк анхааруулга",
        value: "1",
        note: "Жингийн синкийг шалгах шаардлагатай",
        tone: "red",
      },
      {
        label: "Маршрутын зөрүү",
        value: "2",
        note: "Зөрүү эсвэл хаагдаагүй цэг илэрсэн",
        tone: "amber",
      },
    ],
    departments: DEPARTMENT_ORDER.map((name, index) => ({
      name,
      label: DEPARTMENT_LABELS[name],
      accent: DEPARTMENT_ACCENTS[name],
      openTasks: [4, 5, 9, 6, 4][index],
      reviewTasks: [1, 0, 2, 1, 0][index],
      completion: [58, 67, 72, 49, 63][index],
    })),
    projects: [
      {
        id: 1,
        name: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        manager: "BATAA",
        departmentName: "Ногоон байгууламж",
        stageLabel: "Шалгагдаж буй ажил",
        stageBucket: "review",
        openTasks: 14,
        completion: 71,
        deadline: "4-р сарын 20, 18:00",
        href: "/projects/1",
      },
      {
        id: 2,
        name: "Хог тээвэрлэлтийн өглөөний маршрут",
        manager: "ankhaa",
        departmentName: "Хог тээвэрлэлт",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        openTasks: 5,
        completion: 62,
        deadline: "Өнөөдөр 20:00",
        href: "/projects/2",
      },
      {
        id: 3,
        name: "Зам талбайн шөнийн цэвэрлэгээ",
        manager: "ankhaa",
        departmentName: "Зам талбайн цэвэрлэгээ",
        stageLabel: "Хийгдэх ажил",
        stageBucket: "todo",
        openTasks: 6,
        completion: 35,
        deadline: "4-р сарын 17, 06:00",
        href: "/projects/3",
      },
    ],
    liveTasks: [
      {
        id: 101,
        departmentName: "ÐÐ¾Ð³Ð¾Ð¾Ð½ Ð±Ð°Ð¹Ð³ÑƒÑƒÐ»Ð°Ð¼Ð¶",
        name: "1-р хороо - 20-р байрны ар тал",
        projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        deadline: "Өнөөдөр 18:00",
        plannedQuantity: 48,
        completedQuantity: 21,
        remainingQuantity: 27,
        measurementUnit: "мод",
        leaderName: "suldee",
        priorityLabel: "Өндөр",
        progress: 44,
        href: "/tasks/101",
      },
      {
        id: 102,
        departmentName: "Ð—Ð°Ð¼ Ñ‚Ð°Ð»Ð±Ð°Ð¹Ð½ Ñ†ÑÐ²ÑÑ€Ð»ÑÐ³ÑÑ",
        name: "7-р хороо - Төв замын захын цэвэрлэгээ",
        projectName: "Зам талбайн шөнийн цэвэрлэгээ",
        stageLabel: "Хийгдэх ажил",
        stageBucket: "todo",
        deadline: "Маргааш 06:00",
        plannedQuantity: 12,
        completedQuantity: 0,
        remainingQuantity: 12,
        measurementUnit: "км²",
        leaderName: "temuulen",
        priorityLabel: "Яаралтай",
        progress: 0,
        href: "/tasks/102",
      },
      {
        id: 103,
        departmentName: "ÐÐ²Ñ‚Ð¾ Ð±Ð°Ð°Ð·",
        name: "Авто бааз - 3 машинд урсгал үйлчилгээ",
        projectName: "Техникийн өдөр тутмын бэлэн байдал",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        deadline: "Өнөөдөр 17:30",
        plannedQuantity: 3,
        completedQuantity: 1,
        remainingQuantity: 2,
        measurementUnit: "машин",
        leaderName: "bold",
        priorityLabel: "Дунд",
        progress: 33,
        href: "/tasks/103",
      },
    ],
    reviewQueue: [
        {
          id: 201,
          name: "5-р хороо - 32 модны тайлан",
          departmentName: "Ногоон байгууламж",
          stageLabel: "Шалгагдаж буй ажил",
          deadline: "Өнөөдөр 16:30",
          projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
          leaderName: "suldee",
          progress: 100,
        href: "/tasks/201",
      },
        {
          id: 202,
          name: "Хог тээврийн 2-р маршрут",
          departmentName: "Хог тээвэрлэлт",
          stageLabel: "Шалгагдаж буй ажил",
          deadline: "Өнөөдөр 19:00",
          projectName: "Хог тээвэрлэлтийн өглөөний маршрут",
          leaderName: "sarangerel",
          progress: 88,
        href: "/tasks/202",
      },
    ],
    qualityAlerts: [
      {
        id: 401,
        name: "Хогийн 2-р маршрут",
        departmentName: "Хог тээвэрлэлт",
        projectName: "Өглөөний хог тээврийн маршрут",
        routeName: "2-р чиглэл",
        operationTypeLabel: "Хог цуглуулалт",
        exceptionCount: 3,
        unresolvedStopCount: 1,
        missingProofStopCount: 1,
        deviationStopCount: 0,
        skippedWithoutReasonCount: 0,
        hasWeightWarning: true,
        href: "/tasks/202",
      },
      {
        id: 402,
        name: "Төв замын цэвэрлэгээ",
        departmentName: "Зам талбайн цэвэрлэгээ",
        projectName: "Шөнийн гудамж цэвэрлэгээ",
        routeName: "7-р хорооны чиглэл",
        operationTypeLabel: "Гудамж цэвэрлэгээ",
        exceptionCount: 2,
        unresolvedStopCount: 1,
        missingProofStopCount: 0,
        deviationStopCount: 1,
        skippedWithoutReasonCount: 0,
        hasWeightWarning: false,
        href: "/tasks/102",
      },
    ],
    reports: [
      {
        id: 301,
        departmentName: "ÐÐ¾Ð³Ð¾Ð¾Ð½ Ð±Ð°Ð¹Ð³ÑƒÑƒÐ»Ð°Ð¼Ð¶",
        reporter: "suldee",
        taskName: "1-р хороо - 20-р байрны ар тал",
        projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        summary: "21 мод хэлбэржүүлж, 1 зураг, 1 аудио тайлан хавсаргасан.",
        reportedQuantity: 21,
        imageCount: 1,
        audioCount: 1,
        images: [],
        audios: [],
        submittedAt: "Өнөөдөр 15:30",
      },
      {
        id: 302,
        departmentName: "Ð¥Ð¾Ð³ Ñ‚ÑÑÐ²ÑÑ€Ð»ÑÐ»Ñ‚",
        reporter: "sarangerel",
        taskName: "Хог тээврийн 2-р маршрут",
        projectName: "Хог тээвэрлэлтийн өглөөний маршрут",
        summary: "Маршрут дууссан, дахин ачилт 18:00-д эхэлнэ.",
        reportedQuantity: 4,
        imageCount: 2,
        audioCount: 0,
        images: [],
        audios: [],
        submittedAt: "Өнөөдөр 14:10",
      },
    ],
    teamLeaders: [
      {
        name: "suldee",
        activeTasks: 3,
        reviewTasks: 1,
        averageCompletion: 68,
        squadSize: 5,
      },
      {
        name: "sarangerel",
        activeTasks: 4,
        reviewTasks: 1,
        averageCompletion: 73,
        squadSize: 6,
      },
      {
        name: "bold",
        activeTasks: 2,
        reviewTasks: 0,
        averageCompletion: 51,
        squadSize: 4,
      },
    ],
  };
}

function buildFallbackSnapshot(): DashboardSnapshot {
  return fallbackSnapshot();
}

export async function loadMunicipalSnapshot(
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const connection = createOdooConnection(connectionOverrides);

  try {
    return await fetchLiveSnapshot(connection);
  } catch (error) {
    console.warn("Falling back to demo dashboard snapshot:", error);
    return buildFallbackSnapshot();
  }
}
